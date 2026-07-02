"""Local Guardian accounts — register + Google/GitHub/Discord OAuth binding."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AccountStore:
    OAUTH_PROVIDERS = frozenset({"google", "github", "discord"})

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "accounts"
        self.root.mkdir(parents=True, exist_ok=True)

    def _account_path(self, account_id: str) -> Path:
        safe = hashlib.sha256(account_id.encode()).hexdigest()[:16]
        return self.root / f"{safe}.json"

    def _load(self, account_id: str) -> dict[str, Any] | None:
        path = self._account_path(account_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError):
            return None

    def _save(self, account_id: str, record: dict[str, Any]) -> None:
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._account_path(account_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def register_local(
        self,
        *,
        username: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        username = username.strip().lower()
        if len(username) < 3:
            return {"ok": False, "reason": "username_too_short"}
        account_id = f"local:{username}"
        if self._load(account_id):
            return {"ok": False, "reason": "username_taken"}
        record = {
            "account_id": account_id,
            "username": username,
            "display_name": display_name or username,
            "login_method": "local",
            "oauth_links": {},
            "discord": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save(account_id, record)
        return {"ok": True, "account_id": account_id, "display_name": record["display_name"]}

    def link_oauth(
        self,
        *,
        account_id: str,
        provider: str,
        provider_sub: str,
        display_name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        if provider not in self.OAUTH_PROVIDERS:
            return {"ok": False, "reason": "invalid_provider"}
        record = self._load(account_id)
        if record is None:
            record = {
                "account_id": account_id,
                "username": account_id,
                "display_name": display_name or account_id,
                "login_method": provider,
                "oauth_links": {},
                "discord": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        links = record.setdefault("oauth_links", {})
        links[provider] = {
            "provider_sub": provider_sub,
            "display_name": display_name,
            "email": email,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }
        if provider == "discord":
            record["discord"] = {
                "user_id": provider_sub,
                "username": display_name or provider_sub,
                "linked_at": datetime.now(timezone.utc).isoformat(),
                "error_report_enabled": True,
            }
        self._save(account_id, record)
        return {"ok": True, "account_id": account_id, "provider": provider, "linked": True}

    def bind_discord_webhook(
        self,
        account_id: str,
        *,
        webhook_url: str,
    ) -> dict[str, Any]:
        record = self._load(account_id)
        if record is None:
            return {"ok": False, "reason": "account_not_found"}
        discord = record.setdefault("discord", {})
        discord["webhook_url"] = webhook_url
        discord["error_report_enabled"] = True
        discord["webhook_set_at"] = datetime.now(timezone.utc).isoformat()
        self._save(account_id, record)
        return {"ok": True, "account_id": account_id, "discord_bound": True}

    def status(self, account_id: str) -> dict[str, Any]:
        record = self._load(account_id)
        if record is None:
            return {"ok": False, "reason": "account_not_found"}
        links = record.get("oauth_links") or {}
        return {
            "ok": True,
            "account_id": account_id,
            "display_name": record.get("display_name"),
            "login_method": record.get("login_method"),
            "providers": list(links.keys()),
            "discord_bound": bool(record.get("discord")),
            "discord_error_report": bool((record.get("discord") or {}).get("error_report_enabled")),
        }

    def resolve_by_oauth(self, provider: str, provider_sub: str) -> str | None:
        for path in self.root.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            link = (record.get("oauth_links") or {}).get(provider)
            if link and link.get("provider_sub") == provider_sub:
                return str(record.get("account_id"))
        return None

    def get_discord_webhook(self, account_id: str) -> str | None:
        record = self._load(account_id)
        if not record:
            return None
        discord = record.get("discord") or {}
        return discord.get("webhook_url")