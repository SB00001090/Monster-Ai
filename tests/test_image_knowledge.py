"""Tests for image quality learning."""
from __future__ import annotations

import json

from monster_ai.config import ImageQualitySettings, LearningSettings
from monster_ai.modules.learning.image_knowledge import ImageKnowledgeLearner
from monster_ai.modules.learning.store import LearningStore


def _write_quality_log(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def test_learn_from_quality_store(tmp_path) -> None:
    quality_dir = tmp_path / "quality"
    log = quality_dir / "quality_log.jsonl"
    _write_quality_log(
        log,
        [
            {
                "label": "good",
                "prompt": "masterpiece, best quality, cyberpunk city",
                "checkpoint": "sd15.safetensors",
                "quality": {"score": 0.9, "issues": []},
            },
            {
                "label": "good",
                "prompt": "masterpiece, best quality, neon portrait",
                "checkpoint": "sd15.safetensors",
                "quality": {"score": 0.85, "issues": []},
            },
            {
                "label": "bad",
                "prompt": "blurry scene",
                "checkpoint": "sd15.safetensors",
                "quality": {"score": 0.2, "issues": ["noise_wall"]},
            },
        ],
    )

    store = LearningStore(tmp_path / "learning")
    settings = LearningSettings(image_learning_enabled=True)
    q_settings = ImageQualitySettings(data_dir=str(quality_dir))
    learner = ImageKnowledgeLearner(store, q_settings, settings)
    result = learner.learn_from_quality_store()

    assert result["ok"]
    assert result["good_count"] == 2
    assert "masterpiece" in result["learned_tags"]


def test_enhance_prompt_adds_missing_tags(tmp_path) -> None:
    store = LearningStore(tmp_path / "learning")
    settings = LearningSettings(image_learning_enabled=True)
    q_settings = ImageQualitySettings(data_dir=str(tmp_path / "quality"))
    learner = ImageKnowledgeLearner(store, q_settings, settings)
    patterns = learner._load_patterns()  # noqa: SLF001
    patterns["learned_quality_tags"] = ["masterpiece", "best quality"]
    learner._save_patterns(patterns)  # noqa: SLF001

    out = learner.enhance_prompt("cyberpunk cat")
    assert "masterpiece" in out.lower()
    assert "cyberpunk cat" in out


def test_record_feedback_promotes_tags(tmp_path) -> None:
    store = LearningStore(tmp_path / "learning")
    settings = LearningSettings(image_learning_enabled=True)
    q_settings = ImageQualitySettings(data_dir=str(tmp_path / "quality"))
    learner = ImageKnowledgeLearner(store, q_settings, settings)
    learner.record_feedback(
        user_id="u1",
        image_id="img1",
        thumbs="up",
        prompt="masterpiece, cinematic lighting, dragon",
    )
    patterns = learner._load_patterns()  # noqa: SLF001
    tags = [t.lower() for t in patterns.get("learned_quality_tags", [])]
    assert "cinematic lighting" in tags or "dragon" in tags