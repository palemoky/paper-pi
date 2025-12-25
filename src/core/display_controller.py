"""Display controller for managing display modes and refresh intervals.

This module handles display mode selection based on time and configuration,
as well as refresh interval calculation for different modes.
"""

import logging

import pendulum

from src.config import Config, _seconds_until_midnight
from src.layouts.holiday import HolidayManager

logger = logging.getLogger(__name__)


class DisplayController:
    """Controls display mode selection and refresh intervals.

    Responsibilities:
    - Determine current display mode based on time and configuration
    - Calculate refresh intervals for different modes
    - Handle special modes (holiday, year-end)

    Example:
        >>> controller = DisplayController()
        >>> mode = controller.get_current_mode()
        >>> interval = controller.get_refresh_interval(mode)
    """

    def __init__(self, config=None):
        """Initialize display controller.

        Args:
            config: Configuration object (defaults to global Config)
        """
        self.config = config or Config

    def get_current_mode(self, now: pendulum.DateTime | None = None) -> str:
        """Determine current display mode based on time and configuration.

        Priority order:
        1. Holiday mode (if today is a configured holiday)
        2. Year-end mode (if December 31st)
        3. Configured display mode

        Args:
            now: Current time (defaults to now in configured timezone)

        Returns:
            Display mode name: "dashboard", "quote", "poetry", "wallpaper", "holiday"
        """
        if now is None:
            now = pendulum.now(self.config.hardware.timezone)

        # Check for holiday
        holiday_manager = HolidayManager()
        if holiday_manager.get_holiday():
            logger.info("🎉 Holiday detected, using holiday mode")
            return "holiday"

        # Check for year-end (December 31st)
        if now.month == 12 and now.day == 31:
            logger.info("🎊 Year-end detected, using year-end mode")
            return "year_end"

        # Use configured mode
        return self.config.display.mode

    def get_refresh_interval(self, mode: str) -> int:
        """Get refresh interval for a display mode.

        Args:
            mode: Display mode name

        Returns:
            Refresh interval in seconds
        """
        # For holiday and year_end modes, dynamically calculate seconds until midnight
        if mode in ("holiday", "year_end"):
            interval = _seconds_until_midnight(self.config.hardware.timezone)
            logger.debug(f"Refresh interval for mode '{mode}': {interval}s (until midnight)")
            return interval

        interval_map = {
            "dashboard": self.config.display.refresh_interval_dashboard,
            "quote": self.config.display.refresh_interval_quote,
            "poetry": self.config.display.refresh_interval_poetry,
            "wallpaper": self.config.display.refresh_interval_wallpaper,
        }

        interval = interval_map.get(mode, self.config.hardware.refresh_interval)
        logger.debug(f"Refresh interval for mode '{mode}': {interval}s")
        return interval
