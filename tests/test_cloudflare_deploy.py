"""Tests for Cloudflare Pages + Tunnel deploy assets."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_cloudflare_deploy_files_exist() -> None:
    assert (ROOT / "deploy" / "cloudflare" / "wrangler.toml").is_file()
    assert (ROOT / "deploy" / "cloudflare" / "DEPLOY.md").is_file()
    assert (ROOT / "deploy" / "cloudflare" / "cloudflared-config.example.yml").is_file()
    assert (ROOT / "client" / "public" / "_redirects").is_file()
    assert (ROOT / "client" / "public" / "_routes.json").is_file()
    assert (ROOT / "scripts" / "deploy_cloudflare.py").is_file()
    assert (ROOT / ".github" / "workflows" / "cloudflare-pages.yml").is_file()


def test_monster_api_client_exists() -> None:
    assert (ROOT / "client" / "src" / "lib" / "monsterApi.ts").is_file()
    assert (ROOT / "client" / "src" / "pages" / "EcosystemPage.tsx").is_file()
    assert (ROOT / "client" / "src" / "pages" / "MiniStudioPage.tsx").is_file()
    assert (ROOT / "client" / "src" / "pages" / "DeployPage.tsx").is_file()


def test_web_cors_settings() -> None:
    from monster_ai.config import WebSettings

    w = WebSettings()
    assert w.cors_enabled
    assert "http://127.0.0.1:7860" in w.cors_origins


def test_setup_pages_script_config() -> None:
    assert (ROOT / "scripts" / "setup_cloudflare_pages.py").is_file()
    cfg = json.loads((ROOT / "deploy" / "cloudflare" / "pages-dashboard.json").read_text(encoding="utf-8"))
    assert cfg["build_output_directory"] == "dist/public"
    assert cfg["project_name"] == "monster-ai"


def test_deploy_script_checklist() -> None:
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "deploy_cloudflare.py"), "--checklist"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert r.returncode == 0
    assert "Suckbob" in r.stdout
    assert "dist/public" in r.stdout