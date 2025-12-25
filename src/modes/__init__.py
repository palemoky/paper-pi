"""Example display mode implementations using the plugin system.

This module demonstrates how to create display modes using the new plugin architecture.
These can serve as templates for creating new display modes.
"""

import httpx
import pendulum
from PIL import Image, ImageDraw

from src.config import Config, _seconds_until_midnight
from src.core.display_mode import DisplayMode, register_mode
from src.layouts.holiday import HolidayManager
from src.layouts.poetry import PoetryLayout
from src.layouts.quote import QuoteLayout
from src.providers.poetry import get_poetry
from src.providers.quote import get_quote


@register_mode
class HolidayMode(DisplayMode):
    """Holiday greeting display mode.

    Activates automatically when a configured holiday is detected.
    """

    @property
    def name(self) -> str:
        return "holiday"

    @property
    def refresh_interval(self) -> int:
        # Dynamically calculate seconds until midnight to ensure accurate countdown
        return _seconds_until_midnight(Config.hardware.timezone)

    def should_activate(self, **kwargs) -> bool:
        """Activate if today is a configured holiday."""
        holiday_manager = HolidayManager()
        return holiday_manager.get_holiday() is not None

    async def fetch_data(self, **kwargs) -> dict:
        """Fetch holiday data."""
        holiday_manager = HolidayManager()
        holiday = holiday_manager.get_holiday()
        return {"holiday": holiday}

    def render(self, width: int, height: int, data: dict) -> Image.Image:
        """Render holiday greeting."""
        from src.layouts import DashboardLayout

        holiday = data["holiday"]
        image_mode = "L" if Config.hardware.use_grayscale else "1"
        image = Image.new(image_mode, (width, height), 255)
        draw = ImageDraw.Draw(image)

        layout = DashboardLayout()
        layout.renderer.draw_full_screen_message(
            draw, width, height, holiday["title"], holiday["message"], holiday.get("icon")
        )
        return image


@register_mode
class YearEndMode(DisplayMode):
    """Year-end summary display mode.

    Activates on December 31st to show GitHub contribution summary.
    """

    @property
    def name(self) -> str:
        return "year_end"

    @property
    def refresh_interval(self) -> int:
        # Dynamically calculate seconds until midnight to ensure accurate countdown
        return _seconds_until_midnight(Config.hardware.timezone)

    def should_activate(self, **kwargs) -> bool:
        """Activate on December 31st."""
        now = kwargs.get("now") or pendulum.now(Config.hardware.timezone)
        return now.month == 12 and now.day == 31

    async def fetch_data(self, **kwargs) -> dict:
        """Fetch year-end summary data."""
        dashboard = kwargs.get("dashboard")
        if dashboard:
            return await dashboard.fetch_year_end_data()
        return {}

    def render(self, width: int, height: int, data: dict) -> Image.Image:
        """Render year-end summary."""
        from src.layouts import DashboardLayout

        image_mode = "L" if Config.hardware.use_grayscale else "1"
        image = Image.new(image_mode, (width, height), 255)
        draw = ImageDraw.Draw(image)

        layout = DashboardLayout()
        layout._draw_year_end_summary(draw, width, height, data["github_year_summary"])
        return image


@register_mode
class QuoteMode(DisplayMode):
    """Quote display mode."""

    @property
    def name(self) -> str:
        return "quote"

    @property
    def refresh_interval(self) -> int:
        return Config.display.refresh_interval_quote

    async def fetch_data(self, **kwargs) -> dict:
        """Fetch quote data."""
        async with httpx.AsyncClient() as client:
            quote = await get_quote(client)
            return {"quote": quote}

    def render(self, width: int, height: int, data: dict) -> Image.Image:
        """Render quote."""
        quote_layout = QuoteLayout()
        return quote_layout.create_quote_image(width, height, data["quote"])


@register_mode
class PoetryMode(DisplayMode):
    """Poetry display mode."""

    @property
    def name(self) -> str:
        return "poetry"

    @property
    def refresh_interval(self) -> int:
        return Config.display.refresh_interval_poetry

    async def fetch_data(self, **kwargs) -> dict:
        """Fetch poetry data."""
        async with httpx.AsyncClient() as client:
            poetry = await get_poetry(client)
            return {"poetry": poetry}

    def render(self, width: int, height: int, data: dict) -> Image.Image:
        """Render poetry."""
        poetry_layout = PoetryLayout()
        return poetry_layout.create_poetry_image(width, height, data["poetry"])


@register_mode
class WallpaperMode(DisplayMode):
    """Wallpaper display mode."""

    @property
    def name(self) -> str:
        return "wallpaper"

    @property
    def refresh_interval(self) -> int:
        # If wallpaper name is specified, use configured interval
        # If random, use configured interval or fallback to 1 hour
        if Config.display.wallpaper_name:
            return Config.display.refresh_interval_wallpaper
        return Config.display.refresh_interval_wallpaper or 3600

    async def fetch_data(self, **kwargs) -> dict:
        """No data needed for wallpaper mode."""
        return {}

    def render(self, width: int, height: int, data: dict) -> Image.Image:
        """Render wallpaper."""
        from src.providers.wallpaper import WallpaperManager

        wallpaper_manager = WallpaperManager()
        wallpaper_name = Config.display.wallpaper_name or None
        return wallpaper_manager.create_wallpaper(width, height, wallpaper_name)
