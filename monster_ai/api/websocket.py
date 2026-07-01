"""WebSocket chat endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    client = websocket.client.host if websocket.client else "unknown"
    firewall = websocket.app.state.firewall
    allowed, reason = await firewall.check_request(ip=client, path="/ws/chat")
    if not allowed:
        await websocket.close(code=1008, reason=reason)
        return
    await websocket.accept()
    limiter = websocket.app.state.rate_limiter

    try:
        while True:
            data = await websocket.receive_json()
            if not limiter.allow(client):
                await websocket.send_json({
                    "role": "system",
                    "content": "Rate limit exceeded. Please slow down.",
                    "backend": "protection",
                })
                continue

            user_msg = data.get("message", "")
            session_id = data.get("session_id")
            character_id = data.get("character_id")
            user_id = data.get("user_id") or "default"
            web_search = data.get("web_search")

            crimeguard = getattr(websocket.app.state, "crimeguard", None)
            if crimeguard is not None and user_msg:
                allowed, reason, _ = await crimeguard.check_message_allowed(user_msg)
                if not allowed:
                    await websocket.send_json({
                        "role": "system",
                        "content": reason,
                        "backend": "crimeguard",
                    })
                    continue

            if session_id and websocket.app.state.settings.modules.roleplay.enabled:
                roleplay = websocket.app.state.roleplay
                result = await roleplay.send_message(
                    session_id,
                    user_msg,
                    character_id=character_id,
                    user_id=user_id,
                    web_search=web_search,
                )
            else:
                system = data.get("system")
                persona_mode = data.get("persona_mode")
                chat = websocket.app.state.chat
                result = await chat.send(
                    user_msg,
                    system=system,
                    persona_mode=persona_mode,
                    user_id=user_id,
                    session_id=session_id or "chat",
                )
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass