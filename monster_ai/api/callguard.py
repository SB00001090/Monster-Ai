"""MonsterCallGuard REST API for mobile app integration."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/callguard", tags=["callguard"])


@router.get("/status")
async def callguard_status(request: Request) -> dict:
    cg = getattr(request.app.state, "callguard", None)
    if not cg:
        return {"enabled": False, "reachable": True, "monster_ai": "ok"}
    out = cg.to_dict()
    out["reachable"] = True
    return out


@router.post("/analyze")
async def analyze_call(request: Request, body: dict) -> dict:
    cg = request.app.state.callguard
    if not cg.state.enabled:
        raise HTTPException(503, "CallGuard disabled")
    number = str(body.get("number", ""))
    display = str(body.get("display_name", ""))
    deep = bool(body.get("deep", False))
    result = await cg.analyze_call(number, display_name=display, deep=deep)
    out = result.to_dict()
    if result.reject and cg.settings.report_enabled:
        out["report"] = cg.submit_report(number, result)
    return out


@router.get("/threat-db")
async def threat_db(request: Request) -> dict:
    cg = request.app.state.callguard
    data = cg.get_threat_db()
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=data,
        headers={"X-Threat-DB-Version": str(data.get("version", "unknown"))},
    )


@router.get("/app-manifest")
async def app_manifest(request: Request) -> dict:
    cg = request.app.state.callguard
    settings = request.app.state.settings
    apk_url = getattr(settings.protection.callguard, "apk_download_url", "")
    return cg.app_manifest(apk_url=apk_url or "")


@router.post("/token")
async def client_token(request: Request) -> dict:
    cg = request.app.state.callguard
    token, expires = cg.issue_client_token()
    return {"token": token, "expires_at": expires}


@router.get("/reports")
async def list_reports(request: Request, limit: int = 20) -> dict:
    cg = getattr(request.app.state, "callguard", None)
    if not cg:
        return {"reports": []}
    return {"reports": cg.recent_reports(limit)}


@router.post("/antitheft/location")
async def antitheft_location(request: Request, body: dict) -> dict:
    """Receive encrypted location sync from Monster Call Guard app."""
    cg = getattr(request.app.state, "callguard", None)
    if not cg:
        return {"ok": False, "error": "disabled"}
    cg._record("info", "antitheft_location", lat=body.get("lat"), lng=body.get("lng"))  # noqa: SLF001
    return {"ok": True}


@router.post("/antitheft/event")
async def antitheft_event(request: Request, body: dict) -> dict:
    cg = getattr(request.app.state, "callguard", None)
    if not cg:
        return {"ok": False}
    cg._record("alert", f"antitheft:{body.get('event')}", **body)  # noqa: SLF001
    return {"ok": True}


@router.post("/report")
async def submit_report(request: Request, body: dict) -> dict:
    cg = request.app.state.callguard
    from monster_ai.protection.callguard.rules import CallScoreResult

    result = CallScoreResult(
        score=int(body.get("score", 0)),
        category=str(body.get("category", "scam_suspicious")),
        signals=list(body.get("signals", [])),
    )
    number = str(body.get("number", "unknown"))
    device_contact = body.get("device_contact")
    reporter_id = str(body.get("reporter_id", body.get("device_hash", "")))
    report = cg.submit_report(
        number,
        result,
        device_contact=device_contact if isinstance(device_contact, dict) else None,
        reporter_id=reporter_id,
    )
    return {"ok": True, "report": report, "public_board": False}


@router.get("/consensus")
async def consensus_status(request: Request) -> dict:
    cg = getattr(request.app.state, "callguard", None)
    if not cg:
        return {"public_comment_board": False, "enabled": False}
    return cg._consensus.status()  # noqa: SLF001


def _resolve_tunnel_url(request: Request) -> str:
    import os
    from pathlib import Path

    settings = request.app.state.settings
    cg_cfg = settings.protection.callguard
    env = os.environ.get(cg_cfg.tunnel_url_env, "").strip()
    if env:
        return env.rstrip("/")
    path = Path(cg_cfg.tunnel_url_file)
    if not path.is_absolute():
        root = Path(__file__).resolve().parents[2]
        path = root / path
    if path.is_file():
        return path.read_text(encoding="utf-8-sig").strip().rstrip("/")
    return ""


@router.get("/connection")
async def connection_hint(request: Request) -> dict:
    """Cloudflare Tunnel only — Android app uses public HTTPS URL (no IP)."""
    tunnel = _resolve_tunnel_url(request)
    pages = "https://monster-ai.pages.dev"
    return {
        "modes": ["usb_local", "cloudflare_tunnel"],
        "mode": "cloudflare_tunnel",
        "usb_local_url": "http://127.0.0.1:7860",
        "usb_setup": [
            "Enable USB debugging on phone",
            "Run install-apk-adb.bat on PC",
            "adb reverse tcp:7860 tcp:7860 (auto)",
            "App auto-uses USB when adb reverse active",
        ],
        "tunnel_url": tunnel or None,
        "pages_ui": pages,
        "api_health": f"{tunnel}/health" if tunnel else None,
        "trust_score_enabled": True,
        "setup": [
            "python main.py",
            "install-apk-adb.bat (USB) OR run-tunnel.bat (remote)",
            "Paste https://*.trycloudflare.com for remote mode",
        ],
        "no_public_comment_board": True,
        "no_tailscale": True,
        "no_qr_code": True,
        "developer": "Suckbob | Monster AI Call Guard",
    }