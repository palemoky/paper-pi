"""Dashboard layout manager for E-Ink display.

This module handles the visual layout and rendering of all dashboard components
including weather, date, time, GitHub stats, and custom widgets.
"""

import datetime
import logging

from PIL import Image, ImageDraw

from ..config import Config
from ..renderer.dashboard import DashboardRenderer
from .components.footer import FooterComponent
from .components.hackernews import HackerNewsComponent
from .components.header import HeaderComponent
from .components.todo_list import TodoListComponent
from .components.year_end import YearEndSummaryComponent

logger = logging.getLogger(__name__)


class DashboardLayout:
    """Manages the layout and rendering of dashboard components.

    Handles positioning, sizing, and drawing of all UI elements on the E-Ink display.
    Supports both normal dashboard mode and special holiday greeting screens.
    """

    def __init__(self):
        self.renderer = DashboardRenderer()

        # Initialize components
        self.header = HeaderComponent(self.renderer)
        self.footer = FooterComponent(self.renderer)
        self.hackernews = HackerNewsComponent(self.renderer)
        self.todo_list = TodoListComponent(self.renderer)
        self.year_end = YearEndSummaryComponent(self.renderer)

        # Legacy attributes for backward compatibility if needed
        self._current_hackernews = []
        self._current_goals = Config.todo.list_goals
        self._current_must = Config.todo.list_must
        self._current_optional = Config.todo.list_optional

    def create_image(self, width, height, data):
        """Generate complete dashboard image.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            data: Dictionary containing all display data

        Returns:
            PIL Image object (mode "L" for grayscale or "1" for B/W)
        """
        # Create canvas with appropriate mode
        image_mode = "L" if Config.hardware.use_grayscale else "1"
        image = Image.new(image_mode, (width, height), 255)
        draw = ImageDraw.Draw(image)

        # Extract data
        now = datetime.datetime.now()
        weather = data.get("weather", {})
        commits = data.get("github_commits", 0)
        vps_data = data.get("vps_usage", 0)
        btc_data = data.get("btc_price", {})
        week_prog = data.get("week_progress", 0)

        # Check rotation state
        show_hackernews = data.get("show_hackernews", False)

        # Extract TODO lists or Hacker News
        if show_hackernews:
            self._current_hackernews = data.get("hackernews", [])
        else:
            self._current_goals = data.get("todo_goals", Config.todo.list_goals)
            self._current_must = data.get("todo_must", Config.todo.list_must)
            self._current_optional = data.get("todo_optional", Config.todo.list_optional)

        # Draw three main sections using components
        self.header.draw(draw, width, now, weather)

        # Draw middle section based on rotation
        if show_hackernews:
            self.hackernews.draw(draw, width, self._current_hackernews)
        else:
            self.todo_list.draw(
                draw, self._current_goals, self._current_must, self._current_optional
            )

        self.footer.draw(draw, width, commits, vps_data, btc_data, week_prog)

        return image

    def _draw_hackernews(self, draw, width):
        """Legacy method for backward compatibility/external calls."""
        # Some tasks might call this directly (e.g. hackernews task)
        # We delegate to the component
        self.hackernews.draw(draw, width, self._current_hackernews)

    def _draw_year_end_summary(self, draw, width, height, summary_data):
        """Draw year-end summary (displayed on Dec 31st)."""
        self.year_end.draw(draw, width, height, summary_data)
