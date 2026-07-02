"""Discord one-click error reporting — webhook or MonsterGuard bridge."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEVELOPER = "Developed by Suckbob | Guardian Ai"


async def send_discord_error_report(
    *,
    webhook_url: str,
    error_type: str,
    message: str,
    stack: str | None = None,
    context: str | None = None,
    source: str = "guardian",
    account_id: str | None = None,
) -> dict[str, Any]:
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return {"ok": False, "reason": "invalid_webhook_url"}

    embed = {
        "title": f"Guardian Ai Error · {error_type}",
        "description": (message or "")[:1800],
        "color": 0xE74C3C,
        "fields": [
            {"name": "Source", "value": source, "inline": True},
            {"name": "Developer", "value": DEVELOPER, "inline": True},
        ],
        "footer": {"text": "Guardian Ai · Discord quick report"},
    }
    if account_id:
        embed["fields"].append({"name": "Account", "value": account_id[:64], "inline": True})
    if context:
        embed["fields"].append({"name": "Context", "value": context[:900], "inline": False})
    if stack:
        embed["fields"].append({"name": "Stack", "value": f"```\n{stack[:900]}\n```", "inline": False})

    payload = {"embeds": [embed]}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                webhook_url,
                content="**Guardian Ai 錯誤回報**",
                json=payload,
            )
            if r.status_code >= 400:
                return {"ok": False, "reason": f"discord_http_{r.status_code}", "body": r.text[:200]}
        return {"ok": True, "channel": "discord_webhook"}
    except httpx.HTTPError as exc:
        logger.warning("Discord report failed: %s", exc)
        return {"ok": False, "reason": "discord_request_failed"}