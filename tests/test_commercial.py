"""Tests for commercial trial + pricing."""
from __future__ import annotations

from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import load_settings
from monster_ai.modules.commercial.trial import TrialManager


def test_trial_manager(tmp_path) -> None:
    tm = TrialManager(str(tmp_path))
    st = tm.start_trial()
    assert st["mode"] in ("trial", "not_started")
    assert st["trial_days"] == 7
    unlocked = tm.unlock_lifetime(token="test")
    assert unlocked["mode"] == "lifetime"


def test_pricing_regions() -> None:
    hk = TrialManager.pricing("HK")
    assert hk["currency"] == "HKD"
    us = TrialManager.pricing("US")
    assert us["lifetime"] >= 29


def test_commercial_api(tmp_path) -> None:
    settings = load_settings()
    settings.commercial.data_dir = str(tmp_path)
    settings.protection.monsterlock.enabled = False
    settings.protection.monsterlock.self_destruct_enabled = False
    app = create_app(settings)
    client = TestClient(app)
    r = client.get("/api/commercial/pricing?region=TW")
    assert r.status_code == 200
    assert r.json()["currency"] == "TWD"
    r2 = client.post("/api/commercial/trial/start")
    assert r2.status_code == 200
    assert "remaining_days" in r2.json()


def test_quality_tiers() -> None:
    from monster_ai.modules.image.quality_tiers import enrich_quality_dict, quality_tier

    assert quality_tier(0.5) == "fail"
    assert quality_tier(0.75) == "pass"
    assert quality_tier(0.9) == "high"
    d = enrich_quality_dict({"score": 0.88, "passed": True})
    assert d["tier"] == "high"
    assert d["high_quality"] is True