"""Local Monster AI HTTP client with consent gate."""
from __future__ import annotations

import logging
import os
import ssl
from pathlib import Path
from typing import Any

import aiohttp

from monster_ai.config import GuardSettings, Settings

logger = logging.getLogger(__name__)


class MonsterAIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.guard = settings.modules.discord.guard
        self._session: aiohttp.ClientSession | None = None

    @property
    def base_url(self) -> str:
        if self.guard.monster_ai_url:
            return self.guard.monster_ai_url.rstrip("/")
        port = getattr(self.settings, "port", 7860)
        return f"http://127.0.0.1:{port}"

    @property
    def consent_granted(self) -> bool:
        if not self.guard.monster_ai_consent_required:
            return True
        if os.getenv("MONSTER_AI_CONNECT_CONSENT", "").strip() in {"1", "true", "yes"}:
            return True
        return os.getenv("MONSTER_AI_CONNECT_CONSENT", "").lower() == "granted"

    def _ssl_context(self) -> ssl.SSLContext | None:
        cert = self.guard.mtls_cert_path.strip()
        key = self.guard.mtls_key_path.strip()
        if not cert or not key:
            return None
        ctx = ssl.create_default_context()
        ctx.load_cert_chain(certfile=cert, keyfile=key)
        return ctx

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._ssl_context())
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def ping(self) -> bool:
        if not self.consent_granted:
            return True
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/status") as resp:
                return resp.status == 200
        except Exception as exc:  # noqa: BLE001
            logger.debug("Monster AI ping failed: %s", exc)
            return False

    async def analyze_scam(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        if not self.consent_granted:
            return {"error": "consent_required"}
        session = await self._get_session()
        payload: dict[str, Any] = {"prompt": prompt}
        if system:
            payload["system"] = system
        async with session.post(f"{self.base_url}/api/guard/analyze", json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def callguard_status(self) -> dict[str, Any]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/callguard/status") as resp:
            if resp.status == 200:
                return await resp.json()
            return {"enabled": False}

    async def callguard_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/api/callguard/reports", params={"limit": limit}) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return list(data.get("reports") or [])

    def status_dict(self) -> dict[str, Any]:
        return {
            "connected": self.consent_granted,
            "consent": self.consent_granted,
            "base_url": self.base_url,
            "backend": "local",
        }