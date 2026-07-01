"""Encrypted cloud sync — Google/GitHub OAuth identity + user passphrase E2E."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monster_ai.modules.guardian.crypto import (
    EncryptedBlob,
    decrypt_payload,
    derive_oauth_key,
    encrypt_payload,
    oauth_user_hash,
)


class CloudSyncStore:
    """Self-hosted encrypted blob store — no plaintext on server."""

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "cloud"
        self.root.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, provider: str, provider_sub: str) -> Path:
        user_hash = oauth_user_hash(provider, provider_sub)
        path = self.root / provider / user_hash
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _derive_key(self, provider: str, provider_sub: str, passphrase: str, salt_b64: str) -> bytes:
        import base64

        salt = base64.b64decode(salt_b64)
        return derive_oauth_key(provider, provider_sub, passphrase, salt)

    def upload_bundle(
        self,
        *,
        provider: str,
        provider_sub: str,
        passphrase: str,
        bundle_type: str,
        payload: dict[str, Any] | list[Any],
        device_id: str = "unknown",
    ) -> dict[str, Any]:
        user_dir = self._user_dir(provider, provider_sub)
        import base64
        import secrets

        from monster_ai.modules.guardian.crypto import SALT_SIZE

        salt = secrets.token_bytes(SALT_SIZE)
        key = derive_oauth_key(provider, provider_sub, passphrase, salt)
        blob = encrypt_payload(payload, key)
        blob.salt_b64 = base64.b64encode(salt).decode("ascii")

        meta = {
            "bundle_type": bundle_type,
            "device_id": device_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "user_hash": oauth_user_hash(provider, provider_sub),
            "encrypted": blob.to_dict(),
        }
        out_path = user_dir / f"{bundle_type}.json"
        out_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        manifest_path = user_dir / "manifest.json"
        manifest: dict[str, Any] = {"bundles": [], "last_sync": meta["uploaded_at"]}
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["bundles"] = [b for b in manifest.get("bundles", []) if b.get("type") != bundle_type]
        manifest["bundles"].append(
            {"type": bundle_type, "uploaded_at": meta["uploaded_at"], "device_id": device_id}
        )
        manifest["last_sync"] = meta["uploaded_at"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "bundle_type": bundle_type,
            "uploaded_at": meta["uploaded_at"],
            "user_hash": meta["user_hash"],
        }

    def download_bundle(
        self,
        *,
        provider: str,
        provider_sub: str,
        passphrase: str,
        bundle_type: str,
    ) -> dict[str, Any]:
        user_dir = self._user_dir(provider, provider_sub)
        path = user_dir / f"{bundle_type}.json"
        if not path.is_file():
            return {"ok": False, "reason": "not_found"}

        meta = json.loads(path.read_text(encoding="utf-8"))
        blob = EncryptedBlob.from_dict(meta["encrypted"])
        import base64

        salt = base64.b64decode(blob.salt_b64)
        key = derive_oauth_key(provider, provider_sub, passphrase, salt)
        try:
            payload = decrypt_payload(blob, key)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": "decrypt_failed", "detail": str(exc)}

        return {
            "ok": True,
            "bundle_type": bundle_type,
            "uploaded_at": meta.get("uploaded_at"),
            "payload": payload,
        }

    def list_bundles(self, provider: str, provider_sub: str) -> dict[str, Any]:
        user_dir = self._user_dir(provider, provider_sub)
        manifest_path = user_dir / "manifest.json"
        if not manifest_path.is_file():
            return {"bundles": [], "last_sync": None}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "bundles": manifest.get("bundles", []),
            "last_sync": manifest.get("last_sync"),
            "user_hash": oauth_user_hash(provider, provider_sub),
        }