"""HackerNews component for dashboard layout."""

import logging
from typing import Any

from PIL import ImageDraw

from ...config import Config
from ...renderer.dashboard import DashboardRenderer
from ..utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class HackerNewsComponent:
    """Handles rendering of the HackerNews section."""

    def __init__(self, renderer: DashboardRenderer):
        self.renderer = renderer
        self.layout = LayoutHelper(use_grayscale=Config.hardware.use_grayscale)
        self.LIST_HEADER_Y = 115
        self.LIST_START_Y = 155
        self.LINE_H = 40
        self.LINE_BOTTOM_Y = 365

    def draw(self, draw: ImageDraw.ImageDraw, width: int, hn_data: list | dict[str, Any]) -> None:
        """Draw Hacker News stories section with pagination support.

        Args:
            draw: PIL ImageDraw object
            width: Canvas width
            hn_data: Hacker News data (list or dict with pagination)
        """
        r = self.renderer

        # Support both old format (list) and new format (dict with pagination)
        if isinstance(hn_data, list):
            stories = hn_data[:5]
            header_text = "Hacker News Top Stories"
            start_idx = 1
        else:
            stories = hn_data.get("stories", [])
            start_idx = hn_data.get("start_idx", 1)
            end_idx = hn_data.get("end_idx", 5)
            header_text = f"HN {start_idx}~{end_idx}"

        # Draw header
        r.draw_centered_text(
            draw,
            width // 2,
            self.LIST_HEADER_Y,
            header_text,
            r.font_m,
            align_y_center=False,
        )

        # Draw stories
        for i, story in enumerate(stories):
            y = self.LIST_START_Y + i * self.LINE_H
            title = story.get("title", "")
            score = story.get("score", 0)

            global_idx = start_idx + i
            left_text = f"{global_idx}. {title}"
            right_text = f"{score}▲"

            # Calculate available width for title
            try:
                score_bbox = r.font_s.getbbox(right_text)
                score_width = score_bbox[2] - score_bbox[0]
            except Exception:
                score_width = 30

            title_max_width = width - 80 - score_width - 20

            # Draw left-aligned title (truncated)
            r.draw_truncated_text(
                draw,
                40,
                y,
                left_text,
                r.font_s,
                title_max_width,
            )

            # Draw right-aligned score
            draw.text(
                (width - 40 - score_width, y),
                right_text,
                font=r.font_s,
                fill=0,
            )

        # Draw divider line using LayoutHelper
        self.layout.draw_horizontal_divider(
            draw, self.LINE_BOTTOM_Y, width=width, line_width=LayoutConstants.LINE_NORMAL
        )
