"""Tests that one failing provider cannot abort the whole dashboard refresh.

A single expired credential used to blank the entire panel: TaskGroup is
fail-fast, so one failing child cancelled its siblings and re-raised before
_get_with_cache_fallback ever ran, and main's loop skipped the display update.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import ProviderError
from src.providers.dashboard import Dashboard


@pytest.fixture
def dashboard(tmp_path):
    """Dashboard with an isolated cache file."""
    dm = Dashboard()
    dm.cache_file = tmp_path / "dashboard_cache.json"
    return dm


def _patch_providers(**overrides):
    """Patch every provider called by fetch_dashboard_data.

    Defaults are healthy responses; pass an override to make one fail.
    """
    defaults = {
        "get_weather": {"temp": 21, "desc": "Clear"},
        "get_github_commits": {"day": 3, "week": 12, "month": 40, "year": 500},
        "get_vps_info": 17,
        "get_btc_data": {"usd": 95000, "change": 1.5},
        "get_claude_usage": {"provider_name": "Claude", "percent": 42},
        "get_chatgpt_usage": None,
        "get_kimi_usage": None,
    }
    defaults.update(overrides)

    patchers = []
    for name, value in defaults.items():
        mock = (
            AsyncMock(side_effect=value)
            if isinstance(value, Exception)
            else AsyncMock(return_value=value)
        )
        patchers.append(patch(f"src.providers.dashboard.{name}", mock))
    return patchers


async def _fetch(dashboard, **overrides):
    """Run fetch_dashboard_data in HackerNews mode with providers patched."""
    patchers = _patch_providers(**overrides)
    for p in patchers:
        p.start()
    try:
        # Force the HackerNews branch so the TODO/Notion path stays out of it
        with patch("src.core.TimeSlots") as MockSlots:
            MockSlots.return_value.contains_hour.return_value = False
            with patch(
                "src.providers.hackernews.get_hackernews",
                new_callable=AsyncMock,
                return_value={"page": 1, "total_pages": 10, "stories": []},
            ):
                return await dashboard.fetch_dashboard_data()
    finally:
        for p in patchers:
            p.stop()


class TestDashboardResilience:
    @pytest.mark.asyncio
    async def test_failing_github_does_not_abort_refresh(self, dashboard):
        """An expired GitHub token must not take the rest of the panel down."""
        data = await _fetch(
            dashboard,
            get_github_commits=ProviderError("github", "401 Unauthorized"),
        )

        # The refresh completed instead of raising
        assert data is not None

        # Healthy providers still delivered their data
        assert data["weather"] == {"temp": 21, "desc": "Clear"}
        assert data["vps_usage"] == 17
        assert data["btc_price"] == {"usd": 95000, "change": 1.5}
        assert data["hackernews"]["page"] == 1

        # The failing one fell back to its default
        assert data["github_commits"] == 0

    @pytest.mark.asyncio
    async def test_failing_provider_falls_back_to_cache(self, dashboard):
        """A provider that fails should reuse its last known good value."""
        # First refresh succeeds and populates the cache
        await _fetch(dashboard)
        assert dashboard.load_cache()["github_commits"]["week"] == 12

        # Second refresh: GitHub is down, cached value should survive
        data = await _fetch(
            dashboard,
            get_github_commits=ProviderError("github", "401 Unauthorized"),
        )
        assert data["github_commits"]["week"] == 12

    @pytest.mark.asyncio
    async def test_all_providers_failing_still_returns_data(self, dashboard):
        """Total API blackout should still render a (degraded) panel."""
        boom = ProviderError("any", "network down")
        data = await _fetch(
            dashboard,
            get_weather=boom,
            get_github_commits=boom,
            get_vps_info=boom,
            get_btc_data=boom,
            get_claude_usage=boom,
        )

        assert data is not None
        assert data["weather"] == {}
        assert data["github_commits"] == 0
        assert data["vps_usage"] == 0
