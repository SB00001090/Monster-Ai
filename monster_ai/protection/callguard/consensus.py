"""Anonymous report consensus — no public comment board, multi-voter adoption."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from monster_ai.protection.callguard.report import hash_number


class ReportConsensus:
    """Whocall-style crowd signal without public messages — hash + category only."""

    def __init__(self, data_dir: Path, *, min_votes: int = 3, adopt_threshold: int = 70) -> None:
        self.path = data_dir / "consensus_queue.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.min_votes = min_votes
        self.adopt_threshold = adopt_threshold
        self._queue: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._queue, indent=2), encoding="utf-8")

    def submit(
        self,
        number: str,
        *,
        category: str,
        score: int,
        signals: list[str],
        reporter_id: str = "",
    ) -> dict[str, Any]:
        """Queue anonymous vote. No message text stored."""
        nh = hash_number(number)
        entry = self._queue.setdefault(
            nh,
            {
                "number_hash": nh,
                "votes": 0,
                "scores": [],
                "categories": [],
                "signals": [],
                "reporters": [],
                "first_seen": time.time(),
                "last_seen": time.time(),
            },
        )
        rid = reporter_id or f"anon-{int(time.time())}"
        if rid in entry["reporters"]:
            return {
                "ok": True,
                "duplicate": True,
                "number_hash": nh,
                "votes": entry["votes"],
                "adopted": False,
            }
        entry["reporters"].append(rid)
        entry["votes"] = len(entry["reporters"])
        entry["scores"].append(int(score))
        entry["categories"].append(category)
        entry["signals"] = list(dict.fromkeys(entry["signals"] + signals[:8]))[:20]
        entry["last_seen"] = time.time()
        self._save()
        adopted = self._try_adopt(nh, entry)
        return {
            "ok": True,
            "number_hash": nh,
            "votes": entry["votes"],
            "min_votes": self.min_votes,
            "adopted": adopted,
            "public_board": False,
        }

    def _try_adopt(self, nh: str, entry: dict[str, Any]) -> bool:
        if entry["votes"] < self.min_votes:
            return False
        scores = entry["scores"]
        if not scores:
            return False
        median = sorted(scores)[len(scores) // 2]
        if median < self.adopt_threshold:
            return False
        entry["adopted"] = True
        entry["adopted_at"] = time.time()
        entry["adopted_score"] = median
        self._save()
        return True

    def adopted_hashes(self) -> list[str]:
        return [k for k, v in self._queue.items() if v.get("adopted")]

    def status(self) -> dict[str, Any]:
        pending = sum(1 for v in self._queue.values() if not v.get("adopted"))
        adopted = sum(1 for v in self._queue.values() if v.get("adopted"))
        return {
            "pending": pending,
            "adopted": adopted,
            "min_votes": self.min_votes,
            "adopt_threshold": self.adopt_threshold,
            "public_comment_board": False,
        }

    def apply_to_db(self, db: dict[str, Any]) -> dict[str, Any]:
        block = list(db.get("hash_blocklist") or [])
        for nh in self.adopted_hashes():
            if nh not in block:
                block.append(nh)
        db["hash_blocklist"] = block[-5000:]
        return db