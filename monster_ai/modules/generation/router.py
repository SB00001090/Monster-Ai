"""Route image generation across SD / Flux / Pony backends with VAE and FHD–8K policy."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Full HD minimum, 8K maximum (16:9 reference)
MIN_WIDTH = 1920
MIN_HEIGHT = 1080
MAX_WIDTH = 7680
MAX_HEIGHT = 4320

ASPECT_PRESETS: tuple[tuple[str, int, int], ...] = (
    ("fhd_16_9", 1920, 1080),
    ("qhd_16_9", 2560, 1440),
    ("4k_16_9", 3840, 2160),
    ("4k_1_1", 4096, 4096),
    ("8k_16_9", 7680, 4320),
)


@dataclass(frozen=True)
class GenerationBackend:
    id: str
    label: str
    label_zh: str
    checkpoint_hints: tuple[str, ...]
    default_vae: str
    native_max_width: int
    native_max_height: int
    workflow_template: str


BACKENDS: tuple[GenerationBackend, ...] = (
    GenerationBackend(
        id="sd15",
        label="Stable Diffusion 1.5",
        label_zh="SD 1.5",
        checkpoint_hints=("v1-5", "sd15", "1.5", "pruned", "sd_v1", "dreamshaper", "anything"),
        default_vae="sd-vae-ft-mse.safetensors",
        native_max_width=1920,
        native_max_height=1080,
        workflow_template="sd15_txt2img",
    ),
    GenerationBackend(
        id="sdxl",
        label="SDXL",
        label_zh="SDXL",
        checkpoint_hints=("sdxl", "xl", "juggernaut", "cyberrealistic"),
        default_vae="sdxl_vae.safetensors",
        native_max_width=3840,
        native_max_height=2160,
        workflow_template="sdxl_txt2img",
    ),
    GenerationBackend(
        id="flux",
        label="Flux",
        label_zh="Flux",
        checkpoint_hints=("flux", "flux1", "schnell", "dev"),
        default_vae="ae.safetensors",
        native_max_width=4096,
        native_max_height=4096,
        workflow_template="sdxl_txt2img",
    ),
    GenerationBackend(
        id="pony",
        label="Pony Diffusion",
        label_zh="Pony",
        checkpoint_hints=("pony", "illustrious", "ponydiffusion"),
        default_vae="pony_vae.safetensors",
        native_max_width=2048,
        native_max_height=2048,
        workflow_template="sdxl_txt2img",
    ),
)


def get_backend(backend_id: str | None) -> GenerationBackend:
    if not backend_id:
        return BACKENDS[0]
    key = backend_id.lower().strip()
    for backend in BACKENDS:
        if backend.id == key:
            return backend
    return BACKENDS[0]


def clamp_resolution(width: int | None, height: int | None) -> tuple[int, int, dict[str, Any]]:
    """Enforce Full HD floor and 8K ceiling while preserving aspect ratio."""
    w = width or MIN_WIDTH
    h = height or MIN_HEIGHT
    meta: dict[str, Any] = {"clamped": False, "upscale_recommended": False}

    if w < MIN_WIDTH or h < MIN_HEIGHT:
        scale = max(MIN_WIDTH / max(w, 1), MIN_HEIGHT / max(h, 1))
        w = max(MIN_WIDTH, int(math.ceil(w * scale)))
        h = max(MIN_HEIGHT, int(math.ceil(h * scale)))
        meta["clamped"] = True
        meta["reason"] = "below_fhd_minimum"

    if w > MAX_WIDTH or h > MAX_HEIGHT:
        scale = min(MAX_WIDTH / w, MAX_HEIGHT / h)
        w = min(MAX_WIDTH, int(math.floor(w * scale)))
        h = min(MAX_HEIGHT, int(math.floor(h * scale)))
        meta["clamped"] = True
        meta["reason"] = "above_8k_maximum"

    return w, h, meta


def match_checkpoint(backend: GenerationBackend, available: list[str]) -> str | None:
    for hint in backend.checkpoint_hints:
        hint_l = hint.lower()
        for name in available:
            if hint_l in name.lower():
                return name
    return None


def resolve_vae(backend: GenerationBackend, vae: str | None, available_vaes: list[str] | None = None) -> str:
    if vae and vae.lower() not in ("auto", ""):
        return vae
    if available_vaes:
        for candidate in (backend.default_vae, "vae", "ae"):
            for name in available_vaes:
                if candidate.lower() in name.lower():
                    return name
    return backend.default_vae


class GenerationRouter:
    """Select backend checkpoint, VAE, and resolution for ComfyUI generation."""

    def __init__(self, default_backend: str = "sd15") -> None:
        self.default_backend = default_backend

    def list_backends(self, available_checkpoints: list[str] | None = None) -> list[dict[str, Any]]:
        ckpts = available_checkpoints or []
        items: list[dict[str, Any]] = []
        for backend in BACKENDS:
            matched = match_checkpoint(backend, ckpts) if ckpts else None
            items.append(
                {
                    "id": backend.id,
                    "label": backend.label,
                    "label_zh": backend.label_zh,
                    "default_vae": backend.default_vae,
                    "native_max": {"width": backend.native_max_width, "height": backend.native_max_height},
                    "workflow_template": backend.workflow_template,
                    "checkpoint": matched,
                    "available": matched is not None if ckpts else None,
                }
            )
        return items

    def list_resolutions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": preset_id,
                "width": w,
                "height": h,
                "within_policy": w <= MAX_WIDTH and h <= MAX_HEIGHT and w >= MIN_WIDTH and h >= MIN_HEIGHT,
            }
            for preset_id, w, h in ASPECT_PRESETS
        ]

    def resolve(
        self,
        *,
        backend_id: str | None = None,
        vae: str | None = None,
        width: int | None = None,
        height: int | None = None,
        checkpoint: str | None = None,
        available_checkpoints: list[str] | None = None,
        available_vaes: list[str] | None = None,
    ) -> dict[str, Any]:
        backend = get_backend(backend_id or self.default_backend)
        ckpts = available_checkpoints or []
        warning: str | None = None

        resolved_ckpt = checkpoint
        if not resolved_ckpt and ckpts:
            resolved_ckpt = match_checkpoint(backend, ckpts)
        if not resolved_ckpt and ckpts:
            resolved_ckpt = ckpts[0]
            warning = (
                f"Backend '{backend.label_zh}' checkpoint not found; using '{resolved_ckpt}'. "
                "Install matching .safetensors in ComfyUI/models/checkpoints/"
            )

        w, h, clamp_meta = clamp_resolution(width, height)
        upscale = w > backend.native_max_width or h > backend.native_max_height
        resolved_vae = resolve_vae(backend, vae, available_vaes)

        return {
            "backend": backend.id,
            "backend_label": backend.label_zh,
            "checkpoint": resolved_ckpt,
            "vae": resolved_vae,
            "width": w,
            "height": h,
            "workflow_template": backend.workflow_template,
            "upscale_recommended": upscale,
            "resolution_policy": {
                "min": {"width": MIN_WIDTH, "height": MIN_HEIGHT},
                "max": {"width": MAX_WIDTH, "height": MAX_HEIGHT},
                **clamp_meta,
            },
            "warning": warning,
        }