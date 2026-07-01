"""Encrypted chat vault — AES-256-GCM at rest (SQLCipher-equivalent for local-first)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monster_ai.modules.guardian.crypto import EncryptedBlob, decrypt_payload, encrypt_payload


class ChatVault:
    """Ephemeral + persistent encrypted chat sessions."""

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "chat_vault"
        self.root.mkdir(parents=True, exist_ok=True)
        self._ephemeral: dict[str, list[dict[str, Any]]] = {}

    def _session_path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.mgvault"

    def store_message(
        self,
        session_id: str,
        message: dict[str, Any],
        *,
        key: bytes,
        ephemeral: bool = False,
    ) -> dict[str, Any]:
        entry = {
            **message,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        if ephemeral:
            self._ephemeral.setdefault(session_id, []).append(entry)
            return {"session_id": session_id, "ephemeral": True, "count": len(self._ephemeral[session_id])}

        path = self._session_path(session_id)
        existing: list[dict[str, Any]] = []
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            blob = EncryptedBlob.from_dict(raw)
            existing = decrypt_payload(blob, key)  # type: ignore[assignment]

        if not isinstance(existing, list):
            existing = []
        existing.append(entry)
        blob = encrypt_payload(existing, key)
        path.write_text(json.dumps(blob.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return {"session_id": session_id, "ephemeral": False, "count": len(existing)}

    def load_session(
        self,
        session_id: str,
        *,
        key: bytes | None = None,
        ephemeral: bool = False,
    ) -> list[dict[str, Any]]:
        if ephemeral:
            return list(self._ephemeral.get(session_id, []))

        path = self._session_path(session_id)
        if not path.is_file() or key is None:
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        blob = EncryptedBlob.from_dict(raw)
        data = decrypt_payload(blob, key)
        return data if isinstance(data, list) else []

    def wipe_ephemeral(self, session_id: str | None = None) -> int:
        if session_id:
            count = len(self._ephemeral.pop(session_id, []))
            return count
        total = sum(len(v) for v in self._ephemeral.values())
        self._ephemeral.clear()
        return total