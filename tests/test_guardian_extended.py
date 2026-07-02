"""Guardian Ai PR-C/D/E — manuscript, diary, share, account, discord report."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import load_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "guardian:\n  enabled: true\n  data_dir: ./data/guardian\n",
        encoding="utf-8",
    )
    settings = load_settings(cfg)
    settings.protection.monsterlock.enabled = False
    settings.protection.monsterlock.self_destruct_enabled = False
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


CARD = {"id": "luna-1", "name": "Luna", "description": "moon pilot", "personality": "brave"}


def test_manuscript_versions_and_restore(client):
    protect = client.post("/api/guardian/oc/protect", json={"card": CARD, "owner_id": "u1"})
    assert protect.status_code == 200
    assert protect.json()["manuscript_version"] == 1

    updated = {**CARD, "description": "star pilot"}
    protect2 = client.post("/api/guardian/oc/protect", json={"card": updated, "owner_id": "u1"})
    assert protect2.json()["manuscript_version"] == 2

    versions = client.get("/api/guardian/manuscript/luna-1/versions")
    assert versions.status_code == 200
    assert len(versions.json()["versions"]) == 2

    diff = client.get("/api/guardian/manuscript/luna-1/diff?v1=1&v2=2")
    assert diff.status_code == 200
    assert diff.json()["ok"] is True
    assert diff.json()["change_count"] >= 1

    restored = client.post(
        "/api/guardian/manuscript/luna-1/restore",
        json={"version": 1},
    )
    assert restored.status_code == 200
    assert restored.json()["ok"] is True
    assert restored.json()["restored_from"] == 1


def test_diary_append_and_summary(client):
    append = client.post(
        "/api/guardian/diary/luna-1/append",
        json={
            "session_id": "sess-1",
            "vault_key": "diary-secret-12",
            "messages": [{"role": "user", "content": "你好 Luna"}],
            "mood": "happy",
        },
    )
    assert append.status_code == 200
    assert append.json()["ok"] is True

    dates = client.get("/api/guardian/diary/luna-1/dates")
    assert dates.status_code == 200
    assert len(dates.json()["dates"]) >= 1
    day = dates.json()["dates"][-1]

    summary = client.post(
        "/api/guardian/diary/luna-1/summary",
        json={"date": day, "vault_key": "diary-secret-12"},
    )
    assert summary.status_code == 200
    assert "對話日記" in summary.json()["summary"]


def test_share_create_and_import(client):
    created = client.post(
        "/api/guardian/share/create",
        json={
            "oc_id": "luna-1",
            "card": CARD,
            "owner_id": "u1",
            "mode": "link",
            "ttl_hours": 24,
            "passphrase": "share-pass-12",
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["ok"] is True
    token = data["share_token"]

    imported = client.post(
        "/api/guardian/share/import",
        json={"token": token, "passphrase": "share-pass-12"},
    )
    assert imported.status_code == 200
    assert imported.json()["ok"] is True
    assert imported.json()["card"]["name"] == "Luna"
    assert imported.json()["fingerprint"]["watermark"].startswith("GDA-")


def test_account_register_and_discord_link(client):
    reg = client.post(
        "/api/guardian/account/register",
        json={"username": "suckbob", "display_name": "Suckbob"},
    )
    assert reg.status_code == 200
    account_id = reg.json()["account_id"]

    link = client.post(
        "/api/guardian/account/link",
        json={
            "account_id": account_id,
            "provider": "discord",
            "provider_sub": "discord-12345",
            "display_name": "suckbob#0001",
        },
    )
    assert link.status_code == 200
    assert link.json()["linked"] is True

    status = client.get(f"/api/guardian/account/status?account_id={account_id}")
    assert status.status_code == 200
    assert status.json()["discord_bound"] is True
    assert "discord" in status.json()["providers"]


def test_guardian_status_extended_flags(client):
    r = client.get("/api/guardian/status")
    data = r.json()
    assert data["manuscript_versions"] is True
    assert data["diary_encryption"] is True
    assert data["character_share"] is True
    assert data["discord_binding"] is True