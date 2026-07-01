"""Schedule windows for autonomous Guardian network learning."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_WINDOW_RE = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")


def parse_window(spec: str) -> tuple[int, int, int, int] | None:
    m = _WINDOW_RE.match(spec.strip())
    if not m:
        return None
    sh, sm, eh, em = (int(m.group(i)) for i in range(1, 5))
    if not (0 <= sh < 24 and 0 <= sm < 60 and 0 <= eh < 24 and 0 <= em < 60):
        return None
    return sh, sm, eh, em


class LearningScheduler:
    def __init__(self, windows: list[str], *, min_hours_between_runs: float = 6.0) -> None:
        self._windows = [w for w in windows if parse_window(w)]
        self.min_hours_between_runs = min_hours_between_runs

    def in_window(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        minutes = now.hour * 60 + now.minute
        for spec in self._windows:
            parsed = parse_window(spec)
            if not parsed:
                continue
            sh, sm, eh, em = parsed
            start = sh * 60 + sm
            end = eh * 60 + em
            if start <= end:
                if start <= minutes < end:
                    return True
            elif minutes >= start or minutes < end:
                return True
        return False

    def status(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now()
        return {
            "windows": list(self._windows),
            "in_window": self.in_window(now),
            "next_window_hint": self._windows[0] if self._windows else None,
            "min_hours_between_runs": self.min_hours_between_runs,
        }

    def should_run(
        self,
        *,
        consented: bool,
        enabled: bool,
        last_run_at: float | None,
        force: bool = False,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        if not enabled:
            return False, "network_learning_disabled"
        if not consented:
            return False, "consent_required"
        if force:
            return True, ""
        if not self.in_window(now):
            return False, "outside_schedule_window"
        if last_run_at is not None:
            age_h = (datetime.now(timezone.utc).timestamp() - last_run_at) / 3600
            if age_h < self.min_hours_between_runs:
                return False, "cooldown_active"
        return True, ""