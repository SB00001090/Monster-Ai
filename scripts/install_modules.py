"""Auto-install Monster AI modules with CUDA/VRAM-aware profiles."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], **kwargs) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, **kwargs)


def detect_vram_mb() -> int | None:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return int(r.stdout.strip().split("\n")[0])
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def pick_profile(vram_mb: int | None) -> str:
    if vram_mb is None:
        return "cpu"
    if vram_mb <= 10240:
        return "low_vram"
    return "high_vram"


def install_piper_voice(voice: str, dest: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from install_voice_pack import install_piper_voice as _install

    if not _install(voice, dest):
        print(f"Piper voice download failed or skipped: {voice}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Monster AI modules")
    parser.add_argument("--with-train", action="store_true", help="Install training stack")
    parser.add_argument("--with-quality", action="store_true", help="Install CLIP quality scoring (torch + open-clip)")
    parser.add_argument("--download-models", action="store_true", help="Download recommended models")
    parser.add_argument("--with-generate", action="store_true", default=True)
    parser.add_argument("--upgrade", action="store_true", default=True)
    args = parser.parse_args()

    vram = detect_vram_mb()
    profile = pick_profile(vram)
    print(f"VRAM: {vram or 'unknown'} MB → profile: {profile}")

    pip = [sys.executable, "-m", "pip", "install"]
    if args.upgrade:
        pip.append("--upgrade")

    run(pip + ["-r", str(ROOT / "requirements.txt")])
    if args.with_generate:
        run(pip + ["-r", str(ROOT / "requirements-generate.txt")])

    if args.with_quality:
        run([
            sys.executable, "-m", "pip", "install", "torch", "torchvision",
            "--index-url", "https://download.pytorch.org/whl/cu124",
        ])
        run(pip + ["open-clip-torch>=2.24.0"])

    if args.download_models:
        run([sys.executable, str(ROOT / "scripts" / "download_models.py")])

    if args.with_train:
        run([
            sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio",
            "--index-url", "https://download.pytorch.org/whl/cu124",
        ])
        run(pip + ["-r", str(ROOT / "requirements-train.txt"), "-c", str(ROOT / "constraints.txt")])

    voices = ["en_US-lessac-medium", "zh_CN-huayan-medium"]
    for voice in voices:
        install_piper_voice(voice, ROOT / "data" / "models" / "piper")
    voice = voices[-1]

    sys.path.insert(0, str(Path(__file__).parent))
    from detect_comfyui import find_comfyui
    comfy = find_comfyui()
    checkpoints: list[str] = []
    loras: list[str] = []
    animatediff = False
    if comfy:
        inner = comfy / "ComfyUI" if (comfy / "ComfyUI").exists() else comfy
        ckpt_dir = inner / "models" / "checkpoints"
        lora_dir = inner / "models" / "loras"
        if ckpt_dir.exists():
            checkpoints = [p.name for p in ckpt_dir.iterdir() if p.suffix == ".safetensors"]
        if lora_dir.exists():
            loras = [p.name for p in lora_dir.iterdir() if p.suffix == ".safetensors"]
        custom = inner / "custom_nodes"
        if custom.exists():
            animatediff = any(
                "animatediff" in p.name.lower() for p in custom.iterdir() if p.is_dir()
            )
    suggested_config = {
        "modules": {
            "image": {"checkpoint": "auto"},
            "video": {"mode": "animatediff", "max_frames": 16 if profile == "high_vram" else 8},
        }
    }
    report = {
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "vram_mb": vram,
        "comfyui_path": str(comfy) if comfy else None,
        "checkpoints": checkpoints,
        "loras": loras,
        "animatediff_plugin": animatediff,
        "suggested_config": suggested_config,
        "piper_voice": voice,
    }
    log_dir = ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "install_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if comfy:
        print(f"\nComfyUI found: {comfy}")
        print("Start it before image/video generation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())