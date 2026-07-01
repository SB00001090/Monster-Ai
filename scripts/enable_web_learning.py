"""Enable and verify Monster AI network knowledge learning."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from monster_ai.config import LearningSettings, load_settings
from monster_ai.modules.learning.store import LearningStore
from monster_ai.modules.learning.web_knowledge import WebKnowledgeLearner

SEED_TOPICS = [
    "人工智慧",
    "機器學習",
    "大型語言模型",
    "Python 程式語言",
    "量子計算",
    "區塊鏈",
    "cybersecurity",
    "climate change",
]


async def main() -> int:
    parser = argparse.ArgumentParser(description="Enable web knowledge learning")
    parser.add_argument("--test-query", default="什麼是人工智慧")
    parser.add_argument("--seed", action="store_true", help="Batch learn seed topics")
    parser.add_argument("--limit", type=int, default=4, help="Max seed topics")
    args = parser.parse_args()

    settings = load_settings()
    ls = settings.learning
    store = LearningStore(ls.data_dir)
    learner = WebKnowledgeLearner(store, ls)

    print("Web learning:", ls.web_learning_enabled)
    print("Auto search:", ls.web_auto_search)
    print("Langs:", ls.web_search_langs)

    search = await learner.search(args.test_query)
    if not search.get("ok"):
        print(f"Search failed: {search.get('reason')}")
        print("Check network connection and CrimeGuard network lock.")
        return 1
    print(f"Search OK: {len(search.get('results', []))} results for '{args.test_query}'")

    learned = await learner.learn(args.test_query)
    print(f"Learned: {learned.get('facts_added', 0)} facts, total={learned.get('fact_count', 0)}")

    if args.seed:
        for topic in SEED_TOPICS[: args.limit]:
            r = await learner.learn(topic)
            print(f"  seed {topic}: +{r.get('facts_added', 0)} facts")

    print("\nDone. Restart main.py — /chat and /learn will use network knowledge.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))