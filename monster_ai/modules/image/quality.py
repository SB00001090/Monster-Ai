"""Image quality scoring — rule-based checks and optional ML scores."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np
from PIL import Image

from monster_ai.config import ImageQualitySettings
from monster_ai.core.generation_repair import validate_image_file

logger = logging.getLogger(__name__)


class QualityIssue(str, Enum):
    CORRUPT = "corrupt"
    BLACK_IMAGE = "black_image"
    WHITE_IMAGE = "white_image"
    LOW_VARIANCE = "low_variance"
    LOW_ENTROPY = "low_entropy"
    OVERSATURATED = "oversaturated"
    LOW_EDGE = "low_edge"
    NOISE_WALL = "noise_wall"
    LOW_CLIP = "low_clip"
    LOW_AESTHETIC = "low_aesthetic"


HARD_FAIL = frozenset(
    {
        QualityIssue.CORRUPT,
        QualityIssue.BLACK_IMAGE,
        QualityIssue.WHITE_IMAGE,
        QualityIssue.LOW_VARIANCE,
        QualityIssue.LOW_ENTROPY,
        QualityIssue.NOISE_WALL,
        QualityIssue.LOW_EDGE,
    }
)


@dataclass
class QualityReport:
    passed: bool
    score: float
    issues: list[QualityIssue] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    clip_score: float | None = None
    aesthetic_score: float | None = None
    rule_score: float = 1.0

    def to_dict(self) -> dict:
        from monster_ai.modules.image.quality_tiers import enrich_quality_dict

        base = {
            "passed": self.passed,
            "score": round(self.score, 4),
            "issues": [i.value for i in self.issues],
            "reasons": self.reasons,
            "clip_score": self.clip_score,
            "aesthetic_score": self.aesthetic_score,
            "rule_score": round(self.rule_score, 4),
        }
        return enrich_quality_dict(base)


def _load_rgb_array(path: Path, max_side: int = 512) -> np.ndarray:
    with Image.open(path) as img:
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
        return np.asarray(img, dtype=np.float32)


def _shannon_entropy(gray: np.ndarray) -> float:
    hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 255))
    hist = hist.astype(np.float64)
    hist = hist[hist > 0]
    if hist.size == 0:
        return 0.0
    prob = hist / hist.sum()
    return float(-np.sum(prob * np.log2(prob)))


def _sobel_edge_density(gray: np.ndarray) -> float:
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[1:-1, 1:-1] = (
        -gray[:-2, :-2] - 2 * gray[:-2, 1:-1] - gray[:-2, 2:]
        + gray[2:, :-2] + 2 * gray[2:, 1:-1] + gray[2:, 2:]
    )
    gy[1:-1, 1:-1] = (
        -gray[:-2, :-2] - 2 * gray[1:-1, :-2] - gray[2:, :-2]
        + gray[:-2, 2:] + 2 * gray[1:-1, 2:] + gray[2:, 2:]
    )
    magnitude = np.sqrt(gx * gx + gy * gy)
    return float((magnitude > 30).mean())


class _MLScorer:
    """Lazy-loaded CLIP + aesthetic predictor (CPU only)."""

    def __init__(self, device: str = "cpu") -> None:
        self._device = device
        self._clip = None
        self._preprocess = None
        self._tokenizer = None
        self._aesthetic = None
        self._load_failed = False

    def _ensure_clip(self) -> bool:
        if self._load_failed:
            return False
        if self._clip is not None:
            return True
        try:
            import open_clip
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="laion2b_s34b_b79k"
            )
            model.eval()
            self._clip = model.to(self._device)
            self._preprocess = preprocess
            self._tokenizer = open_clip.get_tokenizer("ViT-B-32")
            self._torch = torch
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("CLIP scorer unavailable: %s", exc)
            self._load_failed = True
            return False

    def clip_score(self, path: Path, prompt: str) -> float | None:
        if not self._ensure_clip():
            return None
        try:
            torch = self._torch
            with Image.open(path) as img:
                image = self._preprocess(img.convert("RGB")).unsqueeze(0).to(self._device)
            tokens = self._tokenizer([prompt]).to(self._device)
            with torch.no_grad():
                image_features = self._clip.encode_image(image)
                text_features = self._clip.encode_text(tokens)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                sim = (image_features @ text_features.T).item()
            return float(sim)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CLIP scoring failed: %s", exc)
            return None

    def aesthetic_score(self, path: Path) -> float | None:
        if not self._ensure_clip():
            return None
        try:
            import torch
            import torch.nn as nn

            if self._aesthetic is None:
                self._aesthetic = nn.Linear(512, 1)
                try:
                    import httpx

                    url = (
                        "https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s12B-b42K"
                        "/resolve/main/aesthetic-model.pth"
                    )
                    r = httpx.get(url, follow_redirects=True, timeout=60)
                    if r.status_code == 200:
                        state = torch.load(
                            __import__("io").BytesIO(r.content), map_location=self._device
                        )
                        self._aesthetic.load_state_dict(state)
                except Exception:  # noqa: BLE001
                    pass
                self._aesthetic.eval().to(self._device)

            with Image.open(path) as img:
                image = self._preprocess(img.convert("RGB")).unsqueeze(0).to(self._device)
            with torch.no_grad():
                features = self._clip.encode_image(image)
                features /= features.norm(dim=-1, keepdim=True)
                score = self._aesthetic(features.float()).item()
            return float(score)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Aesthetic scoring failed: %s", exc)
            return None


class ImageQualityScorer:
    def __init__(self, settings: ImageQualitySettings) -> None:
        self.settings = settings
        self._ml: _MLScorer | None = None

    def _ml_scorer(self) -> _MLScorer:
        if self._ml is None:
            self._ml = _MLScorer(device=self.settings.device)
        return self._ml

    def evaluate(self, path: Path, prompt: str = "") -> QualityReport:
        issues: list[QualityIssue] = []
        reasons: list[str] = []
        rule_score = 1.0

        if not validate_image_file(path, min_bytes=64):
            return QualityReport(
                passed=False,
                score=0.0,
                issues=[QualityIssue.CORRUPT],
                reasons=["File corrupt or unreadable"],
                rule_score=0.0,
            )

        try:
            arr = _load_rgb_array(path)
        except OSError as exc:
            return QualityReport(
                passed=False,
                score=0.0,
                issues=[QualityIssue.CORRUPT],
                reasons=[str(exc)],
                rule_score=0.0,
            )

        gray = arr.mean(axis=2)
        brightness = float(gray.mean())
        brightness_std = float(gray.std())
        channel_var = float(arr.var(axis=(0, 1)).mean())
        entropy = _shannon_entropy(gray)
        edge_density = _sobel_edge_density(gray)

        if brightness < 8 and brightness_std < 5:
            if not (self.settings.allow_dark_style and brightness_std >= 2):
                issues.append(QualityIssue.BLACK_IMAGE)
                reasons.append(f"Near-black image (brightness={brightness:.1f})")
                rule_score -= 0.5

        if brightness > 247 and brightness_std < 5:
            issues.append(QualityIssue.WHITE_IMAGE)
            reasons.append(f"Near-white image (brightness={brightness:.1f})")
            rule_score -= 0.5

        if channel_var < 12:
            issues.append(QualityIssue.LOW_VARIANCE)
            reasons.append(f"Very low color variance ({channel_var:.1f})")
            rule_score -= 0.4

        if entropy < 2.5:
            issues.append(QualityIssue.LOW_ENTROPY)
            reasons.append(f"Low information entropy ({entropy:.2f})")
            rule_score -= 0.35

        if not self.settings.allow_high_saturation:
            max_c = arr.max(axis=2)
            min_c = arr.min(axis=2)
            denom = np.maximum(max_c, 1.0)
            saturation = (max_c - min_c) / denom
            sat_mean = float(saturation.mean())
            if sat_mean > 0.92:
                issues.append(QualityIssue.OVERSATURATED)
                reasons.append(f"Oversaturated (mean sat={sat_mean:.2f})")
                rule_score -= 0.2

        if edge_density < 0.01:
            issues.append(QualityIssue.LOW_EDGE)
            reasons.append(f"Very blurry or flat (edge density={edge_density:.4f})")
            rule_score -= 0.15

        if edge_density > 0.45 and entropy > 6.5:
            issues.append(QualityIssue.NOISE_WALL)
            reasons.append("High-frequency noise wall detected")
            rule_score -= 0.4

        rule_score = max(0.0, min(1.0, rule_score))

        clip_score: float | None = None
        aesthetic_score: float | None = None
        mode = self.settings.mode

        if mode in ("light", "full") and prompt:
            clip_score = self._ml_scorer().clip_score(path, prompt)
            if clip_score is not None and clip_score < self.settings.min_clip_score:
                issues.append(QualityIssue.LOW_CLIP)
                reasons.append(
                    f"Low CLIP alignment ({clip_score:.3f} < {self.settings.min_clip_score})"
                )
                rule_score = min(rule_score, 0.5)

        if mode == "full":
            aesthetic_score = self._ml_scorer().aesthetic_score(path)
            if aesthetic_score is not None and aesthetic_score < self.settings.min_aesthetic:
                issues.append(QualityIssue.LOW_AESTHETIC)
                reasons.append(
                    f"Low aesthetic score ({aesthetic_score:.2f} < {self.settings.min_aesthetic})"
                )
                rule_score = min(rule_score, 0.55)

        hard_fail = any(i in HARD_FAIL for i in issues)
        soft_fail = any(
            i in (QualityIssue.LOW_CLIP, QualityIssue.LOW_AESTHETIC, QualityIssue.OVERSATURATED)
            for i in issues
        )
        passed = not hard_fail and not soft_fail

        overall = rule_score
        if clip_score is not None:
            overall = 0.6 * overall + 0.4 * min(1.0, clip_score / 0.35)
        if aesthetic_score is not None:
            overall = 0.7 * overall + 0.3 * min(1.0, aesthetic_score / 7.0)

        return QualityReport(
            passed=passed,
            score=overall,
            issues=issues,
            reasons=reasons,
            clip_score=clip_score,
            aesthetic_score=aesthetic_score,
            rule_score=rule_score,
        )