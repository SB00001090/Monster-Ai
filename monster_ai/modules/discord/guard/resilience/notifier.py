"""Disconnect notifications via Discord webhook and alert channel."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Callable

import aiohttp

from monster_ai.config import GuardSettings
from monster_ai.modules.discord.constants import DEVELOPER_CREDIT, PRODUCT_NAME, VERSION
from monster_ai.modules.discord.guard.ui.embeds import alert_embed

if TYPE_CHECKING:
    from discord.ext import commands

logger = logging.getLogger(__name__)


class DisconnectNotifier:
    def __init__(
        self,
        guard: GuardSettings,
        *,
        get_bot: Callable[[], commands.Bot | None] | None = None,
    ) -> None:
        self.guard = guard
        self._get_bot = get_bot

    def _webhook_url(self) -> str:
        return (self.guard.notify_webhook_url or os.getenv("MONSTERGUARD_WEBHOOK_URL", "")).strip()

    def _alert_channel_id(self) -> int:
        env = os.getenv("MONSTERGUARD_ALERT_CHANNEL_ID", "").strip()
        if env.isdigit():
            return int(env)
        return int(self.guard.notify_channel_id or 0)

    async def _send_webhook(self, content: str, *, title: str, level: str = "warn") -> None:
        url = self._webhook_url()
        if not url:
            return
        embed = alert_embed(title, content, level=level)
        payload = {
            "username": f"{PRODUCT_NAME} v{VERSION}",
            "embeds": [embed.to_dict()],
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status >= 400:
                        logger.warning("Webhook notify failed: HTTP %s", resp.status)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Webhook notify error: %s", exc)

    async def _send_channel(self, content: str, *, title: str, level: str = "warn") -> None:
        channel_id = self._alert_channel_id()
        if not channel_id or not self._get_bot:
            return
        bot = self._get_bot()
        if not bot or not bot.is_ready():
            return
        try:
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
            if channel is None:
                return
            embed = alert_embed(title, content, level=level)
            embed.set_footer(text=DEVELOPER_CREDIT)
            await channel.send(embed=embed)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Channel notify error: %s", exc)

    async def _broadcast(self, content: str, *, title: str, level: str = "warn") -> None:
        await self._send_webhook(content, title=title, level=level)
        await self._send_channel(content, title=title, level=level)

    async def notify_disconnect(self, attempt: int) -> None:
        await self._broadcast(
            f"Bot disconnected. Reconnect attempt **{attempt}** in progress.\n{DEVELOPER_CREDIT}",
            title=f"{PRODUCT_NAME} Disconnect",
            level="warn",
        )

    async def notify_reconnect_success(self) -> None:
        await self._broadcast(
            "Bot reconnected successfully and is back online.",
            title=f"{PRODUCT_NAME} Reconnected",
            level="info",
        )

    async def notify_standby(self, attempts: int) -> None:
        await self._broadcast(
            f"Entered **standby mode** after **{attempts}** failed reconnect attempts.\n"
            "Run `/guard restart` or `POST /api/guard/restart` to resume.",
            title=f"{PRODUCT_NAME} Standby Mode",
            level="critical",
        )

    async def notify_heartbeat_failure(self, streak: int) -> None:
        await self._broadcast(
            f"Heartbeat check failed **{streak}** times consecutively.",
            title=f"{PRODUCT_NAME} Heartbeat Alert",
            level="warn",
        )