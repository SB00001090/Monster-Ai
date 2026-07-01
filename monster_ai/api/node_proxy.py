"""Reverse proxy to the Node tRPC API (background :3000)."""
from __future__ import annotations

import os
from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter(tags=["node-proxy"])

def _node_api_url() -> str:
    return os.environ.get("NODE_API_URL", "http://127.0.0.1:3000").rstrip("/")

_SKIP_REQ_HEADERS = frozenset(
    {"host", "content-length", "transfer-encoding", "connection"}
)
_SKIP_RESP_HEADERS = frozenset(
    {"content-encoding", "transfer-encoding", "connection", "content-length"}
)

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def _filter_headers(
    headers: Iterable[tuple[str, str]], skip: frozenset[str]
) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in headers:
        if key.lower() not in skip:
            out[key] = value
    return out


async def _proxy_request(request: Request, target_path: str) -> Response:
    url = f"{_node_api_url()}{target_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    body = await request.body()
    headers = _filter_headers(request.headers.items(), _SKIP_REQ_HEADERS)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            upstream = await client.request(
                request.method,
                url,
                headers=headers,
                content=body if body else None,
            )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={
                "error": "node_api_offline",
                "detail": "Start Node API on :3000 (run.bat or pnpm dev:api)",
                "node_url": _node_api_url(),
            },
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"error": "node_api_timeout", "node_url": _node_api_url()},
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_filter_headers(upstream.headers.items(), _SKIP_RESP_HEADERS),
        media_type=upstream.headers.get("content-type"),
    )


@router.api_route("/api/trpc", methods=_PROXY_METHODS)
@router.api_route("/api/trpc/{path:path}", methods=_PROXY_METHODS)
async def proxy_trpc(request: Request, path: str = "") -> Response:
    suffix = f"/{path}" if path else ""
    return await _proxy_request(request, f"/api/trpc{suffix}")


@router.api_route("/api/oauth", methods=_PROXY_METHODS)
@router.api_route("/api/oauth/{path:path}", methods=_PROXY_METHODS)
async def proxy_oauth(request: Request, path: str = "") -> Response:
    suffix = f"/{path}" if path else ""
    return await _proxy_request(request, f"/api/oauth{suffix}")


@router.api_route("/monster-storage", methods=_PROXY_METHODS)
@router.api_route("/monster-storage/{path:path}", methods=_PROXY_METHODS)
async def proxy_storage(request: Request, path: str = "") -> Response:
    suffix = f"/{path}" if path else ""
    return await _proxy_request(request, f"/monster-storage{suffix}")