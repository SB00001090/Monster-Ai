#!/usr/bin/env python3
"""Quick Supabase + integrations smoke test."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fastapi.testclient import TestClient

from monster_ai.app import create_app
from monster_ai.config import load_settings


def _mask(value: str | None) -> str:
    if not value:
        return "(missing)"
    v = value.strip()
    if len(v) <= 8:
        return "***"
    return f"{v[:6]}...{v[-4:]}"


def main() -> int:
    url = os.environ.get("VITE_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("VITE_SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY")
    )

    print("=== Supabase env ===")
    print(f"VITE_SUPABASE_URL: {_mask(url)}")
    print(f"VITE_SUPABASE_ANON_KEY: {_mask(key)}")
    print(f"configured: {bool(url and key)}")

    settings = load_settings()
    settings.protection.monsterlock.enabled = False
    settings.protection.monsterlock.self_destruct_enabled = False
    client = TestClient(create_app(settings))
    r = client.get("/api/integrations/status")
    data = r.json()
    print("\n=== GET /api/integrations/status (local code) ===")
    print(json.dumps(
        {
            "status": r.status_code,
            "supabase_configured": data.get("supabase_configured"),
            "sentry_configured": data.get("sentry_configured"),
        },
        indent=2,
    ))

    if not url or not key:
        print("\nResult: SKIP live ping — add VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY to .env")
        return 0

    import urllib.error
    import urllib.request

    endpoint = f"{url.strip().rstrip('/')}/rest/v1/guardian_profiles?select=id&limit=1"
    req = urllib.request.Request(
        endpoint,
        headers={
            "apikey": key.strip(),
            "Authorization": f"Bearer {key.strip()}",
        },
    )
    print("\n=== Live Supabase ping ===")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {resp.status}")
            print(f"body: {body[:200]}")
            print("Result: OK")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}")
        print(f"body: {body[:300]}")
        if exc.code == 404 and "does not exist" in body:
            print("Result: FAIL — run migration (GitHub Integration or SQL Editor)")
        else:
            print("Result: FAIL — check URL/key and RLS/schema")
        return 1
    except Exception as exc:
        print(f"Result: FAIL — {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())