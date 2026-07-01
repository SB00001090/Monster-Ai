#!/usr/bin/env python3
"""Scan outputs, classify good/bad, encrypt to vault, analyze learning patterns."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _hardware_fingerprint() -> str:
    binding = ROOT / "data" / "monsterlock" / "hardware.binding"
    if binding.is_file():
        try:
            data = json.loads(binding.read_text(encoding="utf-8"))
            fp = data.get("fingerprint", "")
            if fp:
                return str(fp)
        except (OSError, json.JSONDecodeError):
            pass
    return "guardian-local-fallback"


def scan_and_archive(root: Path) -> dict:
    from monster_ai.config import load_settings
    from monster_ai.modules.guardian.key_manager import TrainingKeyManager
    from monster_ai.modules.guardian.training_vault import TrainingVault
    from monster_ai.modules.image.quality import ImageQualityScorer
    from monster_ai.modules.image.quality_store import QualityStore
    from monster_ai.modules.prompt.anti_collapse import build_negative

    settings = load_settings()
    hw = _hardware_fingerprint()
    km = TrainingKeyManager(settings.guardian, root, hardware_fingerprint=hw)
    km.unlock(None)
    vault = TrainingVault(Path(settings.guardian.data_dir), km)
    q_cfg = settings.modules.image.quality
    store = QualityStore(
        q_cfg.data_dir,
        q_cfg,
        training_vault=vault,
        encrypt_training=True,
    )
    scorer = ImageQualityScorer(q_cfg)

    existing_sources = set()
    for entry in vault.list_assets():
        meta = vault.read_asset_metadata(str(entry.get("id", "")))
        if meta and meta.get("source"):
            existing_sources.add(str(Path(meta["source"]).resolve()))

    sources: list[Path] = []
    img_out = root / "data" / "outputs" / "images"
    if img_out.is_dir():
        sources.extend(sorted(img_out.glob("*.png")))

    comfy_candidates = [
        root / "comfyui" / "output",
        Path(r"C:\MonsterAI\comfyui\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\output"),
    ]
    for comfy_out in comfy_candidates:
        if comfy_out.is_dir():
            sources.extend(sorted(comfy_out.glob("*.png")))
            sources.extend(sorted(comfy_out.glob("*.jpg")))
            break

    good_n = bad_n = skipped = 0
    results: list[dict] = []
    negative = build_negative()
    checkpoint = settings.modules.image.checkpoint

    for src in sources:
        src_key = str(src.resolve())
        if src_key in existing_sources:
            skipped += 1
            continue
        prompt = "highly detailed, photorealistic, masterpiece, best quality, sharp focus"
        report = scorer.evaluate(src, prompt)
        extra = {"source": src_key, "imported": True, "origin": "guardian_train_analyze"}
        if report.passed:
            store.save_good(
                src,
                prompt=prompt,
                negative=negative,
                report=report,
                checkpoint=checkpoint,
                attempt=0,
                extra=extra,
            )
            good_n += 1
            label = "good"
        else:
            store.save_bad(
                src,
                prompt=prompt,
                negative=negative,
                report=report,
                checkpoint=checkpoint,
                attempt=0,
                extra=extra,
            )
            bad_n += 1
            label = "bad"
        results.append(
            {
                "file": src.name,
                "label": label,
                "score": round(report.score, 4),
                "passed": report.passed,
                "issues": report.issues,
                "reasons": report.reasons,
            }
        )
        existing_sources.add(src_key)

    return {
        "good": good_n,
        "bad": bad_n,
        "skipped": skipped,
        "scored": results,
        "vault": vault.status(),
        "hardware_fp_prefix": hw[:16],
    }


def analyze_learning(root: Path) -> dict:
    from monster_ai.config import load_settings
    from monster_ai.modules.guardian.key_manager import TrainingKeyManager
    from monster_ai.modules.guardian.training_vault import TrainingVault
    from monster_ai.modules.image.quality_store import QualityStore
    from monster_ai.modules.learning.image_knowledge import ImageKnowledgeLearner
    from monster_ai.modules.learning.store import LearningStore

    settings = load_settings()
    hw = _hardware_fingerprint()
    km = TrainingKeyManager(settings.guardian, root, hardware_fingerprint=hw)
    km.unlock(None)
    vault = TrainingVault(Path(settings.guardian.data_dir), km)
    q_cfg = settings.modules.image.quality
    store = QualityStore(
        q_cfg.data_dir,
        q_cfg,
        training_vault=vault,
        encrypt_training=True,
    )
    learning_store = LearningStore(settings.learning.data_dir)
    learner = ImageKnowledgeLearner(
        learning_store,
        q_cfg,
        settings.learning,
        quality_store=store,
    )
    learn = learner.learn_from_quality_store()
    status = learner.status()
    records = store.read_log_records()
    good_recs = [r for r in records if r.get("label") == "good"]
    bad_recs = [r for r in records if r.get("label") == "bad"]
    return {
        "learn": learn,
        "status": status,
        "summary": {
            "total_encrypted": len(records),
            "good": len(good_recs),
            "bad": len(bad_recs),
            "training_ready": learn.get("training_ready", False),
            "training_samples": learn.get("training_samples", 0),
            "learned_tags": learn.get("learned_tags", []),
            "top_good_scores": [
                round(float((r.get("quality") or {}).get("score", 0)), 3)
                for r in good_recs[-5:]
            ],
            "bad_issues": [
                {
                    "score": round(float((r.get("quality") or {}).get("score", 0)), 3),
                    "issues": (r.get("quality") or {}).get("issues", []),
                }
                for r in bad_recs
            ],
        },
    }


def main() -> int:
    print("=== Monster Guardian AI — Train Scan + Good/Bad Analysis ===\n")
    scan = scan_and_archive(ROOT)
    print("SCAN:", json.dumps(scan, ensure_ascii=False, indent=2))
    print()
    analysis = analyze_learning(ROOT)
    print("ANALYSIS:", json.dumps(analysis["summary"], ensure_ascii=False, indent=2))
    print("\nSuggested params:", analysis["status"].get("suggested_params"))
    if analysis["summary"].get("training_ready"):
        print("\nReady for LoRA: python scripts/train_image_quality_4060.py --low-vram")
    else:
        need = max(0, 12 - int(analysis["summary"].get("good", 0)))
        print(f"\nNeed {need} more good samples for LoRA training (target 12).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())