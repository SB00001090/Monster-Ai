#!/usr/bin/env python3
"""One-click Mini Monster AI v1.0 setup — Developed by Suckbob."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MINI_BLOCK = """
  mini:
    enabled: true
    data_dir: ./data/mini
    output_dir: ./data/outputs/mini
    default_template: hq
    default_locale: zh-TW
    checkpoint: auto
    lite_mode: true
    uncensored: true
    auto_optimize_prompt: true
    max_quality_retries: 4
    share_with_monster_ai: true
    network_learning_enabled: false
    network_allow_downloads: false
    network_allow_metrics_upload: false
    gguf_model_hint: qwen2.5:7b
    vram_profile: mini
    likeness_enabled: true
    likeness_target_similarity: 0.98
    likeness_ipadapter_weight: 0.85
    require_user_reference: true
    voice_clone_enabled: true
    multimodal_sync_enabled: true
    comfy_input_dir: ./data/comfyui/input
"""


def _patch_config(config_path: Path) -> None:
    text = config_path.read_text(encoding="utf-8")
    if "mini:" in text and "modules:" in text:
        print("config.yaml already has mini section — skip patch")
        return
    marker = "  prompt:"
    if marker not in text:
        raise RuntimeError("Could not find modules.prompt in config.yaml")
    text = text.replace(marker, MINI_BLOCK + marker, 1)
    config_path.write_text(text, encoding="utf-8")
    print("Patched config.yaml with modules.mini")


def _ensure_dirs() -> None:
    for sub in (
        "data/mini",
        "data/mini/references",
        "data/mini/network_cache",
        "data/comfyui/input",
        "data/outputs/mini",
        "data/voices",
        "data/quality/good",
        "data/quality/bad",
        "data/learning/image",
    ):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    print("Data directories ready")


def _write_manifest() -> None:
    manifest = {
        "product": "Mini Monster AI",
        "version": "1.0.0",
        "developer": "Suckbob",
        "target_success_rate": 0.98,
        "target_deadline": "2026-09-01",
        "ui_path": "/mini/index.html",
        "api_prefix": "/api/mini",
    }
    path = ROOT / "data" / "mini" / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {path}")


def main() -> int:
    print("=" * 60)
    print("Mini Monster AI v1.0 Installer — Developed by Suckbob")
    print("=" * 60)
    config = ROOT / "config.yaml"
    if not config.is_file():
        example = ROOT / "config.example.yaml"
        if example.is_file():
            config.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print("Created config.yaml from config.example.yaml")
        else:
            print("ERROR: config.yaml missing")
            return 1

    _ensure_dirs()
    _patch_config(config)
    _write_manifest()

    print("\nNext steps:")
    print("  1. Put SDXL checkpoint in ComfyUI/models/checkpoints/")
    print("     (Juggernaut XL, RealVisXL, Pony, etc.)")
    print("  2. python main.py  OR  apps/mini_monster_ai/run-mini.bat")
    print("  3. Open http://127.0.0.1:7860/mini  (or /mini/index.html)")
    print("  4. Optional network learning:")
    print("     POST /api/mini/network/consent  {grant:true, metrics:true}")
    return 0


if __name__ == "__main__":
    sys.exit(main())