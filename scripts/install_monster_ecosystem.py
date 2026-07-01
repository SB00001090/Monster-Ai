#!/usr/bin/env python3
"""CLI: one-click Monster AI ecosystem network install — Developed by Suckbob."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ECOSYSTEM_BLOCK = """
ecosystem:
  enabled: true
  data_dir: ./data/ecosystem
  network_install_enabled: true
  require_consent: true
  default_bundle: full
  allow_r18_bundle: true
  allow_model_downloads: true
"""


def _patch_config(config_path: Path) -> None:
    text = config_path.read_text(encoding="utf-8")
    if "ecosystem:" in text:
        print("config.yaml already has ecosystem section — skip patch")
        return
    marker = "learning:"
    if marker not in text:
        raise RuntimeError("Could not find learning: in config.yaml")
    text = text.replace(marker, ECOSYSTEM_BLOCK + marker, 1)
    config_path.write_text(text, encoding="utf-8")
    print("Patched config.yaml with ecosystem settings")


def _ensure_dirs() -> None:
    for sub in ("data/ecosystem", "data/models", "data/ecosystem/r18_catalog"):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)


async def _run(bundle: str, *, grant: bool, allow_r18: bool, dry_run: bool) -> int:
    from monster_ai.config import EcosystemSettings, Settings
    from monster_ai.modules.ecosystem.installer import EcosystemInstaller
    from monster_ai.modules.ecosystem.manifest import bundle_steps, list_bundles

    settings = Settings()
    eco = settings.ecosystem
    if not eco.enabled:
        eco = EcosystemSettings(enabled=True)

    inst = EcosystemInstaller(eco, root=ROOT)
    bundles = list_bundles()
    print(f"Monster AI Ecosystem — Developed by Suckbob")
    print(f"Available bundles: {[b['id'] for b in bundles]}")

    steps = bundle_steps(bundle)
    if not steps:
        print(f"Unknown bundle: {bundle}")
        return 1

    print(f"Bundle '{bundle}' — {len(steps)} steps")
    if dry_run:
        print(json.dumps({"bundle": bundle, "steps": steps}, indent=2, ensure_ascii=False))
        return 0

    if grant:
        inst.grant_consent(allow_r18=allow_r18, allow_downloads=True)
        print("Consent granted")

    result = await inst.start(bundle)
    if not result.get("ok"):
        print(f"Start failed: {result.get('reason', 'unknown')}")
        return 1

    print(f"Install started — polling status…")
    while True:
        st = inst.status()
        pct = st.get("progress_pct", 0)
        step = st.get("current_step") or "done"
        print(f"  [{pct:5.1f}%] {step}")
        if not st.get("running"):
            break
        await asyncio.sleep(3)

    st = inst.status()
    print(json.dumps(st, indent=2, ensure_ascii=False))
    return 0 if not st.get("errors") else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Monster AI ecosystem one-click installer")
    parser.add_argument(
        "--bundle",
        default="full",
        choices=["full", "mini", "r18_multimodal", "roleplay", "image_video", "audio"],
        help="Install bundle id",
    )
    parser.add_argument("--grant-consent", action="store_true", help="Auto-grant network consent")
    parser.add_argument("--no-r18", action="store_true", help="Disable R18 in consent")
    parser.add_argument("--dry-run", action="store_true", help="List steps only, no install")
    parser.add_argument("--patch-config", action="store_true", help="Add ecosystem block to config.yaml")
    args = parser.parse_args()

    _ensure_dirs()
    config_path = ROOT / "config.yaml"
    if args.patch_config and config_path.is_file():
        _patch_config(config_path)

    return asyncio.run(
        _run(
            args.bundle,
            grant=args.grant_consent,
            allow_r18=not args.no_r18,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())