"""Conversation diary — encrypted daily summaries per character."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from monster_ai.modules.guardian.crypto import EncryptedBlob, decrypt_payload, derive_user_key, encrypt_payload


class DiaryStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "diaries"
        self.root.mkdir(parents=True, exist_ok=True)

    def _char_dir(self, character_id: str) -> Path:
        safe = hashlib.sha256(character_id.encode()).hexdigest()[:16]
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _day_path(self, character_id: str, date: str) -> Path:
        return self._char_dir(character_id) / f"{date}.mgdiary"

    def _diary_key(self, character_id: str, vault_key: str) -> bytes:
        salt = hashlib.sha256(f"guardian-diary:{character_id}".encode()).digest()[:16]
        return derive_user_key(vault_key, salt, info=b"guardian-diary-v1")

    def append_messages(
        self,
        character_id: str,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
        vault_passphrase: str,
        mood: str | None = None,
    ) -> dict[str, Any]:
        vault_key = self._diary_key(character_id, vault_passphrase)
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self._day_path(character_id, date)
        existing: dict[str, Any] = {
            "character_id": character_id,
            "date": date,
            "sessions": [],
            "mood": mood,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            blob = EncryptedBlob.from_dict(raw)
            decrypted = decrypt_payload(blob, vault_key)
            if isinstance(decrypted, dict):
                existing = decrypted

        sessions = existing.setdefault("sessions", [])
        sessions.append(
            {
                "session_id": session_id,
                "message_count": len(messages),
                "messages": messages[-20:],
                "appended_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        existing["sessions"] = sessions[-30:]
        if mood:
            existing["mood"] = mood
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()

        blob = encrypt_payload(existing, vault_key)
        path.write_text(json.dumps(blob.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "character_id": character_id, "date": date, "session_count": len(sessions)}

    def get_day(self, character_id: str, date: str, *, vault_passphrase: str) -> dict[str, Any]:
        vault_key = self._diary_key(character_id, vault_passphrase)
        path = self._day_path(character_id, date)
        if not path.is_file():
            return {"ok": True, "character_id": character_id, "date": date, "empty": True, "diary": None}
        raw = json.loads(path.read_text(encoding="utf-8"))
        blob = EncryptedBlob.from_dict(raw)
        diary = decrypt_payload(blob, vault_key)
        return {"ok": True, "character_id": character_id, "date": date, "diary": diary}

    def list_dates(self, character_id: str) -> list[str]:
        char_dir = self._char_dir(character_id)
        dates: list[str] = []
        for path in sorted(char_dir.glob("*.mgdiary")):
            dates.append(path.stem)
        return dates

    def generate_summary(
        self,
        character_id: str,
        *,
        date: str | None = None,
        vault_passphrase: str,
    ) -> dict[str, Any]:
        day = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        loaded = self.get_day(character_id, day, vault_passphrase=vault_passphrase)
        diary = loaded.get("diary")
        if not diary or not isinstance(diary, dict):
            return {
                "ok": True,
                "character_id": character_id,
                "date": day,
                "summary": "今日尚無對話記錄。",
                "message_total": 0,
            }
        total = 0
        snippets: list[str] = []
        for session in diary.get("sessions") or []:
            msgs = session.get("messages") or []
            total += len(msgs)
            for msg in msgs[-3:]:
                role = msg.get("role", "user")
                content = str(msg.get("content", ""))[:120]
                if content:
                    snippets.append(f"[{role}] {content}")
        mood = diary.get("mood") or "neutral"
        summary = (
            f"【{day} 對話日記 · {character_id}】\n"
            f"心情：{mood} · 訊息數：{total}\n"
            + ("\n".join(snippets[-8:]) if snippets else "（無摘要內容）")
        )
        return {
            "ok": True,
            "character_id": character_id,
            "date": day,
            "summary": summary,
            "message_total": total,
            "mood": mood,
        }