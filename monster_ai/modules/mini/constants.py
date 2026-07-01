"""Mini Monster AI constants."""
from __future__ import annotations

PRODUCT_NAME = "Mini Monster AI"
VERSION = "1.0.0"
DEVELOPER = "Suckbob"
TARGET_SUCCESS_RATE = 0.98
TARGET_LIKENESS_SIMILARITY = 0.98
TARGET_DEADLINE = "2026-09-01"

# Checkpoint name hints (substring match against ComfyUI checkpoints/)
RECOMMENDED_CHECKPOINTS: tuple[str, ...] = (
    "juggernaut",
    "realvis",
    "cyberrealistic",
    "pony",
    "biglust",
    "flux",
    "illustrious",
    "noobai",
)

RECOMMENDED_LORAS: tuple[str, ...] = (
    "detail",
    "skin",
    "anatomy",
    "anti_collapse",
    "hands",
    "face",
)