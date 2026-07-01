"""Monster Guardian AI REST API."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/guardian", tags=["guardian"])


class SyncUploadRequest(BaseModel):
    provider: str = Field(pattern=r"^(google|github)$")
    provider_sub: str = Field(min_length=1)
    passphrase: str = Field(min_length=8)
    bundle_type: str = Field(pattern=r"^(oc_cards|chat_sessions|preferences|training_vault)$")
    payload: dict[str, Any] | list[Any]
    device_id: str = "web"


class SyncDownloadRequest(BaseModel):
    provider: str = Field(pattern=r"^(google|github)$")
    provider_sub: str = Field(min_length=1)
    passphrase: str = Field(min_length=8)
    bundle_type: str = Field(pattern=r"^(oc_cards|chat_sessions|preferences|training_vault)$")


class ErrorReportRequest(BaseModel):
    error_type: str
    message: str
    stack: str | None = None
    context: str | None = None
    source: str = "api"


class OCProtectRequest(BaseModel):
    card: dict[str, Any]
    owner_id: str = "local"


class BackstoryRequest(BaseModel):
    card: dict[str, Any]
    owner_id: str = "local"
    theme: str = ""
    ephemeral: bool = False
    multimodal: bool = True


class VaultMessageRequest(BaseModel):
    session_id: str
    message: dict[str, Any]
    vault_key: str = Field(min_length=8)
    ephemeral: bool | None = None


class QualityGateRequest(BaseModel):
    score: float = Field(ge=0.0, le=1.0)


class TrainingUnlockRequest(BaseModel):
    passphrase: str | None = Field(default=None, min_length=8)


class NetworkLearningConsentRequest(BaseModel):
    consented: bool = True
    metrics: bool = False


class NetworkLearningTriggerRequest(BaseModel):
    force: bool = False
    topics: list[str] | None = None


class TrainingTextAssetRequest(BaseModel):
    label: str = Field(pattern=r"^(template|prompt|lora)$")
    name: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None


def _guardian(request: Request):
    svc = getattr(request.app.state, "guardian", None)
    if svc is None or not svc.settings.enabled:
        raise HTTPException(503, "Monster Guardian AI disabled")
    return svc


def _network_learning(request: Request):
    svc = _guardian(request)
    if svc.network_learning is None:
        raise HTTPException(503, "Guardian network learning not initialized")
    return svc.network_learning


@router.get("/status")
async def guardian_status(request: Request) -> dict:
    svc = _guardian(request)
    return await svc.health()


@router.get("/disclaimer")
async def guardian_disclaimer(request: Request, locale: str = "zh-TW") -> dict:
    svc = _guardian(request)
    return svc.disclaimer(locale)


@router.post("/sync/upload")
async def sync_upload(body: SyncUploadRequest, request: Request) -> dict:
    svc = _guardian(request)
    return svc.sync_upload(
        provider=body.provider,
        provider_sub=body.provider_sub,
        passphrase=body.passphrase,
        bundle_type=body.bundle_type,
        payload=body.payload,
        device_id=body.device_id,
    )


@router.post("/sync/download")
async def sync_download(body: SyncDownloadRequest, request: Request) -> dict:
    svc = _guardian(request)
    return svc.sync_download(
        provider=body.provider,
        provider_sub=body.provider_sub,
        passphrase=body.passphrase,
        bundle_type=body.bundle_type,
    )


@router.get("/sync/list")
async def sync_list(
    request: Request,
    provider: str,
    provider_sub: str,
) -> dict:
    if provider not in {"google", "github"}:
        raise HTTPException(400, "provider must be google or github")
    svc = _guardian(request)
    return svc.sync_list(provider, provider_sub)


@router.post("/errors/report")
async def report_error(body: ErrorReportRequest, request: Request) -> dict:
    svc = _guardian(request)
    return await svc.report_error(
        error_type=body.error_type,
        message=body.message,
        stack=body.stack,
        context=body.context,
        source=body.source,
    )


@router.get("/errors/summary")
async def error_summary(request: Request) -> dict:
    svc = _guardian(request)
    return svc.errors.summarize()


@router.post("/learning/supervise")
async def supervise_learning(request: Request) -> dict:
    svc = _guardian(request)
    return await svc.supervise_learning()


@router.get("/learning/directives")
async def learning_directives(request: Request, limit: int = 5) -> dict:
    svc = _guardian(request)
    return {"directives": svc.supervisor.latest_directives(limit)}


@router.post("/oc/protect")
async def protect_oc(body: OCProtectRequest, request: Request) -> dict:
    svc = _guardian(request)
    return svc.protect_oc(body.card, owner_id=body.owner_id)


@router.post("/backstory/generate")
async def generate_backstory(body: BackstoryRequest, request: Request) -> dict:
    """Enhanced Character Backstory — OC fingerprint gate + structured sections + multimodal hints."""
    svc = _guardian(request)
    return await svc.generate_backstory(
        card=body.card,
        owner_id=body.owner_id,
        theme=body.theme,
        ephemeral=body.ephemeral,
        multimodal=body.multimodal,
    )


@router.post("/vault/message")
async def vault_message(body: VaultMessageRequest, request: Request) -> dict:
    svc = _guardian(request)
    return svc.vault_store(
        body.session_id,
        body.message,
        vault_key=body.vault_key,
        ephemeral=body.ephemeral,
    )


@router.post("/quality/gate")
async def quality_gate(body: QualityGateRequest, request: Request) -> dict:
    svc = _guardian(request)
    return svc.quality_gate(body.score)


@router.get("/training/status")
async def training_status(request: Request) -> dict:
    svc = _guardian(request)
    vault_status = svc.training_vault.status() if svc.training_vault else None
    return {
        "training_encryption_enabled": svc.settings.training_encryption_enabled,
        "encrypt_quality_assets": svc.settings.encrypt_quality_assets,
        "vault": vault_status,
    }


@router.post("/training/unlock")
async def training_unlock(body: TrainingUnlockRequest, request: Request) -> dict:
    svc = _guardian(request)
    return svc.unlock_training_vault(body.passphrase)


@router.post("/training/lock")
async def training_lock(request: Request) -> dict:
    svc = _guardian(request)
    return svc.lock_training_vault()


@router.post("/training/migrate")
async def training_migrate(request: Request) -> dict:
    svc = _guardian(request)
    settings = request.app.state.settings
    return svc.migrate_training_assets(Path(settings.modules.image.quality.data_dir))


@router.post("/training/store-text")
async def training_store_text(body: TrainingTextAssetRequest, request: Request) -> dict:
    svc = _guardian(request)
    if svc.training_vault is None:
        raise HTTPException(503, "Training vault disabled")
    path = svc.training_vault.store_text_asset(
        label=body.label,
        name=body.name,
        content=body.content,
        metadata=body.metadata,
    )
    return {"ok": True, "path": str(path), "encrypted": True}


@router.get("/training/export")
async def training_export(request: Request) -> dict:
    svc = _guardian(request)
    return svc.export_training_for_sync()


@router.post("/training/import")
async def training_import(bundle: dict[str, Any], request: Request) -> dict:
    svc = _guardian(request)
    payload = bundle.get("bundle", bundle)
    return svc.import_training_from_sync(payload)


@router.get("/network-learning/status")
async def network_learning_status(request: Request) -> dict:
    nl = _network_learning(request)
    return nl.status()


@router.post("/network-learning/consent")
async def network_learning_consent(
    body: NetworkLearningConsentRequest,
    request: Request,
) -> dict:
    nl = _network_learning(request)
    if body.consented:
        return nl.grant_consent(metrics=body.metrics)
    return nl.revoke_consent()


@router.post("/network-learning/trigger")
async def network_learning_trigger(
    body: NetworkLearningTriggerRequest,
    request: Request,
) -> dict:
    nl = _network_learning(request)
    return await nl.trigger(force=body.force, topics=body.topics)


@router.get("/network-learning/directives")
async def network_learning_directives(request: Request, limit: int = 5) -> dict:
    nl = _network_learning(request)
    return {"directives": nl.latest_directives(limit)}


@router.get("/connection")
async def connection_info(request: Request) -> dict:
    """Cloudflare Tunnel only — no Tailscale, no QR code."""
    import os

    svc = _guardian(request)
    tunnel = os.environ.get(svc.settings.tunnel_url_env, "")
    return {
        "mode": "cloudflare_tunnel",
        "tunnel_url": tunnel or None,
        "no_tailscale": True,
        "no_qr_code": True,
        "usb_apk_install": svc.settings.apk_usb_install_enabled,
        "oauth_providers": svc.settings.oauth_providers,
        "developer": "Developed by Suckbob | Monster Guardian AI",
    }