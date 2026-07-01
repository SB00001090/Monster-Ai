"""Analyze image quality archives and enable perfect-image learning."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from monster_ai.config import load_settings
from monster_ai.modules.learning.image_knowledge import ImageKnowledgeLearner
from monster_ai.modules.learning.store import LearningStore


def main() -> int:
    settings = load_settings()
    store = LearningStore(settings.learning.data_dir)
    learner = ImageKnowledgeLearner(
        store,
        settings.modules.image.quality,
        settings.learning,
    )
    result = learner.learn_from_quality_store()
    status = learner.status()

    print("Image learning enabled:", settings.learning.image_learning_enabled)
    print("Quality archive:", settings.modules.image.quality.data_dir)
    print("Learn result:", result)
    print("Suggested params:", status.get("suggested_params"))
    print("Training samples:", status.get("training_samples"))
    if status.get("training_ready"):
        print("\nNext: python scripts/train_image_quality_4060.py --low-vram")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())