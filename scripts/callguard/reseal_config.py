#!/usr/bin/env python3
"""Re-seal config.yaml after legitimate MonsterLock / Call Guard changes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from monster_ai.protection.monsterlock.config_guard import create_config_seal

    create_config_seal(ROOT / "config.yaml", ROOT / "data" / "monsterlock")
    print("OK: config.seal updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())