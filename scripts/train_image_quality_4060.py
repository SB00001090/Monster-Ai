#!/usr/bin/env python3
"""Train anti-collapse LoRA on RTX 4060 using Monster AI quality datasets."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VIDEO_TRAINING_DIR = Path(r"C:\MonsterAI\Training generative video")
FFMPEG_WINGET_CANDIDATES = [
    Path.home()
    / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe",
]


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in FFMPEG_WINGET_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    for pkg in (Path.home() / "AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*"):
        for exe in pkg.rglob("ffmpeg.exe"):
            return str(exe)
    return None


def _video_training_dir(root: Path) -> Path:
    sys.path.insert(0, str(root))
    try:
        from monster_ai.config import load_settings

        configured = load_settings().modules.video.training_materials_dir
        if configured:
            return Path(configured)
    except Exception:
        pass
    return DEFAULT_VIDEO_TRAINING_DIR


def _slug_name(path: Path) -> str:
    stem = path.stem.replace(" ", "_")
    for ch in '()[]{}':
        stem = stem.replace(ch, "")
    return stem


def extract_training_video_frames(
    video_dir: Path,
    cache_dir: Path,
    *,
    ffmpeg: str,
    max_frames_per_video: int = 16,
    sample_fps: float = 2.0,
) -> tuple[list[Path], dict[str, str]]:
    """Extract PNG frames from reference MP4s for LoRA / quality training."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    frame_paths: list[Path] = []
    frame_prompts: dict[str, str] = {}
    videos = sorted(
        p for p in video_dir.iterdir() if p.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}
    )
    if not videos:
        return frame_paths, frame_prompts

    print(f"Video training materials: {video_dir} ({len(videos)} files)")
    for video in videos:
        key = str(video.resolve())
        mtime = video.stat().st_mtime
        slug = _slug_name(video)
        out_dir = cache_dir / slug
        prev = manifest.get(key, {})
        existing = sorted(out_dir.glob("frame_*.png")) if out_dir.exists() else []
        if prev.get("mtime") == mtime and len(existing) >= 1:
            frame_paths.extend(existing)
            caption = prev.get(
                "prompt",
                "cinematic generative video frame, high quality, smooth motion",
            )
            for fp in existing:
                frame_prompts[str(fp.resolve())] = caption
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("frame_*.png"):
            old.unlink(missing_ok=True)

        pattern = str(out_dir / "frame_%04d.png")
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps={sample_fps}",
            "-frames:v",
            str(max_frames_per_video),
            pattern,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"  skip {video.name}: ffmpeg failed")
            if result.stderr:
                print(result.stderr[-400:])
            continue

        extracted = sorted(out_dir.glob("frame_*.png"))
        caption = (
            f"cinematic generative video frame from {video.stem}, "
            "high quality, detailed, smooth motion"
        )
        manifest[key] = {
            "video": video.name,
            "mtime": mtime,
            "frames": len(extracted),
            "prompt": caption,
        }
        frame_paths.extend(extracted)
        for fp in extracted:
            frame_prompts[str(fp.resolve())] = caption
        print(f"  {video.name} -> {len(extracted)} frames")

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return frame_paths, frame_prompts


def _find_comfyui_output(root: Path) -> Path | None:
    scripts = root / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from detect_comfyui import find_comfyui

        base = find_comfyui()
    except Exception:
        base = None
    if not base:
        return None
    inner = base / "ComfyUI" if (base / "ComfyUI").exists() else base
    out = inner / "output"
    return out if out.is_dir() else None


def _build_prompt_map(root: Path) -> dict[str, str]:
    prompts: dict[str, str] = {}
    history = root / "data" / "logs" / "generation_history"
    index = history / "index.jsonl"
    if index.exists():
        for line in index.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            path = row.get("output_path") or ""
            name = Path(path).name
            if name:
                prompts[name] = row.get("prompt") or ""
    records = history / "records"
    if records.exists():
        for record in records.rglob("*.json"):
            try:
                row = json.loads(record.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            path = row.get("path") or row.get("output_path") or ""
            name = Path(path).name
            if name and row.get("prompt"):
                prompts[name] = row["prompt"]
    image_prompts: list[str] = []
    if index.exists():
        rows = [
            json.loads(line)
            for line in index.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for row in sorted(rows, key=lambda r: r.get("timestamp", "")):
            if row.get("type") == "image" and row.get("prompt"):
                image_prompts.append(row["prompt"])
    if image_prompts:
        prompts["__default_image__"] = image_prompts[-1]
        prompts["__default_video__"] = image_prompts[-1]
    return prompts


def scan_and_import_outputs(root: Path, data_dir: Path) -> tuple[int, int]:
    """Score output images/frames and archive into quality/good|bad."""
    sys.path.insert(0, str(root))
    from monster_ai.config import load_settings
    from monster_ai.modules.image.quality import ImageQualityScorer
    from monster_ai.modules.image.quality_store import QualityStore
    from monster_ai.modules.prompt.anti_collapse import build_negative

    settings = load_settings()
    q_cfg = settings.modules.image.quality
    scorer = ImageQualityScorer(q_cfg)
    store = QualityStore(data_dir, q_cfg)
    prompts = _build_prompt_map(root)

    archived_names = {
        p.name
        for folder in (data_dir / "good", data_dir / "bad")
        if folder.exists()
        for p in folder.glob("*.png")
    }
    archived_sources = set()
    for rec in load_quality_records(data_dir):
        src = (rec.get("extra") or {}).get("source")
        if src:
            archived_sources.add(str(Path(src).resolve()))
    archived_sources |= {
        str(p.resolve())
        for folder in (data_dir / "good", data_dir / "bad")
        if folder.exists()
        for p in folder.glob("*.png")
    }

    sources: list[Path] = []
    img_out = root / "data" / "outputs" / "images"
    if img_out.exists():
        sources.extend(sorted(img_out.glob("*.png")))
    vid_out = root / "data" / "outputs" / "videos"
    if vid_out.exists():
        for frames_dir in sorted(vid_out.glob("frames_*")):
            sources.extend(sorted(frames_dir.glob("frame_*.png")))

    comfy_out = _find_comfyui_output(root)
    if comfy_out:
        sources.extend(sorted(comfy_out.glob("*.png")))
        sources.extend(sorted(comfy_out.glob("*.jpg")))
        print(f"Scanning ComfyUI output: {comfy_out}")

    video_train_dir = _video_training_dir(root)
    video_frame_prompts: dict[str, str] = {}
    if video_train_dir.is_dir():
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            cache_dir = root / "data" / "training" / "video_materials" / "frames"
            vframes, video_frame_prompts = extract_training_video_frames(
                video_train_dir,
                cache_dir,
                ffmpeg=ffmpeg,
            )
            sources.extend(vframes)
        else:
            print(
                f"Video training dir found ({video_train_dir}) but ffmpeg missing — "
                "run scripts/setup_ffmpeg.bat"
            )
    else:
        print(f"Video training dir not found: {video_train_dir}")

    seen_sources: set[str] = set()
    unique_sources: list[Path] = []
    for src in sources:
        key = str(src.resolve())
        if key in seen_sources:
            continue
        seen_sources.add(key)
        unique_sources.append(src)

    good_n = bad_n = video_n = 0
    for src in unique_sources:
        src_key = str(src.resolve())
        from_video_train = "video_materials" in src_key
        if src_key in archived_sources:
            continue
        if not from_video_train and src.name in archived_names:
            continue
        if src_key in video_frame_prompts:
            prompt = video_frame_prompts[src_key]
        elif from_video_train:
            prompt = "cinematic generative video frame, high quality, smooth motion"
        elif src.name.startswith("monster_ai_vid"):
            prompt = prompts.get(src.name) or prompts.get("__default_video__", "video frame")
        elif src.name.startswith("monster_ai"):
            prompt = prompts.get(src.name) or prompts.get("__default_image__", "high quality detailed image")
        else:
            prompt = prompts.get(src.name, "high quality detailed image")
        negative = build_negative()
        report = scorer.evaluate(src, prompt)
        checkpoint = settings.modules.image.checkpoint
        from_comfy = bool(comfy_out and src_key.startswith(str(comfy_out.resolve())))
        if from_video_train:
            origin = "video_training"
        elif from_comfy:
            origin = "comfyui_output"
        else:
            origin = "monster_ai"
        if report.passed:
            store.save_good(
                src,
                prompt=prompt,
                negative=negative,
                report=report,
                checkpoint=checkpoint,
                attempt=0,
                extra={"source": str(src), "imported": True, "origin": origin},
            )
            good_n += 1
            if from_video_train:
                video_n += 1
        else:
            store.save_bad(
                src,
                prompt=prompt,
                negative=negative,
                report=report,
                checkpoint=checkpoint,
                attempt=0,
                extra={"source": str(src), "imported": True, "origin": origin},
            )
            bad_n += 1
            if from_video_train:
                video_n += 1
        archived_names.add(src.name)
        archived_sources.add(src_key)

    if video_n:
        print(f"Video training frames archived: {video_n}")
    return good_n, bad_n


def detect_vram_gb() -> float | None:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            mb = int(r.stdout.strip().split("\n")[0])
            return mb / 1024
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def _hardware_fingerprint(root: Path) -> str:
    binding = root / "data" / "monsterlock" / "hardware.binding"
    if binding.is_file():
        try:
            data = json.loads(binding.read_text(encoding="utf-8"))
            fp = data.get("fingerprint", "")
            if fp:
                return str(fp)
        except (OSError, json.JSONDecodeError):
            pass
    return "guardian-local-fallback"


def load_encrypted_vault_records(root: Path) -> list[dict]:
    """Load good/bad metadata from Guardian encrypted training vault."""
    sys.path.insert(0, str(root))
    try:
        from monster_ai.config import load_settings
        from monster_ai.modules.guardian.key_manager import TrainingKeyManager
        from monster_ai.modules.guardian.training_vault import TrainingVault
    except ImportError:
        return []

    settings = load_settings()
    if not settings.guardian.training_encryption_enabled:
        return []
    hw = _hardware_fingerprint(root)
    km = TrainingKeyManager(settings.guardian, root, hardware_fingerprint=hw)
    try:
        km.unlock(None)
    except ValueError:
        return []
    vault = TrainingVault(Path(settings.guardian.data_dir), km)
    return vault.quality_log_records()


def load_quality_records(data_dir: Path, *, root: Path | None = None) -> list[dict]:
    records: list[dict] = []
    log_path = data_dir / "quality_log.jsonl"
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    for label in ("good", "bad"):
        folder = data_dir / label
        if not folder.exists():
            continue
        for meta_path in folder.glob("*.json"):
            records.append(json.loads(meta_path.read_text(encoding="utf-8")))
    if not records and root is not None:
        records = load_encrypted_vault_records(root)
    seen: set[str] = set()
    unique: list[dict] = []
    for rec in records:
        rid = rec.get("id", json.dumps(rec, sort_keys=True))
        if rid in seen:
            continue
        seen.add(rid)
        unique.append(rec)
    return unique


def _vault_image_bytes(root: Path, asset_id: str) -> bytes | None:
    import base64

    sys.path.insert(0, str(root))
    try:
        from monster_ai.config import load_settings
        from monster_ai.modules.guardian.key_manager import TrainingKeyManager
        from monster_ai.modules.guardian.training_vault import TrainingVault
    except ImportError:
        return None
    settings = load_settings()
    hw = _hardware_fingerprint(root)
    km = TrainingKeyManager(settings.guardian, root, hardware_fingerprint=hw)
    try:
        km.unlock(None)
    except ValueError:
        return None
    vault = TrainingVault(Path(settings.guardian.data_dir), km)
    blob = vault.decrypt_asset_to_memory(asset_id)
    if not blob or not blob.get("image_b64"):
        return None
    return base64.b64decode(str(blob["image_b64"]))


def build_caption_manifest(data_dir: Path, out_dir: Path, *, root: Path | None = None) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    images_dir.mkdir(exist_ok=True)
    good_n = bad_n = 0
    project_root = root or ROOT

    for rec in load_quality_records(data_dir, root=project_root):
        label = rec.get("label", "good")
        prompt = rec.get("prompt", "high quality image")
        negative = rec.get("negative", "")
        img_name = f"{rec.get('id', 'sample')}.png"
        src_candidates = [
            data_dir / label / img_name,
            data_dir / "good" / img_name,
            data_dir / "bad" / img_name,
        ]
        extra_src = (rec.get("extra") or {}).get("source")
        if extra_src:
            src_candidates.insert(0, Path(extra_src))
        src = next((p for p in src_candidates if p.exists()), None)

        dest = images_dir / img_name
        if src is not None:
            if not dest.exists():
                dest.write_bytes(src.read_bytes())
        else:
            asset_id = str(rec.get("id", ""))
            if not asset_id:
                continue
            raw = _vault_image_bytes(project_root, asset_id)
            if raw is None:
                continue
            if not dest.exists():
                dest.write_bytes(raw)

        if label == "good":
            caption = prompt
            good_n += 1
        else:
            caption = f"{prompt} ### negative: {negative}, avoid collapse artifacts"
            bad_n += 1

        (images_dir / f"{dest.stem}.txt").write_text(caption, encoding="utf-8")

    return good_n, bad_n


def train_preference_lora(
    *,
    manifest_dir: Path,
    base_model: str,
    output: Path,
    rank: int,
    epochs: int,
    lr: float,
    low_vram: bool,
) -> int:
    try:
        import torch
        from diffusers import DDPMScheduler, StableDiffusionPipeline
        from peft import LoraConfig, get_peft_model
        from torch.utils.data import DataLoader, Dataset
        from PIL import Image
    except ImportError:
        print("Install training deps: pip install -r requirements-train.txt diffusers peft")
        return 1

    images_dir = manifest_dir / "images"
    if not images_dir.exists() or not any(images_dir.glob("*.png")):
        print(f"No training images in {images_dir}. Generate images with quality_filter enabled first.")
        return 1

    class LocalDataset(Dataset):
        def __init__(self) -> None:
            self.items = sorted(images_dir.glob("*.png"))

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, idx: int) -> dict:
            path = self.items[idx]
            caption_path = path.with_suffix(".txt")
            caption = caption_path.read_text(encoding="utf-8") if caption_path.exists() else ""
            image = Image.open(path).convert("RGB").resize((512, 512))
            return {"image": image, "caption": caption}

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = StableDiffusionPipeline.from_pretrained(
        base_model,
        torch_dtype=dtype,
        safety_checker=None,
    )
    pipe.scheduler = DDPMScheduler.from_config(pipe.scheduler.config)
    pipe.to(device)
    if low_vram and device == "cuda":
        pipe.enable_attention_slicing()
        pipe.vae.enable_slicing()
        try:
            pipe.unet.enable_gradient_checkpointing()
        except AttributeError:
            pass

    lora_config = LoraConfig(
        r=rank,
        lora_alpha=rank * 2,
        target_modules=["to_k", "to_q", "to_v", "to_out.0"],
        lora_dropout=0.05,
    )
    pipe.vae.requires_grad_(False)
    pipe.text_encoder.requires_grad_(False)
    pipe.unet = get_peft_model(pipe.unet, lora_config)
    pipe.unet.train()
    pipe.unet.to(device)

    optimizer = torch.optim.AdamW(pipe.unet.parameters(), lr=lr)
    dataset = LocalDataset()
    loader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=True,
        collate_fn=lambda batch: batch[0],
    )

    max_steps = min(800, max(50, epochs * len(dataset)))
    step = 0
    print(f"Training preference LoRA: {len(dataset)} images, max_steps={max_steps}")

    while step < max_steps:
        for batch in loader:
            if step >= max_steps:
                break
            images = [batch["image"]]
            captions = [batch["caption"]]
            with torch.no_grad():
                latents = pipe.vae.encode(
                    pipe.image_processor.preprocess(images).to(device=device, dtype=dtype)
                ).latent_dist.sample()
                latents = latents * pipe.vae.config.scaling_factor

            noise = torch.randn_like(latents)
            timesteps = torch.randint(
                0, pipe.scheduler.config.num_train_timesteps, (latents.shape[0],), device=device
            ).long()
            noisy = pipe.scheduler.add_noise(latents, noise, timesteps)
            encoder_hidden_states = pipe.text_encoder(
                pipe.tokenizer(
                    captions,
                    padding="max_length",
                    max_length=pipe.tokenizer.model_max_length,
                    truncation=True,
                    return_tensors="pt",
                ).input_ids.to(device)
            )[0]

            model_pred = pipe.unet(
                noisy, timesteps, encoder_hidden_states.to(device=device, dtype=dtype)
            ).sample
            loss = torch.nn.functional.mse_loss(model_pred, noise)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            step += 1
            if step % 25 == 0:
                print(f"step {step}/{max_steps} loss={loss.item():.4f}")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / "_lora_staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        if hasattr(pipe.unet, "save_lora_adapter"):
            pipe.unet.save_lora_adapter(staging, weight_name="anti_collapse")
        else:
            pipe.unet.save_attn_procs(staging)
    except Exception:
        pipe.unet.save_pretrained(staging)

    weight_candidates: list[Path] = [
        staging / "anti_collapse.safetensors",
        staging / "anti_collapse",
        staging / "pytorch_lora_weights.safetensors",
        staging / "adapter_model.safetensors",
    ]
    weight_candidates.extend(staging.rglob("*.safetensors"))
    for p in staging.iterdir():
        if p.is_file() and p.suffix.lower() not in {".json", ".md", ".txt"}:
            weight_candidates.append(p)
    seen: set[str] = set()
    src_weight = None
    for p in weight_candidates:
        key = str(p.resolve())
        if key in seen or not p.is_file() or p.stat().st_size < 1024:
            continue
        seen.add(key)
        src_weight = p
        break
    if src_weight is None:
        print(f"No LoRA weights found in {staging}")
        return 1

    if output.exists() and output.is_dir():
        shutil.rmtree(output, ignore_errors=True)
    elif output.exists():
        output.unlink()
    shutil.copy2(src_weight, output)
    shutil.rmtree(staging, ignore_errors=True)
    print(f"Saved LoRA weights to {output} ({output.stat().st_size} bytes)")
    return 0


def deploy_lora_to_comfyui(lora_path: Path) -> bool:
    if not lora_path.exists():
        print(f"LoRA not found: {lora_path}")
        return False
    comfy_out = _find_comfyui_output(ROOT)
    if not comfy_out:
        print("ComfyUI not found — copy LoRA manually to ComfyUI/models/loras/")
        return False
    lora_dir = comfy_out.parent / "models" / "loras"
    lora_dir.mkdir(parents=True, exist_ok=True)
    dest = lora_dir / lora_path.name
    if lora_path.is_dir():
        inner = lora_path / "pytorch_lora_weights.safetensors"
        if not inner.exists():
            inner = next(lora_path.rglob("*.safetensors"), None)
        if inner is None:
            print(f"No .safetensors inside {lora_path}")
            return False
        data = inner.read_bytes()
    else:
        data = lora_path.read_bytes()
    dest.write_bytes(data)
    print(f"Deployed LoRA -> {dest} ({len(data)} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Train anti-collapse image quality LoRA (RTX 4060)")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "quality")
    parser.add_argument("--base-model", default="runwayml/stable-diffusion-v1-5")
    parser.add_argument("--mode", choices=("preference_lora", "prepare_only"), default="preference_lora")
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "models" / "lora" / "anti_collapse.safetensors")
    parser.add_argument("--low-vram", action="store_true")
    parser.add_argument(
        "--scan-outputs",
        action="store_true",
        help="Import and score images from data/outputs before training",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copy trained LoRA to ComfyUI models/loras after training",
    )
    args = parser.parse_args()

    vram = detect_vram_gb()
    if vram is not None:
        print(f"Detected GPU VRAM: {vram:.1f} GB")
    if args.low_vram or (vram is not None and vram <= 8.5):
        args.low_vram = True
        print("Low VRAM mode enabled")

    if args.scan_outputs:
        imp_good, imp_bad = scan_and_import_outputs(ROOT, args.data_dir)
        print(f"Imported from outputs: {imp_good} good, {imp_bad} bad")

    manifest_dir = ROOT / "data" / "training" / "quality_manifest"
    good_n, bad_n = build_caption_manifest(args.data_dir, manifest_dir, root=ROOT)
    total = good_n + bad_n
    print(f"Manifest: {good_n} good, {bad_n} bad samples ({total} total) -> {manifest_dir}")

    if total >= 9 and args.epochs == 3:
        args.epochs = min(8, max(5, total // 2))
        print(f"Scaled epochs to {args.epochs} for {total} samples")

    if good_n + bad_n < 2:
        print("Need at least 2 archived images (good or bad). Enable quality_filter and generate images.")
        return 1

    if args.mode == "prepare_only":
        print("Dataset prepared. Run again without --mode prepare_only to train.")
        return 0

    rc = train_preference_lora(
        manifest_dir=manifest_dir,
        base_model=args.base_model,
        output=args.output,
        rank=args.rank,
        epochs=args.epochs,
        lr=args.lr,
        low_vram=args.low_vram,
    )
    if rc == 0 and args.deploy:
        deploy_lora_to_comfyui(args.output)
    return rc


if __name__ == "__main__":
    sys.exit(main())