"""Run MonsterGuard v2.0 standalone — Developed by Suckbob | Monster AI Ecosystem."""
from __future__ import annotations

import asyncio
import logging
import os
import sys

from monster_ai.config import load_settings
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.chat.service import ChatService
from monster_ai.modules.discord.bot import DiscordService
from monster_ai.modules.roleplay.service import RoleplayService

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    settings.modules.discord.enabled = True
    settings.modules.discord.guard.mode = "standalone"

    token = os.getenv(settings.modules.discord.token_env, "").strip()
    if not token:
        root_token = __import__("pathlib").Path("discord.token.local")
        if root_token.is_file():
            lines = [
                ln.strip()
                for ln in root_token.read_text(encoding="utf-8-sig").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            token = lines[0] if lines else ""
    if not token:
        print(f"Set {settings.modules.discord.token_env} or discord.token.local", file=sys.stderr)
        sys.exit(1)
    os.environ[settings.modules.discord.token_env] = token

    repair = SelfRepairEngine(settings)
    await repair.start()

    chat = ChatService(repair, settings)
    roleplay = RoleplayService(settings, repair) if settings.modules.roleplay.enabled else None

    svc = DiscordService(settings)
    try:
        await svc.start_guard(repair, chat, roleplay)
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await svc.stop_guard()
        await repair.stop()


if __name__ == "__main__":
    asyncio.run(main())