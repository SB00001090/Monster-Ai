"""Monster AI commercial trial — 7-day free + lifetime unlock."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

TRIAL_DAYS = 7
TRIAL_MS = TRIAL_DAYS * 24 * 60 * 60 * 1000

REGIONAL_PRICING: dict[str, dict[str, Any]] = {
    "HK": {"currency": "HKD", "lifetime": 388, "label": "香港"},
    "TW": {"currency": "TWD", "lifetime": 999, "label": "台灣"},
    "SEA": {"currency": "USD", "lifetime": 29, "label": "東南亞"},
    "US": {"currency": "USD", "lifetime": 49, "label": "美國"},
    "EU": {"currency": "EUR", "lifetime": 45, "label": "歐盟"},
    "GLOBAL": {"currency": "USD", "lifetime": 39, "label": "全球"},
}


class TrialManager:
    """Local-first trial window — no server required."""

    def __init__(self, data_dir: str) -> None:
        self.path = Path(data_dir) / "trial_state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def start_trial(self) -> dict[str, Any]:
        data = self._load()
        if data.get("lifetime_unlocked"):
            return self.status()
        if not data.get("trial_started_at"):
            data["trial_started_at"] = time.time()
            self._save(data)
        return self.status()

    def unlock_lifetime(self, *, token: str = "") -> dict[str, Any]:
        data = self._load()
        data["lifetime_unlocked"] = True
        data["unlocked_at"] = time.time()
        if token:
            data["unlock_token_hint"] = token[:8]
        self._save(data)
        return self.status()

    def status(self) -> dict[str, Any]:
        data = self._load()
        if data.get("lifetime_unlocked"):
            return {
                "active": True,
                "mode": "lifetime",
                "trial_days": TRIAL_DAYS,
                "remaining_ms": 0,
                "remaining_days": 0,
            }
        started = float(data.get("trial_started_at") or 0)
        if not started:
            return {
                "active": True,
                "mode": "not_started",
                "trial_days": TRIAL_DAYS,
                "remaining_ms": TRIAL_MS,
                "remaining_days": TRIAL_DAYS,
            }
        elapsed_ms = (time.time() - started) * 1000
        remaining = max(0, TRIAL_MS - elapsed_ms)
        active = remaining > 0
        return {
            "active": active,
            "mode": "trial" if active else "expired",
            "trial_days": TRIAL_DAYS,
            "remaining_ms": int(remaining),
            "remaining_days": round(remaining / (24 * 60 * 60 * 1000), 2),
            "started_at": started,
        }

    @staticmethod
    def pricing(region: str = "GLOBAL") -> dict[str, Any]:
        key = region.upper()
        row = REGIONAL_PRICING.get(key, REGIONAL_PRICING["GLOBAL"])
        return {
            "region": key,
            "label": row["label"],
            "currency": row["currency"],
            "lifetime": row["lifetime"],
            "trial_days": TRIAL_DAYS,
            "model": "one_time_lifetime",
            "developer": "Suckbob | Monster AI",
        }

    @staticmethod
    def all_pricing() -> list[dict[str, Any]]:
        return [TrialManager.pricing(k) for k in ("HK", "TW", "SEA", "US", "EU", "GLOBAL")]