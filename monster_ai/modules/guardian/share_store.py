"""Character share — private / link / public with OC fingerprint protection."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from monster_ai.modules.guardian.crypto import EncryptedBlob, decrypt_payload, encrypt_payload
from monster_ai.modules.guardian.oc_fingerprint import embed_watermark, generate_fingerprint


class ShareStore:
    MODES = frozenset({"private", "link", "public"})

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "shares"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.jsonl"

    def _token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    def _bundle_path(self, token_hash: str) -> Path:
        return self.root / f"{token_hash}.mgshare"

    def create_share(
        self,
        *,
        oc_id: str,
        card: dict[str, Any],
        owner_id: str,
        mode: str = "link",
        ttl_hours: int = 24,
        passphrase: str,
    ) -> dict[str, Any]:
        if mode not in self.MODES:
            return {"ok": False, "reason": "invalid_mode"}
        if len(passphrase) < 8:
            return {"ok": False, "reason": "passphrase_too_short"}

        record = generate_fingerprint(card, owner_id=owner_id)
        protected = embed_watermark(card, record)
        token = secrets.token_urlsafe(32)
        token_hash = self._token_hash(token)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=max(1, ttl_hours))).isoformat()

        bundle = {
            "oc_id": oc_id,
            "owner_id": owner_id,
            "mode": mode,
            "card": protected,
            "fingerprint": record,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        from monster_ai.modules.guardian.crypto import derive_user_key, SALT_SIZE
        import base64

        salt = secrets.token_bytes(SALT_SIZE)
        key = derive_user_key(f"{passphrase}:{token}", salt, info=b"guardian-share-v1")
        blob = encrypt_payload(bundle, key)
        blob.salt_b64 = base64.b64encode(salt).decode("ascii")

        self._bundle_path(token_hash).write_text(
            json.dumps(blob.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        index_entry = {
            "token_hash": token_hash,
            "oc_id": oc_id,
            "owner_id": owner_id,
            "mode": mode,
            "expires_at": expires_at,
            "created_at": bundle["created_at"],
        }
        with self.index_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(index_entry, ensure_ascii=False) + "\n")

        return {
            "ok": True,
            "share_token": token,
            "mode": mode,
            "expires_at": expires_at,
            "watermark": record.get("watermark"),
            "import_hint": "POST /api/guardian/share/import with token + passphrase",
        }

    def import_share(self, *, token: str, passphrase: str) -> dict[str, Any]:
        if len(passphrase) < 8:
            return {"ok": False, "reason": "passphrase_too_short"}
        token_hash = self._token_hash(token)
        path = self._bundle_path(token_hash)
        if not path.is_file():
            return {"ok": False, "reason": "share_not_found"}

        raw = json.loads(path.read_text(encoding="utf-8"))
        blob = EncryptedBlob.from_dict(raw)
        from monster_ai.modules.guardian.crypto import derive_user_key
        import base64

        salt = base64.b64decode(blob.salt_b64)
        key = derive_user_key(f"{passphrase}:{token}", salt, info=b"guardian-share-v1")
        try:
            bundle = decrypt_payload(blob, key)
        except Exception:
            return {"ok": False, "reason": "decrypt_failed"}

        if not isinstance(bundle, dict):
            return {"ok": False, "reason": "invalid_bundle"}

        expires = bundle.get("expires_at")
        if expires:
            try:
                exp_dt = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
                if exp_dt < datetime.now(timezone.utc):
                    return {"ok": False, "reason": "share_expired"}
            except ValueError:
                pass

        return {
            "ok": True,
            "oc_id": bundle.get("oc_id"),
            "owner_id": bundle.get("owner_id"),
            "mode": bundle.get("mode"),
            "card": bundle.get("card"),
            "fingerprint": bundle.get("fingerprint"),
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }

    def list_by_owner(self, owner_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not self.index_path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self.index_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("owner_id") == owner_id:
                out.append(entry)
        return out[-limit:]