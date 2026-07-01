"""Track Mini Monster AI generation success rate toward 98% goal."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from monster_ai.modules.mini.constants import (
    TARGET_DEADLINE,
    TARGET_LIKENESS_SIMILARITY,
    TARGET_SUCCESS_RATE,
)


class SuccessTracker:
    def __init__(self, data_dir: str) -> None:
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.metrics_path = self.root / "metrics.jsonl"
        self.summary_path = self.root / "summary.json"

    def record(
        self,
        *,
        ok: bool,
        template_id: str,
        quality_score: float | None = None,
        issues: list[str] | None = None,
        repair_attempts: int = 0,
        locale: str = "en",
        similarity_score: float | None = None,
        mode: str = "image",
    ) -> None:
        row = {
            "ts": time.time(),
            "ok": ok,
            "template_id": template_id,
            "quality_score": quality_score,
            "similarity_score": similarity_score,
            "issues": issues or [],
            "repair_attempts": repair_attempts,
            "locale": locale,
            "mode": mode,
        }
        with self.metrics_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        if not self.metrics_path.is_file():
            return
        lines = self.metrics_path.read_text(encoding="utf-8").strip().splitlines()
        total = len(lines)
        if total == 0:
            return
        successes = 0
        scores: list[float] = []
        sim_scores: list[float] = []
        by_template: dict[str, dict[str, int]] = {}
        for ln in lines[-500:]:
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            tid = str(row.get("template_id", "unknown"))
            bucket = by_template.setdefault(tid, {"ok": 0, "total": 0})
            bucket["total"] += 1
            if row.get("ok"):
                successes += 1
                bucket["ok"] += 1
            qs = row.get("quality_score")
            if isinstance(qs, (int, float)):
                scores.append(float(qs))
            ss = row.get("similarity_score")
            if isinstance(ss, (int, float)):
                sim_scores.append(float(ss))

        window = min(total, 500)
        rate = successes / window if window else 0.0
        avg_sim = round(sum(sim_scores) / len(sim_scores), 4) if sim_scores else None
        summary = {
            "total_recorded": total,
            "window_size": window,
            "success_rate": round(rate, 4),
            "target_rate": TARGET_SUCCESS_RATE,
            "avg_likeness_similarity": avg_sim,
            "target_likeness": TARGET_LIKENESS_SIMILARITY,
            "likeness_on_track": (avg_sim or 0) >= TARGET_LIKENESS_SIMILARITY,
            "target_deadline": TARGET_DEADLINE,
            "on_track": rate >= TARGET_SUCCESS_RATE,
            "avg_quality_score": round(sum(scores) / len(scores), 3) if scores else None,
            "by_template": {
                k: {"success_rate": round(v["ok"] / max(v["total"], 1), 4), **v}
                for k, v in by_template.items()
            },
            "updated_at": time.time(),
        }
        self.summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        if self.summary_path.is_file():
            return json.loads(self.summary_path.read_text(encoding="utf-8"))
        return {
            "total_recorded": 0,
            "success_rate": 0.0,
            "target_rate": TARGET_SUCCESS_RATE,
            "target_deadline": TARGET_DEADLINE,
            "on_track": False,
        }