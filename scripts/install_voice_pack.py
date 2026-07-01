"""Download Piper TTS voice packs for Monster AI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# voice_id -> relative path under rhasspy/piper-voices (without .onnx suffix)
PIPER_VOICES: dict[str, dict[str, str]] = {
    "en_US-lessac-medium": {
        "path": "en/en_US/lessac/medium/en_US-lessac-medium",
        "label": "English (US) · Lessac",
    },
    "zh_CN-huayan-medium": {
        "path": "zh/zh_CN/huayan/medium/zh_CN-huayan-medium",
        "label": "中文（華妍 · 普通話）",
    },
}

LANG_DEFAULT_VOICE = {
    "en": "en_US-lessac-medium",
    "zh": "zh_CN-huayan-medium",
    "zh-CN": "zh_CN-huayan-medium",
    "zh-TW": "zh_CN-huayan-medium",
}


def install_piper_voice(voice_id: str, dest: Path) -> bool:
    meta = PIPER_VOICES.get(voice_id)
    if not meta:
        known = ", ".join(sorted(PIPER_VOICES))
        print(f"Unknown voice '{voice_id}'. Available: {known}")
        return False

    dest.mkdir(parents=True, exist_ok=True)
    onnx = dest / f"{voice_id}.onnx"
    json_path = dest / f"{voice_id}.onnx.json"
    if onnx.exists() and json_path.exists():
        print(f"Already installed: {onnx}")
        return True

    try:
        import httpx
    except ImportError:
        print("httpx not installed. Run: pip install httpx")
        return False

    base = f"{HF_BASE}/{meta['path']}"
    ok = True
    for suffix, target in ((".onnx", onnx), (".onnx.json", json_path)):
        if target.exists():
            print(f"Skip existing {target.name}")
            continue
        url = base + suffix
        print(f"Downloading {url} …")
        try:
            r = httpx.get(url, follow_redirects=True, timeout=300)
            if r.status_code != 200:
                print(f"Failed ({r.status_code}): {url}")
                ok = False
                continue
            target.write_bytes(r.content)
            print(f"Saved {target} ({len(r.content) // 1024} KB)")
        except Exception as exc:
            print(f"Download error: {exc}")
            ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Piper voice packs")
    parser.add_argument(
        "--voice",
        action="append",
        dest="voices",
        help="Voice id (repeatable). Default: zh_CN-huayan-medium",
    )
    parser.add_argument(
        "--lang",
        choices=sorted(LANG_DEFAULT_VOICE),
        help="Shortcut: en, zh, zh-CN, zh-TW",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available voices and exit",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=ROOT / "data" / "models" / "piper",
        help="Output directory for .onnx models",
    )
    args = parser.parse_args()

    if args.list:
        for vid, meta in PIPER_VOICES.items():
            print(f"  {vid:24}  {meta['label']}")
        return 0

    voices: list[str] = []
    if args.lang:
        voices.append(LANG_DEFAULT_VOICE[args.lang])
    if args.voices:
        voices.extend(args.voices)
    if not voices:
        voices = ["zh_CN-huayan-medium"]

    ok = True
    for voice in voices:
        print(f"\n=== {voice} ===")
        if not install_piper_voice(voice, args.dest):
            ok = False

    if ok:
        primary = voices[-1]
        print(f"\nDone. Set config.yaml → modules.tts.piper_voice: \"{primary}\"")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())