"""Poll CallGuard reports and forward high-risk alerts to Discord."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

from monster_ai.config import GuardSettings
from monster_ai.modules.discord.guard.ui.embeds import callguard_alert_embed

if TYPE_CHECKING:
    from discord.ext import commands

    from monster_ai.modules.discord.guard.integration.monster_ai_client import MonsterAIClient

logger = logging.getLogger(__name__)


class CallGuardBridge:
    def __init__(
        self,
        guard: GuardSettings,
        client: MonsterAIClient,
        *,
        get_bot: Callable[[], commands.Bot | None],
        get_alert_channel_id: Callable[[], int],
    ) -> None:
        self.guard = guard
        self.client = client
        self._get_bot = get_bot
        self._get_alert_channel_id = get_alert_channel_id
        self._task: asyncio.Task | None = None
        self._stop = False
        self._seen: set[str] = set()
        self.forwarded = 0
        self._last_status = "unknown"

    def start(self) -> None:
        if not self.guard.callguard_bridge_enabled:
            return
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
                await self._poll()
                await asyncio.sleep(self.guard.callguard_poll_interval_seconds)
        except asyncio.CancelledError:
            pass

    def _report_key(self, report: dict) -> str:
        return str(report.get("id") or report.get("number") or report.get("ts") or id(report))

    async def _poll(self) -> None:
        status = await self.client.callguard_status()
        self._last_status = str(status.get("status", "ok" if status.get("enabled") else "off"))
        reports = await self.client.callguard_reports(limit=10)
        bot = self._get_bot()
        if not bot or not bot.is_ready():
            return

        channel_id = self._get_alert_channel_id()
        if not channel_id:
            return

        try:
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        except Exception:  # noqa: BLE001
            return
        if channel is None:
            return

        threshold = self.guard.callguard_alert_score_threshold
        for report in reports:
            key = self._report_key(report)
            if key in self._seen:
                continue
            score = int(report.get("score", 0))
            if score < threshold:
                continue
            self._seen.add(key)
            if len(self._seen) > 500:
                self._seen = set(list(self._seen)[-200:])
            try:
                embed = callguard_alert_embed(report)
                await channel.send(embed=embed)
                self.forwarded += 1
            except Exception as exc:  # noqa: BLE001
                logger.debug("CallGuard forward failed: %s", exc)

    def status_dict(self) -> dict:
        return {
            "enabled": self.guard.callguard_bridge_enabled,
            "status": self._last_status,
            "forwarded": self.forwarded,
        }