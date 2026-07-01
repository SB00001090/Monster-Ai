"""LoRA training launcher — exports dataset from image quality learning."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from monster_ai.config import Settings


class TrainingService:
    name = "training"

    def __init__(self, settings: Settings, root: Path | None = None) -> None:
        self.settings = settings
        self.root = root or Path(".")

    def _manifest_count(self) -> int:
        manifest = self.root / "data" / "training" / "manifests" / "training_manifest.json"
        if not manifest.is_file():
            return 0
        try:
            return int(json.loads(manifest.read_text(encoding="utf-8")).get("count", 0))
        except (OSError, json.JSONDecodeError, TypeError):
            return 0

    async def export_dataset(self) -> dict[str, Any]:
        script = self.root / "scripts" / "export_training_dataset.py"
        if not script.is_file():
            return {"ok": False, "reason": "export_script_missing"}
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "ok": proc.returncode == 0,
            "samples": self._manifest_count(),
            "stdout": (proc.stdout or "")[-500:],
        }

    async def health(self) -> dict[str, Any]:
        samples = self._manifest_count()
        if not self.settings.modules.training.enabled:
            return {
                "enabled": False,
                "healthy": samples >= 12,
                "samples": samples,
                "message": "Training module disabled — image learning still archives samples",
            }
        ready = samples >= 12
        return {
            "enabled": True,
            "healthy": ready,
            "samples": samples,
            "message": (
                "Ready for train_image_quality_4060.py"
                if ready
                else f"Need {12 - samples} more good image samples"
            ),
        }