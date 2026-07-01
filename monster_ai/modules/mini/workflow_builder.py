"""Mini Monster AI ComfyUI workflows — fast + HQ paths."""
from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any


def _workflows_dir() -> Path:
    return Path(__file__).resolve().parent / "workflows"


def load_mini_workflow(name: str) -> dict[str, Any]:
    path = _workflows_dir() / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Mini workflow not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_mini_txt2img(
    *,
    positive: str,
    negative: str,
    checkpoint: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    seed: int | None = None,
    lora_name: str | None = None,
    lora_strength: float = 0.75,
    template_id: str = "hq",
) -> dict[str, Any]:
    wf_name = "mini_sdxl_fast" if template_id == "fast" else "mini_sdxl_hq"
    wf = copy.deepcopy(load_mini_workflow(wf_name))
    wf["4"]["inputs"]["ckpt_name"] = checkpoint
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    wf["6"]["inputs"]["text"] = positive
    wf["7"]["inputs"]["text"] = negative
    wf["3"]["inputs"]["seed"] = seed if seed is not None else random.randint(0, 2**32 - 1)
    wf["3"]["inputs"]["steps"] = steps
    wf["3"]["inputs"]["cfg"] = cfg
    wf["9"]["inputs"]["filename_prefix"] = "mini_monster"

    if lora_name and "10" in wf:
        wf["10"]["inputs"]["lora_name"] = lora_name
        wf["10"]["inputs"]["strength_model"] = lora_strength
        wf["10"]["inputs"]["strength_clip"] = lora_strength
        wf["3"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
    elif "10" in wf:
        del wf["10"]
        wf["3"]["inputs"]["model"] = ["4", 0]

    return wf