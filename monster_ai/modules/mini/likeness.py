"""Likeness control — reference images, IP-Adapter prompts, idol fan-work alignment."""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

LIKENESS_TEMPLATE_ID = "idol_likeness"
TARGET_LIKENESS = 0.98

LIKENESS_PREFIX = (
    "same person as reference, identical face, exact facial features, "
    "matching face shape, same eyes nose lips, consistent identity, "
    "high face similarity, portrait likeness, "
)

LIKENESS_SUFFIX = (
    "photorealistic, anatomically correct, natural skin texture, "
    "coherent body proportions, sharp focus, 8k uhd"
)

LIKENESS_NEGATIVE_EXTRA = (
    "different person, face swap artifact, inconsistent face, "
    "wrong identity, celebrity lookalike mismatch, deformed face, "
    "asymmetric eyes, plastic skin"
)


@dataclass
class ReferenceProfile:
    id: str
    name: str
    image_path: Path
    voice_path: Path | None = None
    likeness_lora: str | None = None
    notes: str = ""


class ReferenceStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.ref_dir = self.root / "references"
        self.meta_path = self.root / "references.json"
        self.ref_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.meta_path.is_file():
            return {"profiles": {}}
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def register(
        self,
        *,
        name: str,
        image_bytes: bytes,
        image_ext: str = ".png",
        voice_bytes: bytes | None = None,
        voice_ext: str = ".wav",
        likeness_lora: str | None = None,
        notes: str = "",
    ) -> ReferenceProfile:
        ref_id = uuid.uuid4().hex[:12]
        img_path = self.ref_dir / f"{ref_id}_face{image_ext}"
        img_path.write_bytes(image_bytes)
        voice_path = None
        if voice_bytes:
            voice_path = self.ref_dir / f"{ref_id}_voice{voice_ext}"
            voice_path.write_bytes(voice_bytes)

        profile = ReferenceProfile(
            id=ref_id,
            name=name,
            image_path=img_path,
            voice_path=voice_path,
            likeness_lora=likeness_lora,
            notes=notes,
        )
        data = self._load()
        data["profiles"][ref_id] = {
            "id": ref_id,
            "name": name,
            "image": str(img_path),
            "voice": str(voice_path) if voice_path else None,
            "likeness_lora": likeness_lora,
            "notes": notes,
        }
        self._save(data)
        return profile

    def get(self, ref_id: str) -> ReferenceProfile | None:
        data = self._load()
        row = data.get("profiles", {}).get(ref_id)
        if not row:
            return None
        return ReferenceProfile(
            id=row["id"],
            name=row["name"],
            image_path=Path(row["image"]),
            voice_path=Path(row["voice"]) if row.get("voice") else None,
            likeness_lora=row.get("likeness_lora"),
            notes=row.get("notes", ""),
        )

    def list_profiles(self) -> list[dict[str, Any]]:
        data = self._load()
        out = []
        for row in data.get("profiles", {}).values():
            out.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "has_voice": bool(row.get("voice")),
                    "likeness_lora": row.get("likeness_lora"),
                }
            )
        return out


async def comfy_has_node(base_url: str, class_type: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{base_url.rstrip('/')}/object_info/{class_type}")
            return r.status_code == 200 and bool(r.json())
    except httpx.HTTPError:
        return False


def build_likeness_prompt(user_prompt: str, profile: ReferenceProfile) -> str:
    identity = f"character {profile.name}, " if profile.name else ""
    return f"{LIKENESS_PREFIX}{identity}{user_prompt.strip()}, {LIKENESS_SUFFIX}"


def build_likeness_negative(base_negative: str) -> str:
    return f"{base_negative}, {LIKENESS_NEGATIVE_EXTRA}"


def stage_reference_for_comfy(profile: ReferenceProfile, comfy_input: Path) -> str:
    """Copy reference into ComfyUI input folder; return filename for LoadImage."""
    comfy_input.mkdir(parents=True, exist_ok=True)
    dest_name = f"mini_ref_{profile.id}{profile.image_path.suffix}"
    dest = comfy_input / dest_name
    shutil.copy2(profile.image_path, dest)
    return dest_name


def build_ipadapter_workflow(
    *,
    positive: str,
    negative: str,
    checkpoint: str,
    reference_filename: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    ip_weight: float = 0.85,
    lora_name: str | None = None,
    lora_strength: float = 0.8,
) -> dict[str, Any]:
    """ComfyUI IP-Adapter FaceID-style workflow (requires custom nodes installed)."""
    wf: dict[str, Any] = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "11": {
            "class_type": "LoadImage",
            "inputs": {"image": reference_filename},
        },
        "12": {
            "class_type": "IPAdapterUnifiedLoader",
            "inputs": {"model": ["4", 0], "preset": "FACEID PLUS V2"},
        },
        "13": {
            "class_type": "IPAdapter",
            "inputs": {
                "model": ["12", 0],
                "ipadapter": ["12", 1],
                "image": ["11", 0],
                "weight": ip_weight,
                "start_at": 0.0,
                "end_at": 1.0,
                "weight_type": "standard",
            },
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1,
                "model": ["13", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "mini_likeness", "images": ["8", 0]},
        },
    }
    if lora_name:
        wf["10"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["4", 0],
                "clip": ["4", 1],
            },
        }
        wf["12"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
    return wf