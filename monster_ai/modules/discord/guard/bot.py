"""MonsterGuard Discord bot v2.0 — Developed by Suckbob | Monster AI Ecosystem."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from monster_ai.config import Settings
from monster_ai.modules.discord.constants import DEVELOPER_CREDIT, PRODUCT_NAME, VERSION
from monster_ai.modules.discord.guard.actions import ActionEngine
from monster_ai.modules.discord.guard.guild_config import GuildConfigStore
from monster_ai.modules.discord.guard.pipeline import DetectionPipeline
from monster_ai.modules.discord.guard.privacy import PrivacySafeLogger
from monster_ai.modules.discord.guard.ui.embeds import neon_footer

if TYPE_CHECKING:
    from monster_ai.core.self_repair import SelfRepairEngine
    from monster_ai.modules.chat.service import ChatService
    from monster_ai.modules.discord.bot import DiscordService
    from monster_ai.modules.roleplay.service import RoleplayService

logger = logging.getLogger(__name__)


class MonsterGuardBot(commands.Bot):
    def __init__(
        self,
        settings: Settings,
        *,
        repair: SelfRepairEngine | None = None,
        chat: ChatService | None = None,
        roleplay: RoleplayService | None = None,
        discord_service: DiscordService | None = None,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(command_prefix="!", intents=intents)

        self.monster_settings = settings
        self.guard_settings = settings.modules.discord.guard
        self.repair = repair
        self.chat = chat
        self.roleplay = roleplay
        self.discord_service = discord_service

        data_dir = Path(self.guard_settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

        self.guild_store = GuildConfigStore(data_dir / "guild_config.db")
        self.pipeline = DetectionPipeline(settings, repair, data_dir)
        self.privacy_log = PrivacySafeLogger(
            data_dir / "events.jsonl",
            retention_hours=self.guard_settings.privacy_retention_hours,
        )
        self.actions = ActionEngine(self.privacy_log)
        self._stats: dict[str, int] = {"scanned": 0, "blocked": 0, "warned": 0}
        self._guild_cmds_cleared = False

    async def setup_hook(self) -> None:
        await self.guild_store.init()
        from monster_ai.modules.discord.guard.cogs.guard_group import guard_group

        self.tree.add_command(guard_group)
        await self._load_cogs()
        try:
            await self.tree.sync()
            logger.info("MonsterGuard v%s slash commands synced", VERSION)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slash sync failed (set MONSTER_DISCORD_APP_ID?): %s", exc)

    async def _load_cogs(self) -> None:
        from monster_ai.modules.discord.guard.cogs import (
            admin,
            ai_commands,
            callguard,
            chat_bridge,
            commercial,
            education,
            features,
            intro,
            learning,
            monitor,
            report,
            setup_wizard,
        )

        await setup_wizard.setup(self)
        await admin.setup(self)
        await intro.setup(self)
        await monitor.setup(self)
        await callguard.setup(self)
        await ai_commands.setup(self)
        await chat_bridge.setup(self)
        await learning.setup(self)
        await education.setup(self)
        await features.setup(self)
        await report.setup(self)
        if self.guard_settings.trial_reminder_enabled:
            await commercial.setup(self)

    async def on_ready(self) -> None:
        logger.info(
            "%s v%s logged in as %s (%s guilds) — %s",
            PRODUCT_NAME,
            VERSION,
            self.user,
            len(self.guilds),
            DEVELOPER_CREDIT,
        )
        if self.discord_service:
            self.discord_service._reconnect.on_connect_success()  # noqa: SLF001
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{PRODUCT_NAME} v{VERSION} · /intro /status /防盜",
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Presence update skipped: %s", exc)
        if not self._guild_cmds_cleared:
            self._guild_cmds_cleared = True
            try:
                for guild in self.guilds:
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                logger.info("Cleared guild-scoped slash duplicates (global commands only)")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Guild command cleanup failed: %s", exc)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.exception("Slash command error: %s", error)
        msg = "指令執行失敗，請確認 Bot 在線並稍後再試。"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot or not self.guard_settings.welcome_intro_enabled:
            return
        try:
            from monster_ai.modules.discord.guard.cogs.intro import send_welcome_intro

            channel: discord.abc.Messageable | None = None
            cfg = await self.guild_store.get(member.guild.id)
            if cfg.mod_channel_id:
                channel = member.guild.get_channel(cfg.mod_channel_id)
            if channel is None and member.guild.system_channel:
                channel = member.guild.system_channel
            notify_id = self.guard_settings.notify_channel_id
            if channel is None and notify_id:
                channel = member.guild.get_channel(notify_id)
            if channel is None:
                return
            await send_welcome_intro(channel, self, member)
        except discord.Forbidden:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("Welcome intro failed: %s", exc)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            if guild.owner:
                from monster_ai.modules.discord.guard.capabilities import INTERCEPT_CATEGORIES

                intercept_preview = "、".join(c.title for c in INTERCEPT_CATEGORIES[:4]) + " 等"
                embed = discord.Embed(
                    title=f"{PRODUCT_NAME} v{VERSION} 已加入伺服器",
                    description=(
                        "感謝邀請 MonsterGuard！請執行 **`/guard setup`** 完成設定。\n\n"
                        f"**可攔截：**{intercept_preview}\n"
                        "**指令：** `/intro` `/monsterai` `/status` `/ai` `/callguard` `/防盜`\n\n"
                        "也可使用 **`/chat`** 與本地 Monster AI 對話。"
                    ),
                    color=0x00F5FF,
                )
                embed.set_footer(text=neon_footer())
                await guild.owner.send(embed=embed)
        except discord.Forbidden:
            pass

    async def on_message(self, message: discord.Message) -> None:
        await self.process_commands(message)

        if message.author.bot or not message.guild:
            return
        if not self.guard_settings.enabled:
            return

        guild_cfg = await self.guild_store.get(message.guild.id)
        if not guild_cfg.guard_enabled or not guild_cfg.setup_complete:
            return

        asyncio.create_task(self._scan_message_safe(message, guild_cfg))

    async def _scan_message_safe(self, message: discord.Message, guild_cfg) -> None:
        try:
            await self._scan_message(message, guild_cfg)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Guard pipeline error: %s", exc)

    async def _scan_message(self, message: discord.Message, guild_cfg) -> None:
        created = message.author.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        ctx = self.pipeline.build_context(
            content=message.content or "",
            author_id=message.author.id,
            author_name=str(message.author),
            account_created_at=created,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            attachment_names=[a.filename for a in message.attachments],
            mention_everyone=message.mention_everyone,
            guild_cfg=guild_cfg,
            is_bot=message.author.bot,
        )

        self._stats["scanned"] += 1
        result = await self.pipeline.analyze(ctx)
        action = await self.actions.execute(message, result, guild_cfg)
        if action == "blocked":
            self._stats["blocked"] += 1
        elif action == "warned":
            self._stats["warned"] += 1

    def status_dict(self) -> dict[str, Any]:
        return {
            "guilds": len(self.guilds),
            "rules_version": self.pipeline.rules_version,
            "scanned": self._stats["scanned"],
            "blocked": self._stats["blocked"],
            "warned": self._stats["warned"],
            "blocked_24h": 0,
            "guard_enabled": self.guard_settings.enabled,
            "chat_bridge": self.guard_settings.chat_bridge_enabled,
            "ai_backend": self.guard_settings.ai_backend,
            "mode": self.guard_settings.mode,
            "version": VERSION,
        }