"""Tests for Dify bridge — fallback and status."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monster_ai.config import DifySettings
from monster_ai.modules.dify.bridge import DifyBridge


@pytest.fixture
def disabled_bridge() -> DifyBridge:
    return DifyBridge(DifySettings(enabled=False))


@pytest.mark.asyncio
async def test_dify_disabled_falls_back(disabled_bridge: DifyBridge) -> None:
    fallback = AsyncMock(return_value={"ok": True, "url": "/test.png"})
    result = await disabled_bridge.generate_image(
        prompt="test",
        fallback_fn=fallback,
    )
    assert result["url"] == "/test.png"
    fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_dify_health_when_disabled(disabled_bridge: DifyBridge) -> None:
    st = await disabled_bridge.health()
    assert st["enabled"] is False
    assert st["configured"] is False


@pytest.mark.asyncio
async def test_dify_workflow_empty_output_falls_back() -> None:
    settings = DifySettings(
        enabled=True,
        api_url="https://api.dify.ai/v1",
        workflow_image_id="wf-123",
    )
    fallback = AsyncMock(return_value={"ok": True, "provider": "monster"})
    with patch.dict("os.environ", {"DIFY_API_KEY": "test-key"}):
        bridge = DifyBridge(settings)
        bridge.client.run_workflow = AsyncMock(return_value={"data": {"outputs": {}}})
        result = await bridge.generate_image(prompt="x", fallback_fn=fallback)
    assert result["provider"] == "monster"
    assert "dify_fallback_reason" in result