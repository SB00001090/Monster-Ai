"""Guardian autonomous network learning (G5a) tests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import GuardianNetworkLearningSettings, load_settings
from monster_ai.modules.guardian.learning_scheduler import LearningScheduler, parse_window
from monster_ai.modules.guardian.network_learning import GuardianNetworkLearner
from monster_ai.modules.guardian.privacy_firewall import (
    assert_outbound_safe,
    is_denied_read_path,
    sanitize_outbound,
    topic_anonymous_id,
)
from monster_ai.modules.guardian.grok_supervisor import GrokSupervisor


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "guardian:\n"
        "  enabled: true\n"
        "  data_dir: ./data/guardian\n"
        "  network_learning:\n"
        "    enabled: true\n"
        "    require_grok_approval: true\n"
        "    schedule_windows:\n"
        '      - "00:00-23:59"\n'
        "    max_topics_per_run: 2\n",
        encoding="utf-8",
    )
    settings = load_settings(cfg)
    settings.protection.monsterlock.enabled = False
    settings.protection.monsterlock.self_destruct_enabled = False
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_parse_window():
    assert parse_window("02:00-05:00") == (2, 0, 5, 0)
    assert parse_window("bad") is None


def test_scheduler_in_window():
    sched = LearningScheduler(["02:00-05:00"])
    assert sched.in_window(datetime(2026, 7, 1, 3, 30)) is True
    assert sched.in_window(datetime(2026, 7, 1, 12, 0)) is False


def test_privacy_firewall_denied_paths(tmp_path):
    root = tmp_path / "guardian"
    (root / "oc_fingerprints").mkdir(parents=True)
    (root / "chat_vault").mkdir(parents=True)
    assert is_denied_read_path(root / "oc_fingerprints" / "x.json", root)
    assert is_denied_read_path(root / "chat_vault" / "s1", root)
    assert not is_denied_read_path(root / "network_learning" / "runs.jsonl", root)


def test_sanitize_outbound_strips_private_fields():
    raw = {
        "topics": ["AI news", "OC Luna secret"],
        "owner_id": "user-1",
        "card": {"name": "Luna"},
        "facts_added": 3,
    }
    safe = sanitize_outbound(raw)
    assert "owner_id" not in safe
    assert "card" not in safe
    assert "topic_ids" in safe
    assert len(safe["topic_ids"]) == 2
    ok, _ = assert_outbound_safe(safe)
    assert ok


def test_topic_anonymous_id_stable():
    assert topic_anonymous_id("AI News") == topic_anonymous_id("ai news")


@pytest.mark.asyncio
async def test_network_learner_trigger_with_mock_web(tmp_path):
    root = tmp_path / "guardian"
    root.mkdir(parents=True)
    supervisor = GrokSupervisor(root)
    web = AsyncMock()
    web.learn = AsyncMock(
        return_value={"ok": True, "facts_added": 2, "summary": "public facts only", "cached": False}
    )
    nl = GuardianNetworkLearner(
        GuardianNetworkLearningSettings(enabled=True, max_topics_per_run=1),
        data_dir=root,
        web_learner=web,
        supervisor=supervisor,
        training_vault=None,
    )
    nl.grant_consent()
    result = await nl.trigger(force=True, topics=["generative AI"])
    assert result["ok"] is True
    web.learn.assert_awaited_once()
    assert topic_anonymous_id("generative AI") in str(result["results"])


def test_network_learning_api_consent_and_status(client):
    status = client.get("/api/guardian/network-learning/status")
    assert status.status_code == 200
    assert status.json()["enabled"] is True
    assert status.json()["user_consented"] is False

    consent = client.post(
        "/api/guardian/network-learning/consent",
        json={"consented": True, "metrics": False},
    )
    assert consent.status_code == 200
    assert consent.json()["user_consented"] is True

    status2 = client.get("/api/guardian/network-learning/status")
    assert status2.json()["user_consented"] is True


def test_network_learning_trigger_api(client):
    client.post("/api/guardian/network-learning/consent", json={"consented": True})
    with patch(
        "monster_ai.modules.learning.web_knowledge.WebKnowledgeLearner.learn",
        new_callable=AsyncMock,
        return_value={"ok": True, "facts_added": 1, "summary": "test", "cached": False},
    ):
        r = client.post(
            "/api/guardian/network-learning/trigger",
            json={"force": True, "topics": ["open source LLM"]},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["review"]["approved"] is True


def test_network_learning_directives(client):
    client.post("/api/guardian/network-learning/consent", json={"consented": True})
    with patch(
        "monster_ai.modules.learning.web_knowledge.WebKnowledgeLearner.learn",
        new_callable=AsyncMock,
        return_value={"ok": True, "facts_added": 1, "summary": "test", "cached": False},
    ):
        client.post(
            "/api/guardian/network-learning/trigger",
            json={"force": True, "topics": ["stable diffusion"]},
        )
    r = client.get("/api/guardian/network-learning/directives")
    assert r.status_code == 200
    assert len(r.json()["directives"]) >= 1


def test_guardian_status_includes_network_learning(client):
    r = client.get("/api/guardian/status")
    assert r.status_code == 200
    assert "network_learning" in r.json()