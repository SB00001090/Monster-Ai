"""Monster AI Chat Bridge — /chat slash command."""
from __future__ import annotations

import time
from collections import defaultdict, deque

import discord
from discord import app_commands


class ChatBridgeCog(discord.ext.commands.Cog):
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

    @app_commands.command(name="chat", description="與 Monster AI 對話（使用本地 LLM）")
    @app_commands.describe(message="你的訊息", persona="Persona 模式：grok / off")
    async def chat(
        self,
        interaction: discord.Interaction,
        message: str,
        persona: str = "grok",
    ) -> None:
        bot = self.bot
        guard = bot.guard_settings  # type: ignore[attr-defined]
        chat_svc = bot.chat  # type: ignore[attr-defined]

        if not guard.chat_bridge_enabled:
            await interaction.response.send_message("Chat Bridge 未啟用。", ephemeral=True)
            return
        if chat_svc is None:
            await interaction.response.send_message(
                "Monster AI Chat 服務未連接。請以 embedded 模式啟動 Monster AI。",
                ephemeral=True,
            )
            return
        if not self._allow(interaction.user.id, guard.chat_rate_limit_per_minute):
            await interaction.response.send_message("請稍後再試（速率限制）。", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            result = await chat_svc.send(
                message,
                persona_mode=persona,
                user_id=f"discord:{interaction.user.id}",
                session_id=f"discord:{interaction.channel_id}",
            )
            content = result.get("content", "")
            backend = result.get("backend", "unknown")
            if len(content) > 1900:
                content = content[:1900] + "…"
            embed = discord.Embed(description=content, color=0x6EE7B7)
            embed.set_footer(text=f"Monster AI · 後端 {backend}")
            await interaction.followup.send(embed=embed)
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"Chat 失敗: {exc}", ephemeral=True)

    async def _resolve_session_id(
        self,
        roleplay_svc,
        interaction: discord.Interaction,
        session_id: str | None,
        *,
        new_session: bool,
    ) -> str | None:
        if session_id:
            return session_id.strip()
        if new_session:
            session = roleplay_svc.create_session(
                title=f"Discord · {interaction.user.display_name}",
            )
            return session.id
        sessions = roleplay_svc.list_sessions()
        if sessions:
            return str(sessions[0]["id"])
        session = roleplay_svc.create_session(
            title=f"Discord · {interaction.user.display_name}",
        )
        return session.id

    @app_commands.command(name="roleplay", description="Monster AI 角色扮演對話")
    @app_commands.describe(
        message="你的訊息（留空則列出 sessions；前綴 搜尋: 強制上網查世界觀）",
        session_id="Roleplay session ID（可留空，自動使用最新或新建）",
        new_session="強制建立新 session",
        web_search="強制連接網絡學習世界觀（可選）",
    )
    async def roleplay(
        self,
        interaction: discord.Interaction,
        message: str | None = None,
        session_id: str | None = None,
        new_session: bool = False,
        web_search: bool | None = None,
    ) -> None:
        bot = self.bot
        roleplay_svc = bot.roleplay  # type: ignore[attr-defined]
        settings = bot.monster_settings  # type: ignore[attr-defined]

        if roleplay_svc is None or not settings.modules.roleplay.enabled:
            await interaction.response.send_message("Roleplay 模組未啟用。", ephemeral=True)
            return

        if not (message or "").strip() and not session_id and not new_session:
            sessions = roleplay_svc.list_sessions()[:8]
            if not sessions:
                lines = [
                    "尚無 roleplay session。",
                    "請執行 `/roleplay message:你好 new_session:True` 建立新對話。",
                    "",
                    "或在 Web UI 建立：",
                    "1. 開啟 http://127.0.0.1:7860",
                    "2. 進入 Roleplay 分頁 → New Session",
                    "3. 複製 session `id` 到 `/roleplay session_id:...`",
                ]
            else:
                lines = ["**可用 Roleplay Sessions：**", ""]
                for s in sessions:
                    lines.append(
                        f"• `{s['id']}` — {s.get('title', '?')} "
                        f"({s.get('message_count', 0)} msgs)"
                    )
                lines += [
                    "",
                    "用法：`/roleplay message:你的台詞 session_id:上方ID`",
                    "或省略 session_id 自動使用最新 session。",
                ]
            embed = discord.Embed(
                title="Monster AI 角色扮演 Sessions",
                description="\n".join(lines),
                color=0xA78BFA,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        resolved = await self._resolve_session_id(
            roleplay_svc, interaction, session_id, new_session=new_session
        )
        if not resolved:
            await interaction.response.send_message("無法建立 session。", ephemeral=True)
            return
        if not (message or "").strip():
            await interaction.response.send_message(
                f"已選擇 session：`{resolved}`\n請加上 `message:` 開始對話。",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        try:
            force_web = web_search
            if force_web is None and message.strip().lower().startswith(("搜尋:", "搜尋：", "search:")):
                force_web = True
            result = await roleplay_svc.send_message(
                resolved,
                message.strip(),
                user_id=f"discord:{interaction.user.id}",
                web_search=force_web,
            )
            content = result.get("content", result.get("message", ""))
            if len(str(content)) > 1900:
                content = str(content)[:1900] + "…"
            embed = discord.Embed(description=str(content), color=0xA78BFA)
            footer = f"Monster AI 角色扮演 · session {resolved[:8]}…"
            if result.get("web_lore_used"):
                footer += " · 網絡世界觀"
            embed.set_footer(text=footer)
            await interaction.followup.send(embed=embed)
        except Exception as exc:  # noqa: BLE001
            await interaction.followup.send(f"Roleplay 失敗: {exc}", ephemeral=True)


async def setup(bot: discord.Client) -> None:
    await bot.add_cog(ChatBridgeCog(bot))