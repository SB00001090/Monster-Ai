"""Retry and validate generation jobs (image, video, TTS)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GenerationError(Exception):
    def __init__(self, job_name: str, cause: Exception) -> None:
        self.job_name = job_name
        self.cause = cause
        super().__init__(f"{job_name} failed after retries: {cause}")


@dataclass
class GenerationRepairState:
    last_job: str | None = None
    last_error: str | None = None
    repair_count: int = 0
    last_output: str | None = None
    quality_fail_streak: int = 0
    last_quality_score: float | None = None


def is_alive_image(path: Path, *, min_bytes: int = 1024) -> bool:
    """Reject corrupt, blank, and near-dead outputs before serving."""
    if not path.exists() or path.stat().st_size < min_bytes:
        return False
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            w, h = rgb.size
            if w < 64 or h < 64:
                return False
            # Downsample for fast blank/collapse detection
            thumb = rgb.resize((max(32, w // 16), max(32, h // 16)), Image.Resampling.BILINEAR)
            gray = np.asarray(thumb.convert("RGB"), dtype=np.float32).mean(axis=2)
            if gray.size == 0:
                return False
            mean_b = float(gray.mean())
            std_b = float(gray.std())
            if mean_b < 6 and std_b < 4:
                return False
            if mean_b > 250 and std_b < 4:
                return False
            if std_b < 1.0 and (mean_b < 12 or mean_b > 245):
                return False
        return True
    except OSError:
        return False


def validate_image_file(path: Path, min_bytes: int = 1024) -> bool:
    return is_alive_image(path, min_bytes=min_bytes)


def validate_video_file(path: Path, min_bytes: int = 2048) -> bool:
    return path.exists() and path.stat().st_size >= min_bytes


def validate_audio_file(path: Path, min_bytes: int = 256) -> bool:
    return path.exists() and path.stat().st_size >= min_bytes


class GenerationRepair:
    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries
        self.state = GenerationRepairState()

    async def run(
        self,
        job_name: str,
        fn: Callable[[], Awaitable[T]],
        *,
        validate: Callable[[T], bool],
        on_retry: Callable[[int, Exception], Awaitable[None]] | None = None,
    ) -> T:
        self.state.last_job = job_name
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await fn()
                if validate(result):
                    self.state.last_error = None
                    if isinstance(result, (str, Path)):
                        self.state.last_output = str(result)
                    return result
                raise ValueError("invalid output")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self.state.last_error = str(exc)
                self.state.repair_count += 1
                logger.warning("%s attempt %s failed: %s", job_name, attempt + 1, exc)
                if attempt < self.max_retries:
                    if on_retry:
                        await on_retry(attempt, exc)
                    await asyncio.sleep(0.5 * (2**attempt))

        raise GenerationError(job_name, last_exc or RuntimeError("unknown"))