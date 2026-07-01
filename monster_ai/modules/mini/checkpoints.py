"""Resolve best available checkpoint/LoRA for Mini Monster AI."""
from __future__ import annotations

from monster_ai.modules.mini.constants import RECOMMENDED_CHECKPOINTS, RECOMMENDED_LORAS
from monster_ai.modules.image.checkpoint_resolver import resolve_checkpoint, AUTO


def pick_checkpoint(requested: str, available: list[str]) -> tuple[str, str | None]:
    if requested and requested != AUTO:
        return resolve_checkpoint(requested, available)
    for hint in RECOMMENDED_CHECKPOINTS:
        hint_l = hint.lower()
        for name in available:
            if hint_l in name.lower():
                return name, None
    return resolve_checkpoint(AUTO, available)


def pick_lora(requested: str | None, available: list[str]) -> str | None:
    if requested:
        req_l = requested.lower()
        for name in available:
            if req_l in name.lower():
                return name
    for hint in RECOMMENDED_LORAS:
        hint_l = hint.lower()
        for name in available:
            if hint_l in name.lower():
                return name
    return None