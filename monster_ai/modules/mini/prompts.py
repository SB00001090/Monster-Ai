"""R18+ high-success prompt templates and negative prompt bundles."""
from __future__ import annotations

from dataclasses import dataclass

# Universal quality + anatomy guard negatives (defensive against collapse)
BASE_NEGATIVE = (
    "lowres, bad anatomy, bad hands, missing fingers, extra fingers, fused fingers, "
    "mutated hands, poorly drawn hands, malformed limbs, extra limbs, missing limbs, "
    "deformed, ugly, blurry, jpeg artifacts, watermark, text, logo, signature, "
    "oversaturated, overexposed, underexposed, noise, grain, duplicate, cropped, "
    "worst quality, low quality, normal quality, cartoon, 3d render, cgi, doll, "
    "plastic skin, waxy skin, cross-eye, asymmetric eyes, bad face, bad proportions, "
    "long neck, long body, disconnected limbs, floating limbs, mutation, disfigured"
)

R18_NEGATIVE_EXTRA = (
    "censored, mosaic, bar censor, blur censor, black bar, pixelated, "
    "clothing glitch, melted fabric, impossible pose, broken spine"
)

PHOTOREAL_PREFIX = (
    "photorealistic, ultra detailed, natural skin texture, subsurface scattering, "
    "soft cinematic lighting, shallow depth of field, 8k uhd, film grain subtle, "
    "professional photography, anatomically correct, coherent anatomy, "
)

PHOTOREAL_SUFFIX = (
    "sharp focus, realistic proportions, detailed eyes, natural pose, "
    "high dynamic range, color graded"
)


@dataclass(frozen=True)
class R18Template:
    id: str
    label: str
    label_zh: str
    prompt_prefix: str
    prompt_suffix: str
    negative_extra: str
    steps: int
    cfg: float
    width: int
    height: int
    upscale: bool = True


TEMPLATES: tuple[R18Template, ...] = (
    R18Template(
        id="fast",
        label="Fast R18+",
        label_zh="快速 R18+",
        prompt_prefix=PHOTOREAL_PREFIX,
        prompt_suffix=PHOTOREAL_SUFFIX + ", masterpiece",
        negative_extra=R18_NEGATIVE_EXTRA,
        steps=18,
        cfg=6.5,
        width=832,
        height=1216,
        upscale=False,
    ),
    R18Template(
        id="hq",
        label="HQ R18+",
        label_zh="高品質 R18+",
        prompt_prefix=PHOTOREAL_PREFIX,
        prompt_suffix=PHOTOREAL_SUFFIX + ", best quality, extremely detailed",
        negative_extra=R18_NEGATIVE_EXTRA,
        steps=28,
        cfg=7.0,
        width=1024,
        height=1024,
        upscale=True,
    ),
    R18Template(
        id="stable",
        label="Stable R18+ (4060)",
        label_zh="穩定 R18+（少爛圖）",
        prompt_prefix=PHOTOREAL_PREFIX,
        prompt_suffix=PHOTOREAL_SUFFIX + ", coherent anatomy, natural skin",
        negative_extra=R18_NEGATIVE_EXTRA + ", deformed, melted, extra limbs, bad hands",
        steps=32,
        cfg=6.5,
        width=896,
        height=1152,
        upscale=False,
    ),
    R18Template(
        id="portrait",
        label="Portrait R18+",
        label_zh="人像 R18+",
        prompt_prefix=PHOTOREAL_PREFIX + "portrait, face focus, ",
        prompt_suffix="detailed face, realistic eyes, skin pores, " + PHOTOREAL_SUFFIX,
        negative_extra=R18_NEGATIVE_EXTRA + ", bad face, asymmetrical face",
        steps=24,
        cfg=6.8,
        width=832,
        height=1216,
        upscale=True,
    ),
    R18Template(
        id="fullbody",
        label="Full Body R18+",
        label_zh="全身 R18+",
        prompt_prefix=PHOTOREAL_PREFIX + "full body, ",
        prompt_suffix="correct limbs, natural pose, " + PHOTOREAL_SUFFIX,
        negative_extra=R18_NEGATIVE_EXTRA + ", cropped, out of frame, missing legs",
        steps=26,
        cfg=7.0,
        width=832,
        height=1216,
        upscale=True,
    ),
    R18Template(
        id="idol_likeness",
        label="Idol Likeness R18+",
        label_zh="偶像同人極度相似",
        prompt_prefix=PHOTOREAL_PREFIX,
        prompt_suffix=PHOTOREAL_SUFFIX + ", identical face to reference, same person",
        negative_extra=R18_NEGATIVE_EXTRA + ", wrong face, different person, face mismatch",
        steps=30,
        cfg=6.8,
        width=832,
        height=1216,
        upscale=True,
    ),
)


def get_template(template_id: str | None) -> R18Template:
    fallback = next((t for t in TEMPLATES if t.id == "stable"), TEMPLATES[0])
    if not template_id:
        return fallback
    for t in TEMPLATES:
        if t.id == template_id:
            return t
    return fallback


def build_negative(template: R18Template) -> str:
    parts = [BASE_NEGATIVE]
    if template.negative_extra:
        parts.append(template.negative_extra)
    return ", ".join(parts)


def apply_template(prompt: str, template: R18Template) -> str:
    text = prompt.strip()
    if template.prompt_prefix and not text.lower().startswith(template.prompt_prefix[:20].lower()):
        text = f"{template.prompt_prefix}{text}"
    if template.prompt_suffix and template.prompt_suffix.lower() not in text.lower():
        text = f"{text}, {template.prompt_suffix}"
    return text


def list_templates_api() -> list[dict]:
    return [
        {
            "id": t.id,
            "label": t.label,
            "label_zh": t.label_zh,
            "steps": t.steps,
            "cfg": t.cfg,
            "width": t.width,
            "height": t.height,
            "upscale": t.upscale,
        }
        for t in TEMPLATES
    ]