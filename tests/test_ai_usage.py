"""Tests for AI usage token file loading and invalid-token short-circuit."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.config import Config
from src.providers import ai_usage


@pytest.mark.asyncio
async def test_claude_usage_uses_token_file(monkeypatch, tmp_path: Path):
    """Provider should read OAuth token from mounted secret file."""
    token_file = tmp_path / "claude_oauth_token"
    token_file.write_text("file-token\n", encoding="utf-8")

    monkeypatch.setattr(Config.api, "claude_oauth_token_file", str(token_file))
    monkeypatch.setattr(Config.api, "claude_oauth_token", "env-token")

    ai_usage._INVALID_TOKEN_BY_PROVIDER.clear()
    await ai_usage.get_claude_usage.cache.clear()

    payload = {
        "five_hour": {"utilization": 10, "remaining_seconds": 1800},
        "seven_day": {"utilization": 20, "remaining_seconds": 3600},
    }
    request = httpx.Request("GET", "https://api.anthropic.com/api/oauth/usage")
    client = MagicMock()
    client.get = AsyncMock(return_value=httpx.Response(200, request=request, json=payload))

    result = await ai_usage.get_claude_usage(client)

    assert result is not None
    assert result["provider_name"] == "Claude"
    assert result["hourly_usage"] == 10
    assert result["weekly_usage"] == 20
    client.get.assert_awaited_once()
    assert client.get.await_args.kwargs["headers"]["Authorization"] == "Bearer file-token"


@pytest.mark.asyncio
async def test_claude_usage_short_circuits_after_non_200(monkeypatch, tmp_path: Path):
    """After non-200, same token should be skipped until token rotates."""
    token_file = tmp_path / "claude_oauth_token"
    token_file.write_text("stale-token\n", encoding="utf-8")

    monkeypatch.setattr(Config.api, "claude_oauth_token_file", str(token_file))
    monkeypatch.setattr(Config.api, "claude_oauth_token", "")

    ai_usage._INVALID_TOKEN_BY_PROVIDER.clear()
    await ai_usage.get_claude_usage.cache.clear()

    request = httpx.Request("GET", "https://api.anthropic.com/api/oauth/usage")
    response = httpx.Response(401, request=request)
    status_error = httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    client = MagicMock()
    client.get = AsyncMock(side_effect=status_error)

    first = await ai_usage.get_claude_usage(client)
    assert first == {
        "provider_name": "Claude",
        "hourly_usage": "--",
        "weekly_usage": "--",
        "hourly_reset": "--",
        "weekly_reset": "--",
    }
    client.get.assert_awaited_once()

    await ai_usage.get_claude_usage.cache.clear()
    client.get.reset_mock()

    second = await ai_usage.get_claude_usage(client)
    assert second == first
    client.get.assert_not_awaited()

    token_file.write_text("fresh-token\n", encoding="utf-8")
    await ai_usage.get_claude_usage.cache.clear()

    success_payload = {
        "five_hour": {"utilization": 33, "remaining_seconds": 1200},
        "seven_day": {"utilization": 44, "remaining_seconds": 7200},
    }
    client.get = AsyncMock(return_value=httpx.Response(200, request=request, json=success_payload))

    third = await ai_usage.get_claude_usage(client)
    assert third is not None
    assert third["hourly_usage"] == 33
    assert third["weekly_usage"] == 44
    client.get.assert_awaited_once()
