"""Todo list component for dashboard layout."""

import logging

from PIL import ImageDraw

from ...config import Config
from ...renderer.dashboard import DashboardRenderer
from ..utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class TodoListComponent:
    """Handles rendering of the Todo list section."""

    def __init__(self, renderer: DashboardRenderer):
        self.renderer = renderer
        self.layout = LayoutHelper(use_grayscale=Config.hardware.use_grayscale)
        self.LIST_HEADER_Y = 115
        self.LIST_START_Y = 155
        self.LINE_H = 40
        self.LINE_BOTTOM_Y = 365
        self.MAX_LIST_LINES = 5

        # Column configuration
        self.COLS = [
            {"x": LayoutConstants.MARGIN_LARGE, "max_w": 260},  # Goals
            {"x": 320, "max_w": 220},  # Must
            {"x": 560, "max_w": 220},  # Optional
        ]

    def draw(
        self,
        draw: ImageDraw.ImageDraw,
        goals: list[str] | None = None,
        must: list[str] | None = None,
        optional: list[str] | None = None,
    ) -> None:
        """Draw TODO lists section (Goals, Must, Optional).

        Args:
            draw: PIL ImageDraw object
            goals: List of goals
            must: List of must-do items
            optional: List of optional items
        """
        r = self.renderer

        # Use Config defaults if not provided
        goals = goals or Config.LIST_GOALS
        must = must or Config.LIST_MUST
        optional = optional or Config.LIST_OPTIONAL

        # Draw column headers
        headers = ["Goals", "Must", "Optional"]
        for i, header in enumerate(headers):
            r.draw_truncated_text(
                draw,
                self.COLS[i]["x"],
                self.LIST_HEADER_Y,
                header,
                r.font_m,
                self.COLS[i]["max_w"],
            )

        # Process data: truncate lines
        safe_goals = self._limit_list_items(goals, self.MAX_LIST_LINES)
        safe_must = self._limit_list_items(must, self.MAX_LIST_LINES)
        safe_optional = self._limit_list_items(optional, self.MAX_LIST_LINES)

        # Draw content
        self._draw_column(draw, 0, safe_goals)
        self._draw_column(draw, 1, safe_must)
        self._draw_column(draw, 2, safe_optional)

        # Draw divider line using LayoutHelper
        self.layout.draw_horizontal_divider(
            draw,
            self.LINE_BOTTOM_Y,
            width=draw.im.size[0],
            line_width=LayoutConstants.LINE_NORMAL,
        )

    def _draw_column(self, draw: ImageDraw.ImageDraw, col_idx: int, items: list[str]) -> None:
        """Draw a single column of items."""
        r = self.renderer
        col = self.COLS[col_idx]

        for i, text in enumerate(items):
            y = self.LIST_START_Y + i * self.LINE_H

            # Check if item is completed (marked with ✓)
            is_completed = text.startswith("✓")
            if is_completed:
                text = text[1:].strip()  # Remove completion marker

            display_text = text if text == "..." else f"• {text}"

            # Draw text and get bounding box
            bbox = r.draw_truncated_text(
                draw,
                col["x"],
                y,
                display_text,
                r.font_s,
                col["max_w"],
            )

            # Draw strikethrough if completed (skip bullet point)
            if is_completed and bbox:
                self._draw_strikethrough(draw, col["x"], y, bbox, display_text)

    def _draw_strikethrough(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        bbox: tuple[float, float, float, float],
        display_text: str,
    ) -> None:
        """Draw strikethrough line over completed text, skipping bullet point.

        Args:
            draw: PIL ImageDraw object
            x: Starting x position
            y: Text baseline y position
            bbox: Text bounding box (x1, y1, x2, y2)
            display_text: The full display text (e.g., "• Item")
        """
        # Calculate strikethrough position (middle of text height)
        text_height = bbox[3] - bbox[1]
        line_y = y + text_height // 2

        # Calculate bullet point width to skip it
        # If text starts with "• ", skip the bullet and space
        if display_text.startswith("• "):
            bullet_width = draw.textlength("• ", font=self.renderer.font_s)
            line_x1 = x + bullet_width
        else:
            line_x1 = x

        # Draw strikethrough line (only over the text, not the bullet)
        line_x2 = bbox[2]
        draw.line([(line_x1, line_y), (line_x2, line_y)], fill=0, width=2)

    def _limit_list_items(self, src_list: list[str], max_lines: int) -> list[str]:
        """Limit list items and add ellipsis if truncated."""
        if len(src_list) > max_lines:
            return src_list[: max_lines - 1] + ["..."]
        return src_list
