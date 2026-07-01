"""Heartbeat monitor — Discord latency + optional Monster AI ping."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Awaitable, Callable

from monster_ai.config import GuardSettings

if TYPE_CHECKING:
    from discord.ext import commands

    from monster_ai.modules.discord.guard.integration.monster_ai_client import MonsterAIClient
    from monster_ai.modules.discord.guard.resilience.reconnect import ReconnectManager

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    def __init__(
        self,
        guard: GuardSettings,
        reconnect: ReconnectManager,
        *,
        get_bot: Callable[[], commands.Bot | None],
        monster_client: MonsterAIClient | None = None,
        on_failure: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.guard = guard
        self.reconnect = reconnect
        self._get_bot = get_bot
        self._monster_client = monster_client
        self._on_failure = on_failure
        self._task: asyncio.Task | None = None
        self._stop = False

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop = False
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        try:
            while not self._stop:
                await asyncio.sleep(self.guard.heartbeat_interval_seconds)
                await self._tick()
        except asyncio.CancelledError:
            pass

    async def _tick(self) -> None:
        bot = self._get_bot()
        ok = True
        if not bot or bot.is_closed() or not bot.is_ready():
            ok = False
        elif bot.latency > self.guard.heartbeat_max_latency_seconds:
            ok = False
            logger.warning("MonsterGuard heartbeat: high latency %.2fs", bot.latency)

        if ok and self._monster_client and self._monster_client.consent_granted:
            ping_ok = await self._monster_client.ping()
            if not ping_ok:
                ok = False

        self.reconnect.state.heartbeat_ok = ok
        if ok:
            self.reconnect.state.heartbeat_fail_streak = 0
            return

        self.reconnect.state.heartbeat_fail_streak += 1
        self.reconnect.log_event(
            "heartbeat_failure",
            streak=self.reconnect.state.heartbeat_fail_streak,
        )
        if self.reconnect.state.heartbeat_fail_streak >= self.guard.heartbeat_fail_threshold:
            logger.warning("MonsterGuard heartbeat failed %s times — triggering restart", self.reconnect.state.heartbeat_fail_streak)
            self.reconnect.state.heartbeat_fail_streak = 0
            if self._on_failure:
                await self._on_failure()