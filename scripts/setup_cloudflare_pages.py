#!/usr/bin/env python3
"""Setup & deploy Monster AI to Cloudflare Pages — Developed by Suckbob."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, env: dict | None = None) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT), env=env or os.environ.copy())


def _which(name: str) -> str | None:
    return shutil.which(name)


def dashboard_config() -> dict:
    return {
        "project_name": "monster-ai",
        "production_branch": "main",
        "build_command": "pnpm install && pnpm build",
        "build_output_directory": "dist/public",
        "root_directory": "/",
        "node_version": "20",
        "environment_variables": {
            "production": {
                "VITE_MONSTER_API_URL": "https://YOUR-TUNNEL.trycloudflare.com",
                "NODE_VERSION": "20",
            },
            "preview": {
                "VITE_MONSTER_API_URL": "https://YOUR-TUNNEL.trycloudflare.com",
            },
        },
        "github_repo": "SB00001090/Monster-Ai",
        "custom_domain_optional": "monster-ai.yourdomain.com",
        "pages_url": "https://monster-ai.pages.dev",
    }


def write_dashboard_json() -> Path:
    out = ROOT / "deploy" / "cloudflare" / "pages-dashboard.json"
    out.write_text(
        json.dumps(dashboard_config(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out}")
    return out


def build() -> int:
    return _run([sys.executable, str(ROOT / "scripts" / "deploy_cloudflare.py"), "--build"])


def wrangler(cmd: list[str]) -> int:
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    return _run([npx, "wrangler", *cmd])


def login() -> int:
    print("\n=== Cloudflare Login ===")
    print("A browser window will open. Sign in and authorize wrangler.\n")
    return wrangler(["login"])


def create_project(name: str, branch: str) -> int:
    return wrangler(["pages", "project", "create", name, "--production-branch", branch])


def deploy(name: str) -> int:
    dist = ROOT / "dist" / "public"
    if not (dist / "index.html").is_file():
        print("dist/public missing — building first…")
        if build() != 0:
            return 1
    return wrangler(["pages", "deploy", str(dist), "--project-name", name, "--branch", "main"])


def deploy_with_token(name: str, token: str, account_id: str) -> int:
    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = token
    env["CLOUDFLARE_ACCOUNT_ID"] = account_id
    dist = ROOT / "dist" / "public"
    if not (dist / "index.html").is_file():
        if build() != 0:
            return 1
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    return _run(
        [npx, "wrangler", "pages", "deploy", str(dist), "--project-name", name, "--branch", "main"],
        env=env,
    )


def print_github_secrets() -> None:
    print(
        """
GitHub Actions secrets (Settings → Secrets and variables → Actions):
  CLOUDFLARE_API_TOKEN   — API token with "Cloudflare Pages Edit"
  CLOUDFLARE_ACCOUNT_ID  — Dashboard → Account ID (right sidebar)

GitHub Actions variable (Settings → Variables):
  VITE_MONSTER_API_URL   — your Cloudflare Tunnel URL to local :7860

Create API token: https://dash.cloudflare.com/profile/api-tokens
  → Create Token → Edit Cloudflare Workers → Include Pages
"""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup Cloudflare Pages for Monster AI")
    parser.add_argument("--config", action="store_true", help="Write pages-dashboard.json")
    parser.add_argument("--build", action="store_true", help="Build frontend only")
    parser.add_argument("--login", action="store_true", help="wrangler login")
    parser.add_argument("--create", action="store_true", help="Create Pages project")
    parser.add_argument("--deploy", action="store_true", help="Deploy dist/public to Pages")
    parser.add_argument("--all", action="store_true", help="config + build + login + create + deploy")
    parser.add_argument("--project", default="monster-ai", help="Pages project name")
    parser.add_argument("--branch", default="main", help="Production branch")
    args = parser.parse_args()

    if not _which("npx"):
        print("ERROR: npx not found. Install Node.js 20+")
        return 1

    write_dashboard_json()

    if args.config and not any([args.build, args.login, args.create, args.deploy, args.all]):
        print_github_secrets()
        print(json.dumps(dashboard_config(), indent=2, ensure_ascii=False))
        return 0

    if args.build or args.all:
        if build() != 0:
            return 1

    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()

    if args.login or args.all:
        if not token:
            if login() != 0:
                return 1
        else:
            print("CLOUDFLARE_API_TOKEN set — skip interactive login")

    if args.create or args.all:
        if token and account:
            print("Using API token — create project via dashboard if first time:")
            print(f"  https://dash.cloudflare.com → Workers & Pages → Create → Pages → Connect Git")
        else:
            create_project(args.project, args.branch)

    if args.deploy or args.all:
        if token and account:
            return deploy_with_token(args.project, token, account)
        return deploy(args.project)

    if not any([args.build, args.login, args.create, args.deploy, args.all]):
        print_github_secrets()
        cfg = dashboard_config()
        print("\n=== Cloudflare Dashboard (Connect Git) ===\n")
        for k, v in cfg.items():
            if k != "environment_variables":
                print(f"  {k}: {v}")
        print("\n  Environment variables (Production):")
        for k, v in cfg["environment_variables"]["production"].items():
            print(f"    {k}={v}")
        print("\nRun: python scripts/setup_cloudflare_pages.py --login --deploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())