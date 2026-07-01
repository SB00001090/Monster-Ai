"""Monster AI self-introduction — /intro and /monsterai."""
from __future__ import annotations

import discord
from discord import app_commands

from monster_ai.modules.discord.guard.integration.intro_generator import INTRO_STYLES, generate_intro
from monster_ai.modules.discord.guard.ui.embeds import intro_embed, neon_footer

_STYLE_CHOICES = [
    app_commands.Choice(name="正式守衛者 guardian", value="guardian"),
    app_commands.Choice(name="幽默 cyberpunk", value="cyberpunk"),
    app_commands.Choice(name="專業隱私守護者 privacy", value="privacy"),
]


async def _run_intro(
    interaction: discord.Interaction,
    style: str,
    *,
    member_name: str | None = None,
    public: bool = False,
) -> None:
    await interaction.response.defer(thinking=True, ephemeral=not public)
    bot = interaction.client
    text, color = await generate_intro(
        bot,  # type: ignore[arg-type]
        style=style,
        member_name=member_name or interaction.user.display_name,
    )
    embed = intro_embed(text, style=style, color=color)
    await interaction.followup.send(embed=embed, ephemeral=not public)


@app_commands.command(name="intro", description="Monster AI 動態自我介紹（可選風格）")
@app_commands.describe(
    style="介紹風格",
    public="是否公開到頻道（預設僅自己可見）",
)
@app_commands.choices(style=_STYLE_CHOICES)
async def intro_cmd(
    interaction: discord.Interaction,
    style: app_commands.Choice[str] | None = None,
    public: bool = False,
) -> None:
    await _run_intro(interaction, style.value if style else "guardian", public=public)


@app_commands.command(name="monsterai", description="Monster AI 自我介紹（與 /intro 相同）")
@app_commands.describe(style="介紹風格", public="是否公開到頻道")
@app_commands.choices(style=_STYLE_CHOICES)
async def monsterai_cmd(
    interaction: discord.Interaction,
    style: app_commands.Choice[str] | None = None,
    public: bool = False,
) -> None:
    await _run_intro(interaction, style.value if style else "cyberpunk", public=public)


async def send_welcome_intro(
    channel: discord.abc.Messageable,
    bot: discord.Client,
    member: discord.Member,
) -> None:
    """Auto welcome when a new member joins (if enabled in config)."""
    guard = bot.guard_settings  # type: ignore[attr-defined]
    if not getattr(guard, "welcome_intro_enabled", True):
        return
    default_style = getattr(guard, "welcome_intro_style", "cyberpunk")
    text, color = await generate_intro(
        bot,  # type: ignore[arg-type]
        style=default_style,
        member_name=member.display_name,
    )
    embed = intro_embed(
        f"歡迎 {member.mention} 加入伺服器！\n\n{text}",
        style=default_style,
        color=color,
        title="Monster AI · 歡迎加入",
    )
    embed.set_footer(text=neon_footer())
    await channel.send(embed=embed)


async def setup(bot: discord.Client) -> None:
    bot.tree.add_command(intro_cmd)
    bot.tree.add_command(monsterai_cmd)