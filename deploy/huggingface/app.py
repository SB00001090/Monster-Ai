"""Monster AI HF Spaces Demo — calls owner Tunnel API."""
from __future__ import annotations

import os

import gradio as gr
import httpx

API = os.environ.get("MONSTER_API_URL", "http://127.0.0.1:7860").rstrip("/")
THRESHOLD = float(os.environ.get("MIN_QUALITY_SCORE", "0.70"))


def generate(prompt: str, template: str, locale: str) -> tuple[str | None, str]:
    if not prompt.strip():
        return None, "請輸入提示詞"
    try:
        with httpx.Client(timeout=180.0) as client:
            r = client.post(
                f"{API}/api/mini/generate",
                json={"prompt": prompt, "template_id": template, "locale": locale},
            )
        if r.status_code >= 400:
            return None, r.text[:800]
        data = r.json()
        url = data.get("url") or ""
        if url and not url.startswith("http"):
            url = f"{API}{url}"
        q = data.get("quality") or {}
        score = q.get("score")
        passed = q.get("passed", True)
        line = f"品質: {score} | 通過: {passed} | 閾值: {THRESHOLD}"
        if score is not None and float(score) < THRESHOLD:
            line += " (低於 70% — 建議重試)"
        return url or None, line
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


with gr.Blocks(title="Monster AI Demo") as demo:
    gr.Markdown("# Monster AI — HF Spaces Demo\nDeveloped by Suckbob")
    with gr.Row():
        prompt = gr.Textbox(label="Prompt", lines=3)
        template = gr.Dropdown(
            ["stable", "fast", "hq", "portrait"],
            value="stable",
            label="Template",
        )
        locale = gr.Dropdown(
            ["zh-TW", "zh-HK", "en", "ja"],
            value="zh-TW",
            label="Locale",
        )
    btn = gr.Button("Generate", variant="primary")
    out_img = gr.Image(label="Output")
    out_meta = gr.Textbox(label="Quality", interactive=False)
    btn.click(generate, [prompt, template, locale], [out_img, out_meta])

demo.launch()