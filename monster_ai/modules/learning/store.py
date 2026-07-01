"""File-backed learning data store (Phase C)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class LearningStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.root = Path(data_dir)
        self.users_dir = self.root / "users"
        self.characters_dir = self.root / "characters"
        self.knowledge_dir = self.root / "knowledge"
        self.feedback_log = self.root / "feedback.jsonl"
        self.failures_log = self.root / "failures.jsonl"
        self.web_dir = self.root / "web"
        self.web_facts = self.web_dir / "facts.json"
        self.web_learned_log = self.web_dir / "learned.jsonl"
        for d in (self.users_dir, self.characters_dir, self.knowledge_dir, self.web_dir):
            d.mkdir(parents=True, exist_ok=True)

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        record.setdefault("ts", time.time())
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_json(self, path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.is_file():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def user_path(self, user_id: str) -> Path:
        safe = user_id.replace("/", "_").replace("\\", "_")
        return self.users_dir / f"{safe}.json"

    def character_path(self, character_id: str) -> Path:
        safe = character_id.replace("/", "_").replace("\\", "_")
        return self.characters_dir / f"{safe}.json"

    def knowledge_path(self, character_id: str) -> Path:
        safe = character_id.replace("/", "_").replace("\\", "_")
        return self.knowledge_dir / f"{safe}.json"