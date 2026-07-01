"""Commercial trial + regional pricing API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from monster_ai.modules.commercial.trial import TrialManager

router = APIRouter(prefix="/api/commercial", tags=["commercial"])


class UnlockBody(BaseModel):
    purchase_token: str = ""


def _trial(request: Request) -> TrialManager:
    settings = request.app.state.settings
    data_dir = getattr(settings, "commercial", None)
    path = "./data/commercial"
    if data_dir and hasattr(data_dir, "data_dir"):
        path = data_dir.data_dir
    return TrialManager(path)


@router.get("/pricing")
async def pricing(region: str = "GLOBAL") -> dict:
    return TrialManager.pricing(region)


@router.get("/pricing/all")
async def pricing_all() -> dict:
    return {"plans": TrialManager.all_pricing(), "developer": "Suckbob | Monster AI"}


@router.get("/trial")
async def trial_status(request: Request) -> dict:
    return _trial(request).status()


@router.post("/trial/start")
async def trial_start(request: Request) -> dict:
    return _trial(request).start_trial()


@router.post("/unlock")
async def unlock_lifetime(body: UnlockBody, request: Request) -> dict:
    """Dev/local unlock — production should verify payment webhook."""
    settings = request.app.state.settings
    secret = getattr(getattr(settings, "commercial", None), "unlock_dev_token", "")
    if secret and body.purchase_token != secret:
        raise HTTPException(403, "Invalid purchase token")
    return _trial(request).unlock_lifetime(token=body.purchase_token)