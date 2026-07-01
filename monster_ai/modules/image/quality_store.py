"""Archive good/bad images and append quality_log.jsonl for training."""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from monster_ai.config import ImageQualitySettings
from monster_ai.modules.image.quality import QualityReport

if TYPE_CHECKING:
    from monster_ai.modules.guardian.training_vault import TrainingVault


class QualityStore:
    def __init__(
        self,
        base_dir: str | Path,
        settings: ImageQualitySettings,
        *,
        training_vault: TrainingVault | None = None,
        encrypt_training: bool = False,
    ) -> None:
        self.base = Path(base_dir)
        self.settings = settings
        self.training_vault = training_vault
        self.encrypt_training = encrypt_training and training_vault is not None
        self.bad_dir = self.base / "bad"
        self.good_dir = self.base / "good"
        self.pending_dir = self.base / "pending"
        self.log_path = self.base / "quality_log.jsonl"
        for d in (self.bad_dir, self.good_dir, self.pending_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _archive(
        self,
        src: Path,
        dest_dir: Path,
        *,
        label: str,
        prompt: str,
        negative: str,
        report: QualityReport,
        checkpoint: str,
        attempt: int,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        stem = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        meta = {
            "id": stem,
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
            "negative": negative,
            "checkpoint": checkpoint,
            "attempt": attempt,
            "quality": report.to_dict(),
            **(extra or {}),
        }
        if self.encrypt_training and self.training_vault is not None:
            dest_enc = self.training_vault.store_image_asset(src, label=label, metadata=meta)
            self._append_log(meta)
            return dest_enc

        dest_img = dest_dir / f"{stem}.png"
        shutil.copy2(src, dest_img)
        (dest_dir / f"{stem}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._append_log(meta)
        return dest_img

    def _append_log(self, record: dict[str, Any]) -> None:
        if self.encrypt_training:
            return
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_log_records(self, limit: int = 2000) -> list[dict[str, Any]]:
        if self.encrypt_training and self.training_vault is not None:
            return self.training_vault.quality_log_records(limit)
        if not self.log_path.is_file():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def save_bad(
        self,
        src: Path,
        *,
        prompt: str,
        negative: str,
        report: QualityReport,
        checkpoint: str,
        attempt: int,
        extra: dict[str, Any] | None = None,
    ) -> Path | None:
        if not self.settings.save_bad:
            return None
        return self._archive(
            src,
            self.bad_dir,
            label="bad",
            prompt=prompt,
            negative=negative,
            report=report,
            checkpoint=checkpoint,
            attempt=attempt,
            extra=extra,
        )

    def save_good(
        self,
        src: Path,
        *,
        prompt: str,
        negative: str,
        report: QualityReport,
        checkpoint: str,
        attempt: int,
        extra: dict[str, Any] | None = None,
    ) -> Path | None:
        if not self.settings.save_good:
            return None
        return self._archive(
            src,
            self.good_dir,
            label="good",
            prompt=prompt,
            negative=negative,
            report=report,
            checkpoint=checkpoint,
            attempt=attempt,
            extra=extra,
        )