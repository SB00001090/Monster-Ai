"""Monster AI ecosystem one-click network install API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from monster_ai.modules.ecosystem.disclaimer import privacy_notice

router = APIRouter(prefix="/api/ecosystem", tags=["ecosystem"])


class EcosystemConsentRequest(BaseModel):
    grant: bool = True
    allow_r18: bool = True
    allow_downloads: bool = True


class EcosystemInstallRequest(BaseModel):
    bundle: str = Field(default="full", description="full | mini | r18_multimodal | roleplay | image_video | audio")


@router.get("/privacy")
async def ecosystem_privacy(locale: str = "zh-TW") -> dict:
    return privacy_notice(locale)


@router.get("/info")
async def ecosystem_info(request: Request) -> dict:
    inst = _require(request)
    return inst.info()


@router.get("/status")
async def ecosystem_status(request: Request) -> dict:
    inst = _require(request)
    return inst.status()


@router.get("/bundles")
async def ecosystem_bundles(request: Request) -> dict:
    inst = _require(request)
    return {"bundles": inst.info()["bundles"]}


@router.post("/consent")
async def ecosystem_consent(body: EcosystemConsentRequest, request: Request) -> dict:
    inst = _require(request)
    if body.grant:
        return inst.grant_consent(allow_r18=body.allow_r18, allow_downloads=body.allow_downloads)
    return inst.revoke_consent()


@router.post("/install")
async def ecosystem_install(body: EcosystemInstallRequest, request: Request) -> dict:
    inst = _require(request)
    crimeguard = getattr(request.app.state, "crimeguard", None)
    if crimeguard is not None and crimeguard.state.network_locked:
        raise HTTPException(403, "Network locked by CrimeGuard")
    if body.bundle == "r18_multimodal" and not inst.settings.allow_r18_bundle:
        raise HTTPException(403, "R18 bundle disabled in config")
    result = await inst.start(body.bundle)
    if not result.get("ok"):
        raise HTTPException(400, result.get("reason", "install_failed"))
    return result


@router.post("/stop")
async def ecosystem_stop(request: Request) -> dict:
    inst = _require(request)
    return await inst.stop()


def _require(request: Request):
    inst = getattr(request.app.state, "ecosystem", None)
    if inst is None or not inst.settings.enabled:
        raise HTTPException(503, "Ecosystem installer disabled")
    return inst