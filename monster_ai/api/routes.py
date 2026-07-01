"""HTTP API routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter()

_LEGACY_STATIC = Path(__file__).resolve().parents[1] / "web" / "static"
_MINI_STATIC = _LEGACY_STATIC / "mini"
_ECOSYSTEM_STATIC = _LEGACY_STATIC / "ecosystem"


@router.get("/ecosystem")
async def ecosystem_ui_redirect() -> RedirectResponse:
    """Ecosystem one-click installer UI — bypass React SPA 404."""
    return RedirectResponse(url="/ecosystem/index.html", status_code=302)


@router.get("/ecosystem/index.html")
async def ecosystem_ui_html() -> FileResponse:
    return FileResponse(
        _ECOSYSTEM_STATIC / "index.html",
        media_type="text/html; charset=utf-8",
    )


@router.get("/mini")
async def mini_ui_redirect() -> RedirectResponse:
    """Mini Monster AI UI — bypass React SPA 404."""
    return RedirectResponse(url="/mini/index.html", status_code=302)


@router.get("/mini/index.html")
async def mini_ui_html() -> FileResponse:
    return FileResponse(
        _MINI_STATIC / "index.html",
        media_type="text/html; charset=utf-8",
    )


@router.get("/monsterai-security.html")
async def monsterai_security_html() -> FileResponse:
    """Security Center fallback UI (served even when dist/public is the static root)."""
    return FileResponse(
        _LEGACY_STATIC / "monsterai-security.html",
        media_type="text/html; charset=utf-8",
    )


@router.get("/health")
async def health(request: Request) -> dict:
    repair = request.app.state.repair
    return {
        "status": "ok",
        "version": request.app.state.version,
        "llm_backend": repair.state.active_backend,
        "primary_ok": repair.state.primary_ok,
    }


@router.get("/status")
async def status(request: Request) -> dict:
    repair = request.app.state.repair
    gen_repair = request.app.state.gen_repair
    image_repair = request.app.state.image_repair
    firewall = request.app.state.firewall
    watchdog = request.app.state.watchdog
    monsterlock = request.app.state.monsterlock
    crimeguard = getattr(request.app.state, "crimeguard", None)
    callguard = getattr(request.app.state, "callguard", None)
    probe = getattr(request.app.state, "hardware_probe", None)
    vram = request.app.state.vram_guard
    registry = request.app.state.modules
    self_heal = getattr(request.app.state, "self_heal", None)
    learning = getattr(request.app.state, "learning", None)
    return {
        "hardware": probe.to_dict() if probe else {},
        "repair": {
            "active_backend": repair.state.active_backend,
            "primary_ok": repair.state.primary_ok,
            "last_error": repair.state.last_error,
            "repair_count": repair.state.repair_count,
            "hardware_tier": repair.state.hardware_tier,
        },
        "generation": {
            "last_job": gen_repair.state.last_job,
            "last_error": gen_repair.state.last_error,
            "repair_count": gen_repair.state.repair_count,
            "quality_fail_streak": gen_repair.state.quality_fail_streak,
            "last_quality_score": gen_repair.state.last_quality_score,
            "vram_busy": vram.busy,
            "vram_job": vram.current_job,
        },
        "image_repair": image_repair.to_dict(),
        "firewall": firewall.to_dict(),
        "watchdog": watchdog.to_dict(),
        "self_heal": self_heal.to_dict() if self_heal else {"enabled": False},
        "learning": await learning.health() if learning else {"enabled": False},
        "monsterlock": monsterlock.to_dict(),
        "crimeguard": crimeguard.to_dict() if crimeguard else {"enabled": False},
        "callguard": callguard.to_dict() if callguard else {"enabled": False},
        "persona_mode": request.app.state.settings.persona.default_mode,
        "modules": await registry.health_report(),
    }


@router.get("/config")
async def config_summary(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "host": settings.host,
        "port": settings.port,
        "llm": {
            "model": settings.llm.model,
            "ollama_url": settings.llm.ollama_url,
            "num_ctx": settings.llm.num_ctx,
        },
        "persona": {
            "enabled": settings.persona.enabled,
            "default_mode": settings.persona.default_mode,
            "allow_user_override": settings.persona.allow_user_override,
        },
        "modules": {
            "chat": settings.modules.chat.enabled,
            "roleplay": settings.modules.roleplay.enabled,
            "image": settings.modules.image.enabled,
            "video": settings.modules.video.enabled,
            "discord": settings.modules.discord.enabled,
            "tts": settings.modules.tts.enabled,
            "training": settings.modules.training.enabled,
            "prompt": settings.modules.prompt.enabled,
        },
    }