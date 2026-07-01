"""Mini Monster AI API — R18+ image, likeness, voice, multimodal."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mini", tags=["mini"])


class MiniGenerateRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
    template_id: str | None = None
    locale: str | None = None
    lora: str | None = None
    checkpoint: str | None = None
    enhance_prompt: bool | None = None


class MiniLikenessRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
    reference_id: str = Field(min_length=4, max_length=64)
    template_id: str | None = "idol_likeness"
    locale: str | None = None


class MiniMultimodalRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
    reference_id: str = Field(min_length=4, max_length=64)
    voice_text: str | None = None
    template_id: str | None = "idol_likeness"
    locale: str | None = None


class MiniVoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    reference_id: str = Field(min_length=4, max_length=64)
    locale: str | None = None


class MiniFeedbackRequest(BaseModel):
    ok: bool
    template_id: str = "hq"
    similarity_score: float | None = Field(default=None, ge=0.0, le=1.0)


class MiniConsentRequest(BaseModel):
    grant: bool = True
    downloads: bool = False
    metrics: bool = False


class MiniOptimizeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    locale: str | None = None


@router.get("/disclaimer")
async def mini_disclaimer(request: Request, locale: str = "zh-TW") -> dict:
    mini = getattr(request.app.state, "mini", None)
    if mini is None:
        raise HTTPException(503, "Mini Monster AI not loaded")
    return mini.disclaimer(locale)


@router.get("/info")
async def mini_info(request: Request) -> dict:
    mini = getattr(request.app.state, "mini", None)
    if mini is None:
        raise HTTPException(503, "Mini Monster AI not loaded")
    return mini.info()


@router.get("/success")
async def mini_success(request: Request) -> dict:
    mini = getattr(request.app.state, "mini", None)
    if mini is None:
        raise HTTPException(503, "Mini Monster AI not loaded")
    return mini.tracker.status()


@router.get("/references")
async def mini_list_references(request: Request) -> dict:
    mini = _require_mini(request)
    return {"references": mini.refs.list_profiles()}


@router.post("/reference/upload")
async def mini_upload_reference(
    request: Request,
    name: str = Form(...),
    image: UploadFile = File(...),
    voice: UploadFile | None = File(None),
    likeness_lora: str | None = Form(None),
) -> dict:
    mini = _require_mini(request)
    img_bytes = await image.read()
    if len(img_bytes) < 100:
        raise HTTPException(400, "Invalid reference image")
    voice_bytes = await voice.read() if voice else None
    ext = Path_suffix(image.filename)
    try:
        return mini.register_reference(
            name=name,
            image_bytes=img_bytes,
            image_ext=ext,
            voice_bytes=voice_bytes,
            likeness_lora=likeness_lora,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def Path_suffix(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ".png"
    return "." + filename.rsplit(".", 1)[-1].lower()


@router.post("/optimize")
async def mini_optimize(body: MiniOptimizeRequest, request: Request) -> dict:
    mini = _require_mini(request)
    return await mini.optimize_prompt(body.prompt, locale=body.locale)


@router.post("/generate")
async def mini_generate(body: MiniGenerateRequest, request: Request) -> dict:
    mini = _require_mini(request)
    try:
        return await mini.generate_r18(
            body.prompt,
            template_id=body.template_id,
            locale=body.locale,
            lora=body.lora,
            checkpoint=body.checkpoint,
            enhance_prompt=body.enhance_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/generate/likeness")
async def mini_generate_likeness(body: MiniLikenessRequest, request: Request) -> dict:
    mini = _require_mini(request)
    try:
        return await mini.generate_likeness(
            body.prompt,
            reference_id=body.reference_id,
            template_id=body.template_id,
            locale=body.locale,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/generate/multimodal")
async def mini_generate_multimodal(body: MiniMultimodalRequest, request: Request) -> dict:
    mini = _require_mini(request)
    try:
        return await mini.generate_multimodal(
            body.prompt,
            reference_id=body.reference_id,
            voice_text=body.voice_text,
            template_id=body.template_id,
            locale=body.locale,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/voice/clone")
async def mini_voice_clone(body: MiniVoiceRequest, request: Request) -> dict:
    mini = _require_mini(request)
    try:
        return await mini.clone_voice(
            body.text,
            reference_id=body.reference_id,
            locale=body.locale,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/feedback")
async def mini_feedback(body: MiniFeedbackRequest, request: Request) -> dict:
    mini = _require_mini(request)
    return await mini.record_feedback(
        ok=body.ok,
        template_id=body.template_id,
        similarity_score=body.similarity_score,
    )


@router.post("/network/consent")
async def mini_network_consent(body: MiniConsentRequest, request: Request) -> dict:
    mini = _require_mini(request)
    return await mini.network_consent(
        grant=body.grant,
        downloads=body.downloads,
        metrics=body.metrics,
    )


@router.get("/network/catalog")
async def mini_network_catalog(request: Request, q: str = "likeness lora sdxl") -> dict:
    mini = _require_mini(request)
    return await mini.network_catalog(q)


def _require_mini(request: Request):
    mini = getattr(request.app.state, "mini", None)
    if mini is None or not mini.enabled:
        raise HTTPException(503, "Mini Monster AI disabled")
    return mini