"""Anti-collapse guards for Mini Monster AI image generation."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from monster_ai.config import MiniModuleSettings
from monster_ai.modules.mini.prompts import R18Template, get_template

STABLE_TEMPLATE_ID = "stable"
EMERGENCY_TEMPLATE_ID = "stable"


def effective_template(template: R18Template, settings: MiniModuleSettings) -> R18Template:
    """VRAM-safe caps for RTX 4060 / lite_mode — reduces 爛圖 from OOM-ish collapse."""
    if not settings.lite_mode and settings.vram_profile != "mini":
        return template
    w, h = template.width, template.height
    if max(w, h) > 1024:
        w, h = 896, 1152 if template.height >= template.width else (1152, 896)
    steps = max(template.steps, 28) if template.id in ("hq", "stable", "idol_likeness") else template.steps
    cfg = min(template.cfg, 7.0)
    return replace(template, width=w, height=h, steps=steps, cfg=cfg)


def quality_passed(result: dict[str, Any], *, min_score: float) -> bool:
    q = result.get("quality") or {}
    if q.get("passed") is True:
        return True
    if q.get("passed") is False:
        score = q.get("score")
        if score is not None and float(score) >= min_score:
            return True
        return False
    return bool(result.get("ok", True))


def quality_issues(result: dict[str, Any]) -> list[str]:
    q = result.get("quality") or {}
    return [str(i) for i in (q.get("issues") or [])]