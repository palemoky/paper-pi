"""Data fetcher for retrieving display data based on mode.

This module handles data fetching logic for different display modes.
Uses on-demand HTTP connections to minimize idle CPU usage.
"""

import logging
from typing import Any

from src.providers import Dashboard

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches data for different display modes.

    Uses on-demand HTTP connections - creates a new connection for each fetch
    and closes it immediately after. This minimizes CPU usage during idle periods
    (which can be 10+ minutes between refreshes on e-ink displays).

    Example:
        >>> fetcher = DataFetcher()
        >>> data = await fetcher.fetch("dashboard")
    """

    async def fetch(self, mode: str) -> dict[str, Any]:
        """Fetch data for a display mode.

        Creates a temporary HTTP client for the duration of the fetch,
        then closes it to minimize resource usage during idle periods.

        Args:
            mode: Display mode name

        Returns:
            Dictionary containing mode-specific data
        """
        logger.debug(f"Fetching data for mode: {mode}")

        if mode == "dashboard":
            return await self._fetch_dashboard()
        elif mode == "quote":
            return await self._fetch_quote()
        elif mode == "poetry":
            return await self._fetch_poetry()
        elif mode == "wallpaper":
            return await self._fetch_wallpaper()
        elif mode == "holiday":
            return await self._fetch_holiday()
        elif mode == "year_end":
            return await self._fetch_year_end()
        else:
            logger.warning(f"Unknown mode '{mode}', using dashboard")
            return await self._fetch_dashboard()

    async def _fetch_dashboard(self) -> dict[str, Any]:
        """Fetch dashboard data with on-demand HTTP connection."""
        async with Dashboard() as dm:
            return await dm.fetch_dashboard_data()

    async def _fetch_quote(self) -> dict[str, Any]:
        """Fetch quote data with on-demand HTTP connection."""
        from src.providers.quote import get_quote

        # get_quote can handle None client (creates its own)
        quote = await get_quote(client=None)
        return {"quote": quote}

    async def _fetch_poetry(self) -> dict[str, Any]:
        """Fetch poetry data with on-demand HTTP connection."""
        from src.providers.poetry import get_poetry

        # get_poetry can handle None client (creates its own)
        poetry = await get_poetry(client=None)
        return {"poetry": poetry}

    async def _fetch_wallpaper(self) -> dict[str, Any]:
        """Fetch wallpaper data (no HTTP needed)."""
        return {}

    async def _fetch_holiday(self) -> dict[str, Any]:
        """Fetch holiday data (no HTTP needed)."""
        from src.layouts.holiday import HolidayManager

        holiday_manager = HolidayManager()
        holiday = holiday_manager.get_holiday()
        return {"holiday": holiday}

    async def _fetch_year_end(self) -> dict[str, Any]:
        """Fetch year-end summary data with on-demand HTTP connection."""
        async with Dashboard() as dm:
            return await dm.fetch_year_end_data()
