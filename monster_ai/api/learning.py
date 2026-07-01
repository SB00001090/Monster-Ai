"""Autonomous learning API (Phase C)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/learning", tags=["learning"])


class FeedbackRequest(BaseModel):
    user_id: str = "default"
    session_id: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    thumbs: str | None = None
    comment: str = ""
    message: str = ""
    last_user_message: str = ""
    regenerate: bool = False


class CurriculumStartRequest(BaseModel):
    duration_hours: float | None = Field(default=None, ge=1, le=168)
    resume: bool = True
    fast_mode: bool = False
    mode: str = "base"  # base | extended | languages | cybersec | after_ai


@router.get("/curriculum/status")
async def curriculum_status(request: Request) -> dict:
    engine = request.app.state.learning
    return engine.curriculum_status()


@router.get("/curriculum/topics")
async def curriculum_topics(request: Request, mode: str = "base") -> dict:
    from monster_ai.modules.learning.curriculum import build_curriculum, default_hours_for_mode, topic_count

    phases = build_curriculum(mode)
    return {
        "mode": mode,
        "total_topics": topic_count(mode),
        "duration_hours_default": default_hours_for_mode(mode),
        "phases": [
            {
                "id": p.id,
                "title": p.title,
                "hours": p.hours,
                "topic_count": len(p.topics),
                "topics": [
                    {"id": t.id, "query_zh": t.query_zh, "track": t.track} for t in p.topics
                ],
            }
            for p in phases
        ],
    }


@router.post("/curriculum/start")
async def curriculum_start(body: CurriculumStartRequest, request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.settings.curriculum_enabled:
        raise HTTPException(503, "Curriculum disabled")
    crimeguard = getattr(request.app.state, "crimeguard", None)
    if crimeguard is not None and crimeguard.state.network_locked:
        raise HTTPException(403, "Network locked by CrimeGuard")
    return await engine.start_curriculum(
        duration_hours=body.duration_hours,
        resume=body.resume,
        fast_mode=body.fast_mode,
        mode=body.mode,
    )


@router.post("/curriculum/stop")
async def curriculum_stop(request: Request) -> dict:
    engine = request.app.state.learning
    return await engine.stop_curriculum()


@router.get("/status")
async def learning_status(request: Request) -> dict:
    engine = request.app.state.learning
    return await engine.health()


class WebLearnRequest(BaseModel):
    query: str
    force_refresh: bool = False


class WebSearchRequest(BaseModel):
    query: str


@router.get("/web/status")
async def web_learning_status(request: Request) -> dict:
    engine = request.app.state.learning
    return engine.web.status()


@router.post("/web/learn")
async def web_learn(body: WebLearnRequest, request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.settings.enabled or not engine.settings.web_learning_enabled:
        raise HTTPException(503, "Web learning disabled")
    crimeguard = getattr(request.app.state, "crimeguard", None)
    if crimeguard is not None and crimeguard.state.network_locked:
        raise HTTPException(403, "Network locked by CrimeGuard")
    return await engine.learn_from_web(body.query, force_refresh=body.force_refresh)


@router.post("/web/search")
async def web_search(body: WebSearchRequest, request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.settings.web_learning_enabled:
        raise HTTPException(503, "Web learning disabled")
    crimeguard = getattr(request.app.state, "crimeguard", None)
    if crimeguard is not None and crimeguard.state.network_locked:
        raise HTTPException(403, "Network locked by CrimeGuard")
    return await engine.search_web(body.query)


class ImageFeedbackRequest(BaseModel):
    user_id: str = "default"
    image_id: str = ""
    thumbs: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str = ""
    prompt: str = ""


@router.get("/image/status")
async def image_learning_status(request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.image:
        raise HTTPException(503, "Image learning not initialized")
    return engine.image.status()


@router.post("/image/learn")
async def image_learn(request: Request) -> dict:
    engine = request.app.state.learning
    return await engine.learn_perfect_images()


@router.post("/image/feedback")
async def image_feedback(body: ImageFeedbackRequest, request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.image:
        raise HTTPException(503, "Image learning not initialized")
    return engine.image.record_feedback(
        user_id=body.user_id,
        image_id=body.image_id,
        thumbs=body.thumbs,
        rating=body.rating,
        comment=body.comment,
        prompt=body.prompt,
    )


@router.get("/web/facts")
async def web_facts(request: Request, q: str = "", limit: int = 20) -> dict:
    engine = request.app.state.learning
    facts = engine.web.retrieve_local(q, limit=limit) if q else []
    if not q:
        data = engine.web._load_facts()  # noqa: SLF001
        facts = [f["fact"] for f in data.get("facts", [])[-limit:] if f.get("fact")]
    return {"facts": facts, "count": len(facts)}


@router.get("/evolution")
async def evolution_status(request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.settings.enabled:
        raise HTTPException(503, "Learning module disabled")
    return engine.evolution_snapshot()


@router.post("/feedback")
async def post_feedback(body: FeedbackRequest, request: Request) -> dict:
    engine = request.app.state.learning
    if not engine.settings.enabled:
        raise HTTPException(503, "Learning module disabled")
    if body.regenerate or body.thumbs == "down":
        return await engine.record_feedback_and_regenerate(
            user_id=body.user_id,
            session_id=body.session_id,
            thumbs=body.thumbs,
            comment=body.comment,
            message=body.message,
            last_user_message=body.last_user_message,
        )
    return engine.record_feedback(
        user_id=body.user_id,
        session_id=body.session_id,
        rating=body.rating,
        thumbs=body.thumbs,
        comment=body.comment,
        message=body.message,
    )


@router.get("/users/{user_id}/preferences")
async def get_user_preferences(user_id: str, request: Request) -> dict:
    engine = request.app.state.learning
    return engine.preferences.get(user_id)


@router.get("/characters/{character_id}/knowledge")
async def get_character_knowledge(character_id: str, request: Request) -> dict:
    engine = request.app.state.learning
    return engine.knowledge.get(character_id)