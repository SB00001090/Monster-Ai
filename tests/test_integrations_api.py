"""Tests for /api/integrations endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import load_settings


@pytest.fixture
def client() -> TestClient:
    settings = load_settings()
    settings.protection.monsterlock.enabled = False
    settings.protection.monsterlock.self_destruct_enabled = False
    app = create_app(settings)
    return TestClient(app)


def test_integrations_status(client: TestClient) -> None:
    r = client.get("/api/integrations/status")
    assert r.status_code == 200
    data = r.json()
    assert "cloudflare_pages" in data
    assert "quality_threshold" in data
    assert data["quality_threshold"] == 0.7
    assert "supabase_configured" in data
    assert data["supabase_configured"] is False


def test_make_deploy_hook_no_secret(client: TestClient) -> None:
    r = client.post(
        "/api/integrations/make/deploy-hook",
        json={"event": "deploy", "detail": "ok"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_dify_status(client: TestClient) -> None:
    r = client.get("/api/dify/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data