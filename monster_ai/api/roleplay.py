"""Roleplay API — characters, sessions, messages."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from monster_ai.protection.guards import is_safe_path

router = APIRouter(prefix="/api/roleplay", tags=["roleplay"])


class CreateSessionRequest(BaseModel):
    title: str = "New Session"
    character_id: str | None = None


class MessageRequest(BaseModel):
    message: str
    character_id: str | None = None
    user_id: str = "default"
    web_search: bool | None = None


class LearnLoreRequest(BaseModel):
    query: str
    character_id: str | None = None
    force_refresh: bool = False


class SessionFeedbackRequest(BaseModel):
    user_id: str = "default"
    rating: int | None = Field(default=None, ge=1, le=5)
    thumbs: str | None = None
    comment: str = ""
    message: str = ""
    last_user_message: str = ""
    regenerate: bool = False


class ImportCharacterRequest(BaseModel):
    card: dict


class PortraitRequest(BaseModel):
    description: str | None = None
    quality_filter: bool | None = True
    width: int | None = Field(default=None, ge=256, le=1024)
    height: int | None = Field(default=None, ge=256, le=1024)


class AvatarRequest(BaseModel):
    image_path: str


def _check_rate(request: Request) -> None:
    limiter = request.app.state.rate_limiter
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(429, "Rate limit exceeded")


@router.get("/characters")
async def list_characters(request: Request) -> list:
    return request.app.state.roleplay.list_characters()


@router.get("/characters/{character_id}")
async def get_character(character_id: str, request: Request) -> dict:
    card = request.app.state.roleplay.get_character(character_id)
    if not card:
        raise HTTPException(404, "Character not found")
    return card.model_dump()


@router.post("/characters/import")
async def import_character_json(body: ImportCharacterRequest, request: Request) -> dict:
    card = request.app.state.roleplay.import_character_json(body.card)
    return {"id": card.id, "name": card.name}


@router.delete("/characters/{character_id}")
async def delete_character(character_id: str, request: Request) -> dict:
    if not request.app.state.roleplay.delete_character(character_id):
        raise HTTPException(404, "Character not found")
    return {"success": True}


@router.post("/characters/upload")
async def upload_character(request: Request, file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "card.json").suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        card = request.app.state.roleplay.import_character(tmp_path)
        return {"id": card.id, "name": card.name}
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/sessions")
async def list_sessions(request: Request) -> list:
    return request.app.state.roleplay.list_sessions()


@router.post("/sessions")
async def create_session(body: CreateSessionRequest, request: Request) -> dict:
    session = request.app.state.roleplay.create_session(body.title, body.character_id)
    return session.model_dump()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict:
    session = request.app.state.roleplay.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.model_dump()


@router.post("/characters/{character_id}/portrait")
async def generate_portrait(
    character_id: str, body: PortraitRequest, request: Request
) -> dict:
    _check_rate(request)
    try:
        return await request.app.state.roleplay.generate_portrait(
            character_id,
            description=body.description,
            quality_filter=body.quality_filter,
            width=body.width,
            height=body.height,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@router.patch("/characters/{character_id}/avatar")
async def set_avatar(character_id: str, body: AvatarRequest, request: Request) -> dict:
    try:
        card = request.app.state.roleplay.set_avatar(character_id, body.image_path)
        return {
            "id": card.id,
            "name": card.name,
            "avatar": card.avatar,
            "avatar_url": f"/api/roleplay/files/avatars/{character_id}.png",
        }
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/files/avatars/{filename}")
async def get_avatar_file(filename: str, request: Request) -> FileResponse:
    roots = request.app.state.settings.protection.allowed_data_roots
    path = Path("./data/characters/avatars") / filename
    if not is_safe_path(path, roots) or not path.exists():
        raise HTTPException(404, "Avatar not found")
    return FileResponse(path)


@router.post("/sessions/{session_id}/message")
async def send_message(session_id: str, body: MessageRequest, request: Request) -> dict:
    _check_rate(request)
    try:
        return await request.app.state.roleplay.send_message(
            session_id,
            body.message,
            character_id=body.character_id,
            user_id=body.user_id,
            web_search=body.web_search,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/sessions/{session_id}/learn-lore")
async def session_learn_lore(
    session_id: str, body: LearnLoreRequest, request: Request
) -> dict:
    crimeguard = getattr(request.app.state, "crimeguard", None)
    if crimeguard is not None and crimeguard.state.network_locked:
        raise HTTPException(403, "Network locked by CrimeGuard")
    return await request.app.state.roleplay.learn_lore(
        body.query,
        character_id=body.character_id,
        session_id=session_id,
        force_refresh=body.force_refresh,
    )


@router.post("/characters/{character_id}/learn-lore")
async def character_learn_lore(
    character_id: str, body: LearnLoreRequest, request: Request
) -> dict:
    crimeguard = getattr(request.app.state, "crimeguard", None)
    if crimeguard is not None and crimeguard.state.network_locked:
        raise HTTPException(403, "Network locked by CrimeGuard")
    return await request.app.state.roleplay.learn_lore(
        body.query,
        character_id=character_id,
        force_refresh=body.force_refresh,
    )


@router.post("/sessions/{session_id}/feedback")
async def session_feedback(
    session_id: str, body: SessionFeedbackRequest, request: Request
) -> dict:
    learning = request.app.state.learning
    if body.regenerate or body.thumbs == "down":
        return await learning.record_feedback_and_regenerate(
            user_id=body.user_id,
            session_id=session_id,
            thumbs=body.thumbs,
            comment=body.comment,
            message=body.message,
            last_user_message=body.last_user_message,
        )
    return learning.record_feedback(
        user_id=body.user_id,
        session_id=session_id,
        rating=body.rating,
        thumbs=body.thumbs,
        comment=body.comment,
        message=body.message,
    )