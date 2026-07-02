"""Generation API — image, video, TTS."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from monster_ai.modules.generation.router import GenerationRouter
from monster_ai.modules.image.model_presets import list_presets_for_api
from monster_ai.modules.prompt.anti_collapse import DEFAULT_NEGATIVE
from monster_ai.protection.guards import is_safe_path

router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.get("/progress")
async def generation_progress(request: Request) -> dict:
    return request.app.state.gen_progress.to_dict()


@router.get("/checkpoints")
async def list_checkpoints(request: Request) -> dict:
    image = request.app.state.image
    ckpts = await image.list_checkpoints()
    active = image.active_checkpoint
    if not active and ckpts:
        active, _ = await image.client.resolve_checkpoint_name(
            request.app.state.settings.modules.image.checkpoint
        )
    return {
        "checkpoints": ckpts,
        "active": active,
        "config": request.app.state.settings.modules.image.checkpoint,
    }


@router.get("/loras")
async def list_lora_models(request: Request) -> dict:
    loras = await request.app.state.image.list_loras()
    return {"loras": loras}


@router.get("/defaults")
async def generation_defaults() -> dict:
    return {"default_negative": DEFAULT_NEGATIVE}


@router.get("/model-presets")
async def list_model_presets(request: Request) -> dict:
    image = request.app.state.image
    ckpts = await image.list_checkpoints()
    cfg_default = request.app.state.settings.modules.image.checkpoint
    return {"presets": list_presets_for_api(ckpts, config_default=cfg_default)}


@router.get("/backends")
async def list_generation_backends(request: Request) -> dict:
    image = request.app.state.image
    ckpts = await image.list_checkpoints()
    gen_router: GenerationRouter = request.app.state.generation_router
    return {"backends": gen_router.list_backends(ckpts)}


@router.get("/resolutions")
async def list_generation_resolutions(request: Request) -> dict:
    gen_router: GenerationRouter = request.app.state.generation_router
    return {"resolutions": gen_router.list_resolutions()}


class ImageRequest(BaseModel):
    prompt: str
    negative: str | None = None
    lora: str | None = None
    lora_strength: float | None = None
    width: int | None = None
    height: int | None = None
    style: str | None = None
    backend: str | None = Field(default=None, description="sd15 | sdxl | flux | pony")
    vae: str | None = Field(default=None, description="VAE filename or auto")
    checkpoint: str | None = None
    enhance_prompt: bool = True
    quality_filter: bool | None = None
    max_quality_retries: int | None = Field(default=None, ge=0, le=5)


class VideoRequest(BaseModel):
    prompt: str
    frames: int | None = None
    fps: int | None = None
    width: int | None = Field(default=None, ge=256, le=2048)
    height: int | None = Field(default=None, ge=256, le=2048)


class TTSRequest(BaseModel):
    text: str


class TTSCloneRequest(BaseModel):
    text: str
    reference_id: str


class FromChatRequest(BaseModel):
    session_id: str
    message: str | None = None


def _check_rate(request: Request) -> None:
    limiter = request.app.state.rate_limiter
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(429, "Rate limit exceeded")


def _check_crimeguard(request: Request, prompt: str) -> None:
    cg = getattr(request.app.state, "crimeguard", None)
    if cg is None:
        return
    allowed, reason = cg.is_generation_allowed(prompt)
    if not allowed:
        raise HTTPException(403, f"CrimeGuard: {reason}")


def _safe_file(path: Path, allowed_roots: list[str]) -> Path:
    if not is_safe_path(path, allowed_roots):
        raise HTTPException(403, "Path not allowed")
    if not path.exists():
        raise HTTPException(404, "File not found")
    return path


@router.post("/image")
async def generate_image(body: ImageRequest, request: Request) -> dict:
    _check_rate(request)
    _check_crimeguard(request, body.prompt)
    image = request.app.state.image
    gen_router: GenerationRouter = request.app.state.generation_router
    try:
        return await image.generate(
            body.prompt,
            negative=body.negative,
            lora=body.lora,
            lora_strength=body.lora_strength,
            width=body.width,
            height=body.height,
            style=body.style,
            backend=body.backend,
            vae=body.vae,
            checkpoint=body.checkpoint,
            enhance_prompt=body.enhance_prompt,
            quality_filter=body.quality_filter,
            max_quality_retries=body.max_quality_retries,
            generation_router=gen_router,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@router.post("/image/from-chat")
async def generate_image_from_chat(body: FromChatRequest, request: Request) -> dict:
    _check_rate(request)
    roleplay = request.app.state.roleplay
    session = roleplay.get_session(body.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    prompt = body.message
    if not prompt and session.messages:
        prompt = session.messages[-1].get("content", "")
    if not prompt:
        raise HTTPException(400, "No prompt available")
    _check_crimeguard(request, prompt)
    image = request.app.state.image
    return await image.generate(prompt)


@router.post("/video")
async def generate_video(body: VideoRequest, request: Request) -> dict:
    _check_rate(request)
    _check_crimeguard(request, body.prompt)
    video = request.app.state.video
    try:
        return await video.generate(
            body.prompt,
            frames=body.frames,
            fps=body.fps,
            width=body.width,
            height=body.height,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@router.post("/tts")
async def generate_tts(body: TTSRequest, request: Request) -> dict:
    _check_rate(request)
    _check_crimeguard(request, body.text)
    tts = request.app.state.tts
    try:
        return await tts.synthesize(body.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@router.post("/tts/clone")
async def generate_tts_clone(body: TTSCloneRequest, request: Request) -> dict:
    _check_rate(request)
    _check_crimeguard(request, body.text)
    tts = request.app.state.tts
    try:
        return await tts.clone(body.text, body.reference_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@router.get("/files/images/{filename}")
async def get_image_file(filename: str, request: Request) -> FileResponse:
    roots = request.app.state.settings.protection.allowed_data_roots
    path = _safe_file(Path("./data/outputs/images") / filename, roots)
    return FileResponse(path)


@router.get("/files/mini/{filename}")
async def get_mini_image_file(filename: str, request: Request) -> FileResponse:
    roots = request.app.state.settings.protection.allowed_data_roots
    mini_dir = request.app.state.settings.modules.mini.output_dir
    path = _safe_file(Path(mini_dir) / filename, roots)
    return FileResponse(path)


@router.get("/files/videos/{filename}")
@router.head("/files/videos/{filename}")
async def get_video_file(filename: str, request: Request) -> FileResponse:
    roots = request.app.state.settings.protection.allowed_data_roots
    path = _safe_file(Path("./data/outputs/videos") / filename, roots)
    return FileResponse(path, media_type="video/mp4")


@router.get("/files/audio/{filename}")
async def get_audio_file(filename: str, request: Request) -> FileResponse:
    roots = request.app.state.settings.protection.allowed_data_roots
    path = _safe_file(Path("./data/outputs/audio") / filename, roots)
    return FileResponse(path)