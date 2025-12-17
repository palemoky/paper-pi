"""Tests for DataFetcher.

Note: DataFetcher now uses on-demand HTTP connections, so tests mock
the Dashboard context manager instead of passing a Dashboard instance.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.data_fetcher import DataFetcher


class TestDataFetcher:
    """Tests for DataFetcher class."""

    @pytest.fixture
    def fetcher(self):
        """Create a DataFetcher instance."""
        return DataFetcher()

    @pytest.mark.asyncio
    async def test_fetch_dashboard(self, fetcher):
        """Test fetching dashboard data."""
        mock_dashboard = MagicMock()
        mock_dashboard.fetch_dashboard_data = AsyncMock(return_value={"test": "data"})
        mock_dashboard.__aenter__ = AsyncMock(return_value=mock_dashboard)
        mock_dashboard.__aexit__ = AsyncMock(return_value=None)

        with patch("src.core.data_fetcher.Dashboard", return_value=mock_dashboard):
            data = await fetcher.fetch("dashboard")

        assert data == {"test": "data"}
        mock_dashboard.fetch_dashboard_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_quote(self, fetcher):
        """Test fetching quote data."""
        with patch("src.providers.quote.get_quote", new_callable=AsyncMock) as mock_get_quote:
            mock_get_quote.return_value = "Test Quote"

            data = await fetcher.fetch("quote")

            assert data == {"quote": "Test Quote"}
            mock_get_quote.assert_called_once_with(client=None)

    @pytest.mark.asyncio
    async def test_fetch_poetry(self, fetcher):
        """Test fetching poetry data."""
        with patch("src.providers.poetry.get_poetry", new_callable=AsyncMock) as mock_get_poetry:
            mock_get_poetry.return_value = "Test Poetry"

            data = await fetcher.fetch("poetry")

            assert data == {"poetry": "Test Poetry"}
            mock_get_poetry.assert_called_once_with(client=None)

    @pytest.mark.asyncio
    async def test_fetch_wallpaper(self, fetcher):
        """Test fetching wallpaper data."""
        data = await fetcher.fetch("wallpaper")
        assert data == {}

    @pytest.mark.asyncio
    async def test_fetch_holiday(self, fetcher):
        """Test fetching holiday data."""
        with patch("src.layouts.holiday.HolidayManager") as MockHolidayManager:
            mock_manager = MockHolidayManager.return_value
            mock_manager.get_holiday.return_value = "Christmas"

            data = await fetcher.fetch("holiday")

            assert data == {"holiday": "Christmas"}
            mock_manager.get_holiday.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_year_end(self, fetcher):
        """Test fetching year-end data."""
        mock_dashboard = MagicMock()
        mock_dashboard.fetch_year_end_data = AsyncMock(return_value={"year": "end"})
        mock_dashboard.__aenter__ = AsyncMock(return_value=mock_dashboard)
        mock_dashboard.__aexit__ = AsyncMock(return_value=None)

        with patch("src.core.data_fetcher.Dashboard", return_value=mock_dashboard):
            data = await fetcher.fetch("year_end")

        assert data == {"year": "end"}
        mock_dashboard.fetch_year_end_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_unknown_mode(self, fetcher):
        """Test fetching unknown mode defaults to dashboard."""
        mock_dashboard = MagicMock()
        mock_dashboard.fetch_dashboard_data = AsyncMock(return_value={"test": "data"})
        mock_dashboard.__aenter__ = AsyncMock(return_value=mock_dashboard)
        mock_dashboard.__aexit__ = AsyncMock(return_value=None)

        with patch("src.core.data_fetcher.Dashboard", return_value=mock_dashboard):
            data = await fetcher.fetch("unknown_mode")

        assert data == {"test": "data"}
        mock_dashboard.fetch_dashboard_data.assert_called_once()
