"""Make / Sentry / platform integration webhooks."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class MakeHookBody(BaseModel):
    event: str = "deploy"
    detail: str = ""


def _make_secret(request: Request) -> str:
    env = request.app.state.settings.integrations.make_webhook_secret_env
    return os.environ.get(env, "")


@router.get("/status")
async def integrations_status(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    dify = getattr(request.app.state, "dify", None)
    learning = getattr(request.app.state, "learning", None)
    mini = getattr(request.app.state, "mini", None)

    dify_st: dict[str, Any] = {"enabled": False}
    if dify:
        dify_st = await dify.health()

    success: dict[str, Any] = {}
    if mini:
        success = mini.tracker.status()

    curriculum: dict[str, Any] = {}
    if learning:
        curriculum = learning.curriculum_status()

    return {
        "cloudflare_pages": "https://monster-ai.pages.dev",
        "dify": dify_st,
        "sentry_configured": bool(os.environ.get(settings.integrations.sentry_dsn_env)),
        "make_secret_configured": bool(_make_secret(request)),
        "mini_success": success,
        "curriculum": curriculum,
        "quality_threshold": settings.dify.min_quality_score,
    }


@router.post("/make/deploy-hook")
async def make_deploy_hook(body: MakeHookBody, request: Request) -> dict:
    secret = _make_secret(request)
    header = request.headers.get("x-make-secret", "")
    if secret and header != secret:
        raise HTTPException(403, "Invalid Make webhook secret")
    return {"ok": True, "event": body.event, "detail": body.detail}