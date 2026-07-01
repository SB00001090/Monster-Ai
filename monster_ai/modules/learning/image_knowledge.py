"""Learn perfect image generation from quality archives and feedback."""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from monster_ai.config import ImageQualitySettings, LearningSettings
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.learning.store import LearningStore

if TYPE_CHECKING:
    from monster_ai.modules.image.quality_store import QualityStore

DEFAULT_QUALITY_TAGS = (
    "masterpiece",
    "best quality",
    "highly detailed",
    "sharp focus",
)

ISSUE_NEGATIVE_HINTS: dict[str, str] = {
    "black_image": "well lit, bright scene, visible subject",
    "white_image": "balanced exposure, midtones, natural lighting",
    "low_edge": "detailed textures, crisp edges, fine details",
    "oversaturated": "natural colors, balanced saturation",
    "noise_wall": "clean image, smooth gradients, low noise",
    "low_clip": "clear subject, centered composition, readable scene",
    "low_aesthetic": "professional composition, aesthetic lighting",
    "low_variance": "rich detail, varied tones, depth",
}


class ImageKnowledgeLearner:
    def __init__(
        self,
        store: LearningStore,
        quality_settings: ImageQualitySettings,
        learning_settings: LearningSettings,
        repair: SelfRepairEngine | None = None,
        quality_store: QualityStore | None = None,
    ) -> None:
        self.store = store
        self.quality_settings = quality_settings
        self.learning_settings = learning_settings
        self.repair = repair
        self.quality_store = quality_store
        self.quality_dir = Path(quality_settings.data_dir)
        self.image_dir = store.root / "image"
        self.patterns_path = self.image_dir / "patterns.json"
        self.feedback_log = self.image_dir / "feedback.jsonl"
        self.image_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self.learning_settings.enabled and self.learning_settings.image_learning_enabled

    def _load_patterns(self) -> dict[str, Any]:
        default: dict[str, Any] = {
            "learned_quality_tags": list(DEFAULT_QUALITY_TAGS),
            "issue_negative_hints": dict(ISSUE_NEGATIVE_HINTS),
            "top_checkpoints": {},
            "median_good_steps": 20,
            "median_good_cfg": 7.0,
            "good_count": 0,
            "bad_count": 0,
            "avg_good_score": 0.0,
            "auto_apply_tags": True,
            "training_ready": False,
            "training_samples": 0,
        }
        return self.store.read_json(self.patterns_path, default)

    def _save_patterns(self, data: dict[str, Any]) -> None:
        self.store.write_json(self.patterns_path, data)

    def _read_quality_log(self, limit: int = 2000) -> list[dict[str, Any]]:
        if self.quality_store is not None:
            return self.quality_store.read_log_records(limit)
        log_path = self.quality_dir / "quality_log.jsonl"
        if not log_path.is_file():
            return []
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def _extract_tags(self, prompt: str) -> list[str]:
        parts = [p.strip().lower() for p in prompt.split(",") if p.strip()]
        return parts[:20]

    def learn_from_quality_store(self) -> dict[str, Any]:
        records = self._read_quality_log()
        good = [r for r in records if r.get("label") == "good"]
        bad = [r for r in records if r.get("label") == "bad"]

        good_tag_counts: Counter[str] = Counter()
        bad_tag_counts: Counter[str] = Counter()
        issue_counts: Counter[str] = Counter()
        checkpoint_counts: Counter[str] = Counter()
        good_scores: list[float] = []
        steps_vals: list[int] = []
        cfg_vals: list[float] = []

        for rec in good:
            prompt = str(rec.get("prompt", ""))
            for tag in self._extract_tags(prompt):
                good_tag_counts[tag] += 1
            q = rec.get("quality") or {}
            if q.get("score") is not None:
                good_scores.append(float(q["score"]))
            ckpt = str(rec.get("checkpoint", ""))
            if ckpt:
                checkpoint_counts[ckpt] += 1

        for rec in bad:
            prompt = str(rec.get("prompt", ""))
            for tag in self._extract_tags(prompt):
                bad_tag_counts[tag] += 1
            q = rec.get("quality") or {}
            for issue in q.get("issues") or []:
                issue_counts[str(issue)] += 1

        learned_tags: list[str] = []
        for tag, good_n in good_tag_counts.most_common(30):
            bad_n = bad_tag_counts.get(tag, 0)
            if good_n >= 2 and good_n > bad_n:
                learned_tags.append(tag)
        if not learned_tags:
            learned_tags = list(DEFAULT_QUALITY_TAGS)

        patterns = self._load_patterns()
        patterns["learned_quality_tags"] = learned_tags[:12]
        patterns["good_count"] = len(good)
        patterns["bad_count"] = len(bad)
        patterns["avg_good_score"] = round(statistics.mean(good_scores), 4) if good_scores else 0.0
        patterns["top_checkpoints"] = dict(checkpoint_counts.most_common(5))
        patterns["common_issues"] = [
            {"issue": k, "count": v} for k, v in issue_counts.most_common(8)
        ]
        patterns["median_good_steps"] = (
            int(statistics.median(steps_vals)) if steps_vals else patterns.get("median_good_steps", 20)
        )
        patterns["median_good_cfg"] = (
            round(statistics.median(cfg_vals), 2) if cfg_vals else patterns.get("median_good_cfg", 7.0)
        )

        manifest = self._export_training_manifest()
        patterns["training_samples"] = manifest.get("count", 0)
        patterns["training_ready"] = patterns["training_samples"] >= 12

        self._save_patterns(patterns)
        self.store.append_jsonl(
            self.image_dir / "learn.jsonl",
            {
                "event": "analyze_quality_store",
                "good": len(good),
                "bad": len(bad),
                "tags_learned": len(learned_tags),
            },
        )
        return {
            "ok": True,
            "good_count": len(good),
            "bad_count": len(bad),
            "learned_tags": learned_tags[:8],
            "training_samples": patterns["training_samples"],
            "training_ready": patterns["training_ready"],
        }

    def ingest_generation(
        self,
        *,
        label: str,
        prompt: str,
        negative: str,
        report: dict[str, Any],
        checkpoint: str,
        attempt: int,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        patterns = self._load_patterns()
        if label == "good":
            patterns["good_count"] = int(patterns.get("good_count", 0)) + 1
            score = float(report.get("score", 0))
            prev = float(patterns.get("avg_good_score", 0))
            n = patterns["good_count"]
            patterns["avg_good_score"] = round((prev * (n - 1) + score) / max(n, 1), 4)
            ckpts = patterns.setdefault("top_checkpoints", {})
            ckpts[checkpoint] = int(ckpts.get(checkpoint, 0)) + 1
        else:
            patterns["bad_count"] = int(patterns.get("bad_count", 0)) + 1
            hints = patterns.setdefault("issue_negative_hints", dict(ISSUE_NEGATIVE_HINTS))
            for issue in report.get("issues") or []:
                key = str(issue)
                if key in ISSUE_NEGATIVE_HINTS:
                    hints[key] = ISSUE_NEGATIVE_HINTS[key]
        self._save_patterns(patterns)
        self.store.append_jsonl(
            self.image_dir / "ingest.jsonl",
            {
                "label": label,
                "prompt": prompt[:300],
                "checkpoint": checkpoint,
                "attempt": attempt,
                "score": report.get("score"),
                "issues": report.get("issues"),
                **(extra or {}),
            },
        )

    def enhance_prompt(self, positive: str) -> str:
        if not self.enabled or not self.quality_settings.add_quality_tags:
            return positive
        patterns = self._load_patterns()
        if not patterns.get("auto_apply_tags", True):
            return positive
        tags = patterns.get("learned_quality_tags") or list(DEFAULT_QUALITY_TAGS)
        lower = positive.lower()
        missing = [t for t in tags if t.lower() not in lower]
        if not missing:
            return positive
        prefix = ", ".join(missing[:4])
        return f"{prefix}, {positive}"

    def negative_hints_for_issues(self, issues: list[str]) -> str:
        patterns = self._load_patterns()
        hints_map = patterns.get("issue_negative_hints") or ISSUE_NEGATIVE_HINTS
        parts: list[str] = []
        for issue in issues:
            hint = hints_map.get(str(issue))
            if hint and hint not in parts:
                parts.append(hint)
        return ", ".join(parts)

    def context_hint(self, prompt: str = "") -> str:
        if not self.enabled:
            return ""
        patterns = self._load_patterns()
        lines = [
            "[Image learning] Prefer prompts and settings that historically produced high-quality images.",
        ]
        tags = patterns.get("learned_quality_tags") or []
        if tags:
            lines.append("Learned quality tags: " + ", ".join(tags[:6]))
        top_ckpt = patterns.get("top_checkpoints") or {}
        if top_ckpt:
            best = max(top_ckpt.items(), key=lambda x: x[1])[0]
            lines.append(f"Best checkpoint trend: {best}")
        issues = patterns.get("common_issues") or []
        if issues:
            top_issue = issues[0].get("issue")
            hint = (patterns.get("issue_negative_hints") or {}).get(top_issue)
            if hint:
                lines.append(f"Avoid frequent issue '{top_issue}' using: {hint}")
        if patterns.get("training_ready"):
            lines.append("Training dataset ready — anti-collapse LoRA can be refreshed.")
        return "\n".join(lines)

    def suggested_params(self) -> dict[str, Any]:
        patterns = self._load_patterns()
        top_ckpt = patterns.get("top_checkpoints") or {}
        best_ckpt = max(top_ckpt.items(), key=lambda x: x[1])[0] if top_ckpt else None
        return {
            "steps": patterns.get("median_good_steps", 20),
            "cfg": patterns.get("median_good_cfg", 7.0),
            "checkpoint": best_ckpt,
            "quality_tags": patterns.get("learned_quality_tags", [])[:6],
        }

    def record_feedback(
        self,
        *,
        user_id: str,
        image_id: str,
        thumbs: str | None = None,
        rating: int | None = None,
        comment: str = "",
        prompt: str = "",
    ) -> dict[str, Any]:
        rec = {
            "user_id": user_id,
            "image_id": image_id,
            "thumbs": thumbs,
            "rating": rating,
            "comment": comment,
            "prompt": prompt[:400],
        }
        self.store.append_jsonl(self.feedback_log, rec)
        if thumbs == "up" and prompt:
            patterns = self._load_patterns()
            tags = patterns.setdefault("learned_quality_tags", list(DEFAULT_QUALITY_TAGS))
            for tag in self._extract_tags(prompt):
                if tag not in tags and len(tags) < 16:
                    tags.append(tag)
            patterns["learned_quality_tags"] = tags
            self._save_patterns(patterns)
        return {"ok": True, "record": rec}

    def _export_training_manifest(self) -> dict[str, Any]:
        root = self.store.root.parent.parent
        script = root / "scripts" / "export_training_dataset.py"
        if script.is_file():
            try:
                subprocess.run(
                    [sys.executable, str(script)],
                    cwd=str(root),
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass
        manifest = root / "data" / "training" / "manifests" / "training_manifest.json"
        if not manifest.is_file():
            return {"count": 0, "path": str(manifest)}
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return {"count": data.get("count", 0), "path": str(manifest)}
        except (OSError, json.JSONDecodeError):
            return {"count": 0, "path": str(manifest)}

    def status(self) -> dict[str, Any]:
        patterns = self._load_patterns()
        manifest = self._export_training_manifest()
        return {
            "enabled": self.enabled,
            "good_count": patterns.get("good_count", 0),
            "bad_count": patterns.get("bad_count", 0),
            "avg_good_score": patterns.get("avg_good_score", 0),
            "learned_tags": patterns.get("learned_quality_tags", [])[:8],
            "top_checkpoints": patterns.get("top_checkpoints", {}),
            "common_issues": patterns.get("common_issues", []),
            "training_samples": manifest.get("count", 0),
            "training_ready": patterns.get("training_ready", False),
            "suggested_params": self.suggested_params(),
        }