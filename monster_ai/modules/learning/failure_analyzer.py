"""Analyze quality failures and surface evolution hints."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from monster_ai.modules.learning.store import LearningStore


class FailureAnalyzer:
    def __init__(self, store: LearningStore) -> None:
        self.store = store

    def _read_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        path = self.store.failures_log
        if not path.is_file():
            return []
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def summarize(self, limit: int = 50) -> dict[str, Any]:
        records = self._read_recent(limit)
        reasons: Counter[str] = Counter()
        for rec in records:
            for report in rec.get("reports") or []:
                for reason in report.get("reasons") or []:
                    reasons[str(reason)] += 1
        top = reasons.most_common(5)
        return {
            "failure_count": len(records),
            "top_reasons": [{"reason": r, "count": c} for r, c in top],
        }

    def context_hint(self, limit: int = 20) -> str:
        summary = self.summarize(limit)
        if not summary["top_reasons"]:
            return ""
        items = ", ".join(f"{r['reason']}({r['count']})" for r in summary["top_reasons"][:3])
        return (
            "[Evolution hint] Recent quality failures were often due to: "
            f"{items}. Prioritize fixing these patterns in your next reply."
        )

    def suggest_min_quality_adjustment(self, current: float) -> float | None:
        summary = self.summarize()
        count = summary["failure_count"]
        if count >= 10:
            return max(0.35, round(current - 0.05, 2))
        if count <= 1 and current < 0.65:
            return min(0.75, round(current + 0.02, 2))
        return None