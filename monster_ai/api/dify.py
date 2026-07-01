"""Dify parallel orchestration API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/dify", tags=["dify"])


class DifyGenerateRequest(BaseModel):
    prompt: str
    template_id: str = "stable"
    locale: str = "zh-TW"


@router.get("/status")
async def dify_status(request: Request) -> dict:
    bridge = getattr(request.app.state, "dify", None)
    if not bridge:
        return {"enabled": False, "configured": False}
    return await bridge.health()


@router.get("/workflows")
async def dify_workflows(request: Request) -> dict:
    settings = request.app.state.settings.dify
    return {
        "image": settings.workflow_image_id or None,
        "multimodal": settings.workflow_multimodal_id or None,
        "min_quality_score": settings.min_quality_score,
    }


@router.post("/generate")
async def dify_generate(body: DifyGenerateRequest, request: Request) -> dict:
    bridge = getattr(request.app.state, "dify", None)
    mini = request.app.state.mini
    if not bridge:
        raise HTTPException(503, "Dify bridge not initialized")

    async def _fallback() -> dict:
        return await mini.generate_r18(
            body.prompt,
            template_id=body.template_id,
            locale=body.locale,
        )

    try:
        return await bridge.generate_image(
            prompt=body.prompt,
            template_id=body.template_id,
            locale=body.locale,
            fallback_fn=_fallback,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc