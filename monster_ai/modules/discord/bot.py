"""Discord service — MonsterGuard bot + Monster AI chat bridge."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from monster_ai.config import Settings
from monster_ai.modules.discord.constants import DEVELOPER_CREDIT, LOG_PATH, VERSION
from monster_ai.modules.discord.guard.integration.callguard_bridge import CallGuardBridge
from monster_ai.modules.discord.guard.integration.monster_ai_client import MonsterAIClient
from monster_ai.modules.discord.guard.resilience.heartbeat import HeartbeatMonitor
from monster_ai.modules.discord.guard.resilience.notifier import DisconnectNotifier
from monster_ai.modules.discord.guard.resilience.reconnect import ReconnectManager

if TYPE_CHECKING:
    from monster_ai.core.self_repair import SelfRepairEngine
    from monster_ai.modules.chat.service import ChatService
    from monster_ai.modules.roleplay.service import RoleplayService

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class GuardHealStats:
    restarts: int = 0
    last_heal_at: float | None = None
    last_error: str | None = None
    token_fingerprint: str = ""


class DiscordService:
    name = "discord"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._bot = None
        self._task: asyncio.Task | None = None
        self._heal_task: asyncio.Task | None = None
        self._running = False
        self._stop = False
        self._fatal_auth_error = False
        self._offline_streak = 0
        self._heal_stats = GuardHealStats()
        self._repair: SelfRepairEngine | None = None
        self._chat: ChatService | None = None
        self._roleplay: RoleplayService | None = None
        self._token: str = ""

        guard = settings.modules.discord.guard
        self._notifier = DisconnectNotifier(guard, get_bot=lambda: self._bot)
        self._reconnect = ReconnectManager(guard, notifier=self._notifier)
        self._monster_client = MonsterAIClient(settings)
        self._heartbeat = HeartbeatMonitor(
            guard,
            self._reconnect,
            get_bot=lambda: self._bot,
            monster_client=self._monster_client,
            on_failure=self._on_heartbeat_failure,
        )
        self._callguard_bridge = CallGuardBridge(
            guard,
            self._monster_client,
            get_bot=lambda: self._bot,
            get_alert_channel_id=self._resolve_alert_channel_id,
        )

    def _resolve_alert_channel_id(self) -> int:
        env = os.getenv("MONSTERGUARD_ALERT_CHANNEL_ID", "").strip()
        if env.isdigit():
            return int(env)
        return int(self.settings.modules.discord.guard.notify_channel_id or 0)

    def _token_file_path(self) -> Path | None:
        primary = _PROJECT_ROOT / "discord.token.local"
        if primary.is_file():
            return primary
        legacy = Path("discord.token.local")
        return legacy if legacy.is_file() else None

    def _read_token_file(self) -> str:
        token_file = self._token_file_path()
        if not token_file:
            return ""
        lines = [
            ln.strip()
            for ln in token_file.read_text(encoding="utf-8-sig").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        return lines[0] if lines else ""

    def _token_fingerprint(self, token: str) -> str:
        if not token:
            return ""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

    def _sync_token(self) -> str:
        env_name = self.settings.modules.discord.token_env
        file_token = self._read_token_file()
        if file_token:
            fingerprint = self._token_fingerprint(file_token)
            if fingerprint != self._heal_stats.token_fingerprint:
                self._heal_stats.token_fingerprint = fingerprint
                os.environ[env_name] = file_token
                if self._fatal_auth_error:
                    logger.info("MonsterGuard token file updated; clearing auth fatal state")
                self._fatal_auth_error = False
            self._token = file_token
            return file_token

        env_token = os.getenv(env_name, "").strip()
        if env_token:
            self._token = env_token
            self._heal_stats.token_fingerprint = self._token_fingerprint(env_token)
            return env_token
        return ""

    def _resolve_token(self) -> str:
        if self._token:
            return self._token
        return self._sync_token()

    def heal_status_dict(self) -> dict[str, Any]:
        guard = self.settings.modules.discord.guard
        return {
            "enabled": guard.self_heal_enabled,
            "restarts": self._heal_stats.restarts,
            "last_error": self._heal_stats.last_error,
            "last_heal_at": self._heal_stats.last_heal_at,
            "fatal_auth": self._fatal_auth_error,
            "offline_streak": self._offline_streak,
        }

    async def health(self) -> dict[str, Any]:
        if not self.settings.modules.discord.enabled:
            return {"enabled": False, "healthy": False, "message": "Module disabled"}

        token = self._sync_token()
        if not token:
            return {
                "enabled": True,
                "healthy": False,
                "message": f"Set {self.settings.modules.discord.token_env} to enable",
            }

        if self._running and self._bot:
            status = self._bot.status_dict()
            return {
                "enabled": True,
                "healthy": True,
                "message": "MonsterGuard running",
                **status,
            }
        return {
            "enabled": True,
            "healthy": True,
            "message": "Token configured; bot not started",
        }

    def guard_status(self) -> dict[str, Any]:
        guard = self.settings.modules.discord.guard
        connected = bool(
            self._bot
            and not self._bot.is_closed()
            and self._bot.is_ready()
        )
        if connected:
            base: dict[str, Any] = {"running": True, "connected": True, **self._bot.status_dict()}
        elif self._running:
            base = {
                "running": False,
                "connected": False,
                "message": "reconnecting" if not self._reconnect.state.standby_mode else "standby",
            }
        else:
            base = {"running": False, "connected": False}

        base["version"] = VERSION
        base["developer"] = DEVELOPER_CREDIT
        base["self_heal"] = self.heal_status_dict()
        base["resilience"] = self._reconnect.state.to_dict(guard)
        base["monster_ai"] = self._monster_client.status_dict()
        base["callguard_bridge"] = self._callguard_bridge.status_dict()
        return base

    @staticmethod
    def read_logs(limit: int = 50) -> list[dict[str, Any]]:
        path = Path(LOG_PATH)
        if not path.is_file():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    async def start_guard(
        self,
        repair: SelfRepairEngine,
        chat: ChatService,
        roleplay: RoleplayService | None = None,
    ) -> None:
        if not self.settings.modules.discord.enabled:
            return
        if not self.settings.modules.discord.guard.enabled:
            logger.info("MonsterGuard disabled in config")
            return

        self._repair = repair
        self._chat = chat
        self._roleplay = roleplay
        self._stop = False

        token = self._sync_token()
        if not token:
            logger.warning(
                "MonsterGuard: no Discord token. Set %s or create discord.token.local",
                self.settings.modules.discord.token_env,
            )
            return

        await self._start_bot_task(token)
        self._start_heal_loop()
        self._heartbeat.start()
        self._callguard_bridge.start()

    def _start_heal_loop(self) -> None:
        guard = self.settings.modules.discord.guard
        if not guard.self_heal_enabled:
            return
        if self._heal_task and not self._heal_task.done():
            return
        self._heal_task = asyncio.create_task(self._heal_loop())

    async def _heal_loop(self) -> None:
        guard = self.settings.modules.discord.guard
        try:
            while not self._stop:
                await asyncio.sleep(guard.self_heal_interval_seconds)
                await self.ensure_guard_running()
        except asyncio.CancelledError:
            pass

    async def ensure_guard_running(self) -> None:
        guard = self.settings.modules.discord.guard
        if self._stop or not guard.self_heal_enabled:
            return
        if not self.settings.modules.discord.enabled or not guard.enabled:
            return

        self._heal_stats.last_heal_at = time.time()
        token = self._sync_token()
        if not token:
            self._heal_stats.last_error = "missing_token"
            return
        if self._fatal_auth_error:
            self._heal_stats.last_error = "fatal_auth"
            return
        if self._reconnect.state.standby_mode:
            self._heal_stats.last_error = "standby"
            return

        task_alive = self._task is not None and not self._task.done()
        if task_alive and self._running:
            self._offline_streak = 0
            self._heal_stats.last_error = None
            return

        self._offline_streak += 1
        if self._offline_streak < 2:
            return

        logger.warning("MonsterGuard self-heal: restarting bot (streak=%s)", self._offline_streak)
        await self.restart_guard()

    async def restart_guard(self, *, force_token: str | None = None) -> dict[str, Any]:
        self._reconnect.reset()
        token = force_token or self._sync_token()
        if not token:
            return {"ok": False, "error": "missing_token"}
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._close_bot()
        self._offline_streak = 0
        await self._start_bot_task(token)
        self._heal_stats.restarts += 1
        self._heal_stats.last_error = None
        if not self._heartbeat._task or self._heartbeat._task.done():  # noqa: SLF001
            self._heartbeat.start()
        if not self._callguard_bridge._task or self._callguard_bridge._task.done():  # noqa: SLF001
            self._callguard_bridge.start()
        return {"ok": True, "restarts": self._heal_stats.restarts}

    async def _on_heartbeat_failure(self) -> None:
        await self._notifier.notify_heartbeat_failure(self._reconnect.state.heartbeat_fail_streak)
        await self.restart_guard()

    async def _start_bot_task(self, token: str) -> None:
        if self._task and not self._task.done():
            return
        self._token = token
        self._task = asyncio.create_task(self._run_bot(token))

    def _create_bot(self) -> None:
        from monster_ai.modules.discord.guard.bot import MonsterGuardBot

        self._bot = MonsterGuardBot(
            self.settings,
            repair=self._repair,
            chat=self._chat,
            roleplay=self._roleplay,
            discord_service=self,
        )

    async def _close_bot(self) -> None:
        if not self._bot:
            return
        try:
            if not self._bot.is_closed():
                await self._bot.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("MonsterGuard close: %s", exc)
        self._bot = None

    async def _run_bot(self, token: str) -> None:
        guard = self.settings.modules.discord.guard

        async def start_bot() -> None:
            assert self._bot is not None
            await self._bot.start(token)

        await self._reconnect.run(
            stop_flag=lambda: self._stop,
            create_bot=self._create_bot,
            start_bot=start_bot,
            close_bot=self._close_bot,
            on_running=lambda v: setattr(self, "_running", v),
            on_fatal_auth=lambda: setattr(self, "_fatal_auth_error", True),
            get_fatal_auth=lambda: self._fatal_auth_error,
            set_fatal_auth=lambda v: setattr(self, "_fatal_auth_error", v),
            set_last_error=lambda e: setattr(self._heal_stats, "last_error", e),
        )

    async def stop_guard(self) -> None:
        self._stop = True
        await self._heartbeat.stop()
        await self._callguard_bridge.stop()
        await self._monster_client.close()
        if self._heal_task:
            self._heal_task.cancel()
            try:
                await self._heal_task
            except asyncio.CancelledError:
                pass
            self._heal_task = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._close_bot()
        self._running = False