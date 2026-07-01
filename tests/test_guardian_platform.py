"""Monster Guardian AI platform tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import load_settings
from monster_ai.modules.guardian.crypto import (
    decrypt_payload,
    derive_oauth_key,
    encrypt_payload,
    oauth_user_hash,
)
from monster_ai.modules.guardian.disclaimer import DEVELOPER, get_disclaimer
from monster_ai.modules.guardian.oc_fingerprint import generate_fingerprint, verify_ownership


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


def test_disclaimer_hardcoded():
    zh = get_disclaimer("zh-TW")
    assert DEVELOPER in zh["text"]
    assert "可能性無法退款" in zh["text"]
    assert "自主網絡學習" in zh["text"]
    assert "Grok" in zh["text"]
    assert zh["version"] == "guardian_v1"

    en = get_disclaimer("en")
    assert "Autonomous network learning" in en["text"]


def test_e2e_encrypt_roundtrip():
    import base64
    import secrets

    from monster_ai.modules.guardian.crypto import SALT_SIZE

    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_oauth_key("google", "sub-123", "test-passphrase-8", salt)
    payload = {"oc": [{"name": "Test OC"}]}
    blob = encrypt_payload(payload, key)
    blob.salt_b64 = base64.b64encode(salt).decode("ascii")
    out = decrypt_payload(blob, key)
    assert out == payload


def test_oauth_user_hash_stable():
    assert oauth_user_hash("github", "user-42") == oauth_user_hash("github", "user-42")


def test_oc_fingerprint_and_verify():
    card = {"name": "Luna", "description": "moon witch", "worldview": "fantasy"}
    record = generate_fingerprint(card, owner_id="user-1")
    assert record["watermark"].startswith("MGA-")
    assert verify_ownership(card, record, owner_id="user-1")


def test_guardian_status(client):
    r = client.get("/api/guardian/status")
    assert r.status_code == 200
    data = r.json()
    assert data["no_tailscale"] is True
    assert data["no_qr_code"] is True
    assert "Suckbob" in data["developer"]


def test_connection_endpoint(client):
    r = client.get("/api/guardian/connection")
    assert r.status_code == 200
    assert r.json()["mode"] == "cloudflare_tunnel"


def test_cloud_sync_upload_download(client):
    payload = {"characters": [{"id": "c1", "name": "Guardian OC"}]}
    up = client.post(
        "/api/guardian/sync/upload",
        json={
            "provider": "google",
            "provider_sub": "gid-999",
            "passphrase": "my-secret-key-12",
            "bundle_type": "oc_cards",
            "payload": payload,
        },
    )
    assert up.status_code == 200
    assert up.json()["ok"] is True

    down = client.post(
        "/api/guardian/sync/download",
        json={
            "provider": "google",
            "provider_sub": "gid-999",
            "passphrase": "my-secret-key-12",
            "bundle_type": "oc_cards",
        },
    )
    assert down.status_code == 200
    assert down.json()["payload"] == payload

    wrong = client.post(
        "/api/guardian/sync/download",
        json={
            "provider": "google",
            "provider_sub": "gid-999",
            "passphrase": "wrong-passphrase",
            "bundle_type": "oc_cards",
        },
    )
    assert wrong.json()["ok"] is False


def test_error_report_and_supervise(client):
    r = client.post(
        "/api/guardian/errors/report",
        json={
            "error_type": "TunnelError",
            "message": "tailscale connection refused",
            "context": "android tunnel",
        },
    )
    assert r.status_code == 200
    assert "fix_suggestion" in r.json()

    sup = client.post("/api/guardian/learning/supervise")
    assert sup.status_code == 200
    assert sup.json()["supervisor"] == "grok"


def test_quality_gate(client):
    assert client.post("/api/guardian/quality/gate", json={"score": 0.85}).json()["passed"]
    fail = client.post("/api/guardian/quality/gate", json={"score": 0.55}).json()
    assert fail["passed"] is False
    assert fail["action"] == "retry_generation"


def test_training_status(client):
    r = client.get("/api/guardian/training/status")
    assert r.status_code == 200
    data = r.json()
    assert data["training_encryption_enabled"] is True
    assert data["vault"]["encrypted"] is True


def test_training_store_text(client):
    r = client.post(
        "/api/guardian/training/store-text",
        json={
            "label": "template",
            "name": "test_tpl",
            "content": "masterpiece, {{prompt}}",
        },
    )
    assert r.status_code == 200
    assert r.json()["encrypted"] is True


def test_oc_protect(client):
    r = client.post(
        "/api/guardian/oc/protect",
        json={"card": {"id": "x1", "name": "Nova", "description": "pilot"}},
    )
    assert r.status_code == 200
    assert r.json()["protected"] is True
    assert "extensions" in r.json()["card"]