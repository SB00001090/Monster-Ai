#!/usr/bin/env python3
"""Monster AI — Cloudflare Pages build + Tunnel helper. Developed by Suckbob."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)

ROOT = Path(__file__).resolve().parent.parent


def _which(name: str) -> str | None:
    return shutil.which(name)


def _find_cloudflared() -> str | None:
    name = "cloudflared.cmd" if sys.platform == "win32" else "cloudflared"
    found = _which(name)
    if found:
        return found
    if sys.platform != "win32":
        return None
    winget = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for pkg in sorted(winget.glob("Cloudflare.cloudflared*"), reverse=True):
        exe = pkg / "cloudflared.exe"
        if exe.is_file():
            return str(exe)
    return None


def build_frontend() -> int:
    pnpm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
    if not _which(pnpm):
        print("ERROR: pnpm not found. Install Node.js 20+ and: npm install -g pnpm")
        return 1
    print("Building React UI → dist/public …")
    r = subprocess.run([pnpm, "build"], cwd=str(ROOT), shell=False)
    if r.returncode != 0:
        return r.returncode
    out = ROOT / "dist" / "public"
    print(f"OK: {out}")
    return 0


def _save_tunnel_url(url: str) -> Path:
    out = ROOT / "data" / "callguard" / "tunnel_url.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(url.strip().rstrip("/") + "\n", encoding="utf-8")
    return out


def start_quick_tunnel() -> int:
    cf = _find_cloudflared()
    if not cf:
        print("ERROR: cloudflared not found.")
        print("Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
        print("Or: winget install Cloudflare.cloudflared")
        print("Or double-click: run-tunnel.bat")
        return 1
    print("Starting quick tunnel → http://127.0.0.1:7860")
    print("Ensure python main.py is running locally.")
    print("Tunnel URL auto-saves to data/callguard/tunnel_url.txt")
    print("Also paste into Call Guard App → Cloudflare Tunnel")
    proc = subprocess.Popen(
        [cf, "tunnel", "--url", "http://127.0.0.1:7860"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        match = TUNNEL_URL_RE.search(line)
        if match:
            saved = _save_tunnel_url(match.group(0))
            print(f"Saved tunnel URL → {saved}")
    return proc.wait()


def print_checklist() -> None:
    checklist = {
        "developer": "Suckbob",
        "steps": [
            "pnpm build (or python scripts/deploy_cloudflare.py --build)",
            "Connect GitHub repo to Cloudflare Pages",
            "Build command: pnpm build | Output: dist/public",
            "Set VITE_MONSTER_API_URL to tunnel URL",
            "Run python main.py locally",
            "Add pages.dev origin to config.yaml web.cors_origins",
            "Open /ecosystem for one-click module install",
        ],
        "docs": "deploy/cloudflare/DEPLOY.md",
    }
    print(json.dumps(checklist, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Monster AI Cloudflare deploy helper")
    parser.add_argument("--build", action="store_true", help="Build frontend for Pages")
    parser.add_argument("--tunnel", action="store_true", help="Start cloudflared quick tunnel")
    parser.add_argument("--checklist", action="store_true", help="Print deploy checklist JSON")
    args = parser.parse_args()

    if args.build:
        return build_frontend()
    if args.tunnel:
        return start_quick_tunnel()
    if args.checklist:
        print_checklist()
        return 0
    print_checklist()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())