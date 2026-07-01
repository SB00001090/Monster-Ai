"""Quality tier thresholds."""
from monster_ai.modules.image.quality_tiers import FAIL_THRESHOLD, HIGH_THRESHOLD, quality_tier


def test_thresholds() -> None:
    assert FAIL_THRESHOLD == 0.70
    assert HIGH_THRESHOLD == 0.85
    assert quality_tier(0.69) == "fail"
    assert quality_tier(0.70) == "pass"
    assert quality_tier(0.85) == "high"