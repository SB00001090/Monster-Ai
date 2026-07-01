"""Quality tier labels — fail <70%, pass 70–85%, high >=85%."""

from __future__ import annotations

FAIL_THRESHOLD = 0.70
HIGH_THRESHOLD = 0.85


def quality_tier(score: float | None, *, passed: bool | None = None) -> str:
    if score is None:
        return "unknown" if passed is None else ("pass" if passed else "fail")
    if score < FAIL_THRESHOLD:
        return "fail"
    if score >= HIGH_THRESHOLD:
        return "high"
    return "pass"


def enrich_quality_dict(report: dict, *, high_threshold: float = HIGH_THRESHOLD) -> dict:
    score = report.get("score")
    passed = report.get("passed")
    tier = quality_tier(float(score) if score is not None else None, passed=passed)
    if score is not None and float(score) >= high_threshold:
        tier = "high"
    out = {**report, "tier": tier, "high_quality": tier == "high"}
    out["thresholds"] = {"fail_below": FAIL_THRESHOLD, "high_above": high_threshold}
    return out