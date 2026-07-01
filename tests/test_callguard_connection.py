"""Call Guard connection API — Cloudflare Tunnel only."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import load_settings

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path: Path):
    tunnel_file = tmp_path / "tunnel_url.txt"
    tunnel_file.write_text("https://test-tunnel.trycloudflare.com\n", encoding="utf-8")
    settings = load_settings()
    settings.protection.monsterlock.enabled = False
    settings.protection.monsterlock.self_destruct_enabled = False
    settings.protection.callguard.enabled = True
    settings.protection.callguard.tunnel_url_file = str(tunnel_file)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_connection_hint_tunnel_only(client: TestClient) -> None:
    r = client.get("/api/callguard/connection")
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "cloudflare_tunnel"
    assert data["no_tailscale"] is True
    assert data["no_qr_code"] is True
    assert "usb_local" in data["modes"]
    assert data["tunnel_url"] == "https://test-tunnel.trycloudflare.com"
    assert data["no_public_comment_board"] is True


def test_analyze_includes_trust_score(client: TestClient) -> None:
    r = client.post(
        "/api/callguard/analyze",
        json={"number": "+85290001111", "display_name": "test", "deep": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert "trust_score" in body
    assert body["trust_score"] == max(0, 100 - body["score"])