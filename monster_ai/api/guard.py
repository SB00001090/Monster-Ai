"""MonsterGuard API — AI analysis + dashboard status."""
from __future__ import annotations

import json
import re

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/guard", tags=["guard"])


class GuardAnalyzeRequest(BaseModel):
    prompt: str
    system: str | None = None


class GuardAnalyzeResponse(BaseModel):
    is_scam: bool = False
    score: int = 0
    confidence: float = 0.0
    scam_type: str = "none"
    reasons: list[str] = Field(default_factory=list)
    recommended_action: str = "monitor"


def _parse_llm_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


@router.post("/analyze", response_model=GuardAnalyzeResponse)
async def analyze_scam(request: Request, body: GuardAnalyzeRequest) -> GuardAnalyzeResponse:
    repair = request.app.state.repair
    system = body.system or (
        'Output JSON only: {"is_scam":bool,"confidence":0-1,"scam_type":"nitro|verification|'
        'crypto|hacked_dm|malware|raid|phishing|none","reasons":[],"recommended_action":'
        '"delete|warn|monitor"}'
    )
    raw = await repair.generate(body.prompt, system=system)
    data = _parse_llm_json(raw)
    is_scam = bool(data.get("is_scam"))
    confidence = float(data.get("confidence", 0.0))
    return GuardAnalyzeResponse(
        is_scam=is_scam,
        score=int(confidence * 40) if is_scam else 0,
        confidence=confidence,
        scam_type=data.get("scam_type", "none"),
        reasons=[f"ai:{r}" for r in data.get("reasons", [])],
        recommended_action=data.get("recommended_action", "delete" if is_scam else "monitor"),
    )


@router.get("/status")
async def guard_status(request: Request) -> dict:
    discord_svc = request.app.state.modules._modules.get("discord")  # noqa: SLF001

    base = {
        "guard_api": "ok",
        "version": "2.1.0",
        "llm_backend": request.app.state.repair.state.active_backend,
        "primary_ok": request.app.state.repair.state.primary_ok,
    }
    if discord_svc and hasattr(discord_svc, "guard_status"):
        base["bot"] = discord_svc.guard_status()
    else:
        base["bot"] = {"running": False, "message": "Discord bot not started"}
    return base


@router.post("/restart")
async def guard_restart(request: Request) -> dict:
    discord_svc = request.app.state.modules._modules.get("discord")  # noqa: SLF001
    if not discord_svc or not hasattr(discord_svc, "restart_guard"):
        return {"ok": False, "error": "discord_service_unavailable"}
    return await discord_svc.restart_guard()


@router.get("/logs")
async def guard_logs(limit: int = 50) -> dict:
    from monster_ai.modules.discord.bot import DiscordService

    safe_limit = max(1, min(limit, 200))
    return {"logs": DiscordService.read_logs(limit=safe_limit)}