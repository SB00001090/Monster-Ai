"""Unified /ai command — local LLM + scam analyze."""
from __future__ import annotations

import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

from monster_ai.modules.discord.guard.ui.embeds import alert_embed, neon_footer


class AICommandsCog(commands.Cog):
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._rate: dict[int, deque[float]] = defaultdict(deque)

    def _allow(self, user_id: int, limit: int) -> bool:
        now = time.monotonic()
        q = self._rate[user_id]
        q.append(now)
        while q and now - q[0] > 60:
            q.popleft()
        return len(q) <= limit

    @app_commands.command(name="ai", description="查詢本地 Monster AI（對話或詐騙分析）")
    @app_commands.describe(prompt="你的問題或待分析文字", mode="chat 或 analyze")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="對話 chat", value="chat"),
            app_commands.Choice(name="詐騙分析 analyze", value="analyze"),
        ]
    )
    async def ai_cmd(
        self,
        interaction: discord.Interaction,
        prompt: str,
        mode: app_commands.Choice[str] | None = None,
    ) -> None:
        bot = self.bot
        guard = bot.guard_settings  # type: ignore[attr-defined]
        mode_val = mode.value if mode else "chat"

        if not self._allow(interaction.user.id, guard.chat_rate_limit_per_minute):
            await interaction.response.send_message("請稍後再試（速率限制）。", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        if mode_val == "analyze":
            svc = getattr(bot, "discord_service", None)
            client = svc._monster_client if svc else None  # noqa: SLF001
            if not client:
                await interaction.followup.send("Monster AI client 未連接。", ephemeral=True)
                return
            try:
                result = await client.analyze_scam(prompt)
                if result.get("error") == "consent_required":
                    await interaction.followup.send(
                        "需先同意連線本地 Monster AI（設定 MONSTER_AI_CONNECT_CONSENT=1）。",
                        ephemeral=True,
                    )
                    return
                is_scam = result.get("is_scam")
                embed = alert_embed(
                    "AI 詐騙分析結果",
                    f"**是否詐騙：** `{'是' if is_scam else '否'}`\n"
                    f"**風險分數：** `{result.get('score')}`\n"
                    f"**類型：** `{result.get('scam_type')}`\n"
                    f"**建議動作：** `{result.get('recommended_action')}`",
                    level="warn" if is_scam else "info",
                )
                await interaction.followup.send(embed=embed)
            except Exception as exc:  # noqa: BLE001
                await interaction.followup.send(f"分析失敗: {exc}", ephemeral=True)
            return

        chat_svc = bot.chat  # type: ignore[attr-defined]
        if not guard.chat_bridge_enabled or chat_svc is None:
            await interaction.followup.send("Chat Bridge 未啟用或未連接 Monster AI。", ephemeral=True)
            return
        try:
            result = await chat_svc.send(
                prompt,
                persona_mode="grok",
                user_id=f"discord:{interaction.user.id}",
                session_id=f"discord:{interaction.channel_id}",
            )
            content = result.get("content", "")
            backend = result.get("backend", "unknown")
            if len(content) > 1900:
                content = content[:1900] + "…"
            embed = discord.Embed(description=content, color=0x00F5FF)
            embed.set_footer(text=neon_footer() + f" · 後端 {backend}")
            await interaction.followup.send(embed=embed)
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"AI 查詢失敗: {exc}", ephemeral=True)


async def setup(bot: discord.Client) -> None:
    await bot.add_cog(AICommandsCog(bot))