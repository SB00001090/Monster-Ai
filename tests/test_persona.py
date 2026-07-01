from pathlib import Path

import yaml

from monster_ai.persona.grok import build_system_prompt, resolve_persona


def test_resolve_grok_mode():
    prompt = resolve_persona("grok", None, chat_mode="chat")
    assert prompt is not None
    assert "Monster AI" in prompt
    assert "Grok" in prompt


def test_resolve_custom_mode_uses_user_prompt():
    prompt = resolve_persona("custom", "You are a pirate.", chat_mode="chat")
    assert prompt == "You are a pirate."


def test_resolve_off_mode_without_user():
    assert resolve_persona("off", None, chat_mode="chat") is None


def test_resolve_user_override_beats_grok():
    prompt = resolve_persona("grok", "Custom only.", chat_mode="chat")
    assert prompt == "Custom only."


def test_zh_tw_locale_prompt():
    prompt = resolve_persona("grok", None, chat_mode="chat", locale="zh-TW")
    assert prompt is not None
    assert "Monster AI" in prompt or "你是 Monster AI" in prompt
    assert "繁體中文" in prompt


def test_roleplay_appendix(tmp_path, monkeypatch):
    persona_file = tmp_path / "grok_default.yaml"
    persona_file.write_text(
        yaml.dump({"enabled": True, "grok": {"humor": "high", "directness": "high"}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "personas").mkdir(parents=True)
    (tmp_path / "data" / "personas" / "grok_default.yaml").write_text(
        persona_file.read_text(encoding="utf-8"), encoding="utf-8"
    )
    prompt = build_system_prompt("roleplay")
    assert prompt is not None
    assert "in character" in prompt.lower()