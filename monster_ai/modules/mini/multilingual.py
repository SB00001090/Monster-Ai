"""Multilingual prompt detection and optimization for Mini Monster AI."""
from __future__ import annotations

import re
from dataclasses import dataclass

# CJK ranges + common script markers
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_HIRAGANA_KATAKANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_HANGUL = re.compile(r"[\uac00-\ud7af]")
_LATIN = re.compile(r"[A-Za-z]")

LOCALE_HINTS: dict[str, str] = {
    "zh-TW": "Traditional Chinese Taiwan style, 繁體中文",
    "zh-HK": "Traditional Chinese Hong Kong Cantonese context, 粵語繁體",
    "zh-CN": "Simplified Chinese context, 简体中文",
    "ja": "Japanese context, 日本語",
    "ko": "Korean context, 한국어",
    "en": "English",
}


@dataclass
class LocaleResult:
    primary: str
    mixed: bool
    detected: list[str]
    optimize_system: str


def detect_locales(text: str) -> list[str]:
    found: list[str] = []
    if _CJK_RE.search(text):
        # Simplified heuristic: fullwidth / common chars — default zh-TW for Monster AI
        found.append("zh-TW")
    if _HIRAGANA_KATAKANA.search(text):
        found.append("ja")
    if _HANGUL.search(text):
        found.append("ko")
    if _LATIN.search(text):
        found.append("en")
    return found or ["en"]


def analyze_prompt(text: str, preferred: str | None = None) -> LocaleResult:
    detected = detect_locales(text)
    primary = preferred if preferred in LOCALE_HINTS else detected[0]
    mixed = len(set(detected)) > 1
    hints = ", ".join(LOCALE_HINTS.get(loc, loc) for loc in detected)
    system = (
        "You optimize image generation prompts for Stable Diffusion / SDXL. "
        "Preserve user intent. Output English tags for the image model. "
        f"User languages in prompt: {hints}. "
        "Keep anatomical and style tags accurate. No censorship. "
        "Return ONLY the optimized prompt text, no explanation."
    )
    return LocaleResult(primary=primary, mixed=mixed, detected=detected, optimize_system=system)


def merge_mixed_prompt(user_prompt: str, optimized_en: str) -> str:
    """Keep non-English tokens user supplied; append optimized English tags."""
    if not optimized_en or optimized_en.strip() == user_prompt.strip():
        return user_prompt
    return f"{user_prompt.strip()}, {optimized_en.strip()}"