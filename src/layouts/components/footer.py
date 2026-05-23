"""Footer component for dashboard layout."""

import logging
from typing import Any

from PIL import ImageDraw

from ...renderer.dashboard import DashboardRenderer
from ..utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class FooterComponent:
    """Handles rendering of the dashboard footer section."""

    _CROSS_POSITIONS = (
        ("top_left", -1, -1),
        ("top_right", 1, -1),
        ("bottom_left", -1, 1),
        ("bottom_right", 1, 1),
    )
    _CROSS_KEY_ALIASES = {
        "top_left": ("top_left", "day"),
        "top_right": ("top_right", "week"),
        "bottom_left": ("bottom_left", "month"),
        "bottom_right": ("bottom_right", "year"),
    }

    def __init__(self, renderer: DashboardRenderer):
        self.renderer = renderer
        self.layout = LayoutHelper(use_grayscale=False)  # Will be updated based on Config if needed
        self.FOOTER_CENTER_Y = 410
        self.FOOTER_LABEL_Y = 445

    def draw(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        commits: int | dict,
        vps_data: int,
        btc_data: dict[str, Any],
        week_prog: int,
        llm_usage: dict[str, int | str] | None = None,
    ) -> None:
        """Draw the footer section: supports dynamic slot distribution.

        Args:
            draw: PIL ImageDraw object
            width: Canvas width
            commits: GitHub commit count
            vps_data: VPS usage data
            btc_data: Bitcoin price data
            week_prog: Week progress percentage
            llm_usage: LLM usage values with keys hourly_usage/weekly_usage and reset strings
        """
        r = self.renderer

        # Construct BTC string
        btc_val = f"${btc_data.get('usd', 0):,}"
        change = btc_data.get("usd_24h_change", 0.0)
        btc_label = f"BTC ({change:+.1f}%)"

        # Define footer components
        left_item = {"label": "Weekly", "value": week_prog, "type": "ring"}
        if isinstance(llm_usage, dict):
            provider_name = str(llm_usage.get("provider_name", "Claude"))
            hourly_usage = max(
                0, min(100, int(llm_usage.get("hourly_usage", llm_usage.get("hourly", 0))))
            )
            weekly_usage = max(
                0, min(100, int(llm_usage.get("weekly_usage", llm_usage.get("weekly", 0))))
            )
            left_item = {
                "label": provider_name,
                "value": self._build_cross_value(
                    f"{hourly_usage}%",
                    f"{weekly_usage}%",
                    str(llm_usage.get("hourly_reset", "--")),
                    str(llm_usage.get("weekly_reset", "--")),
                ),
                "type": "cross",
            }

        footer_items = [
            left_item,
            {"label": "Commits", "value": commits, "type": "cross"},
            {"label": btc_label, "value": btc_val, "type": "text"},
            {"label": "VPS Data", "value": vps_data, "type": "ring"},
        ]

        # Calculate dynamic layout using LayoutHelper
        col_layout = self.layout.create_column_layout(
            width, len(footer_items), padding=LayoutConstants.MARGIN_SMALL
        )

        # Loop to draw components
        for i, item in enumerate(footer_items):
            center_x = col_layout.get_column_center(i)

            # Draw label
            if item["label"]:
                r.draw_centered_text(
                    draw,
                    center_x,
                    self.FOOTER_LABEL_Y,
                    item["label"],
                    font=r.font_s,
                    align_y_center=False,
                )

            # Draw value based on type
            if item["type"] == "ring":
                self._draw_ring_item(draw, center_x, item["value"])
            elif item["type"] == "cross":
                self._draw_cross_item(draw, center_x, item["value"])
            elif item["type"] == "text":
                self._draw_text_item(draw, center_x, str(item["value"]))
            else:
                logger.warning(f"Unknown footer item type: {item['type']}")
                self._draw_text_item(draw, center_x, str(item["value"]))

    def _draw_ring_item(self, draw: ImageDraw.ImageDraw, center_x: int, value: int) -> None:
        """Draw a ring progress item."""
        r = self.renderer
        radius = 32
        r.draw_progress_ring(
            draw,
            center_x,
            self.FOOTER_CENTER_Y,
            radius,
            value,
            thickness=6,
        )
        r.draw_centered_text(
            draw,
            center_x,
            self.FOOTER_CENTER_Y,
            f"{value}%",
            font=r.font_xs,
            align_y_center=True,
        )

    def _draw_text_item(self, draw: ImageDraw.ImageDraw, center_x: int, value: str) -> None:
        """Draw a simple text item."""
        r = self.renderer
        r.draw_centered_text(
            draw,
            center_x,
            self.FOOTER_CENTER_Y,
            value,
            font=r.font_date_big,
            align_y_center=True,
        )

    def _draw_cross_item(self, draw: ImageDraw.ImageDraw, center_x: int, value: Any) -> None:
        """Draw a cross layout item (typically for GitHub stats)."""
        r = self.renderer

        normalized_value = self._normalize_cross_value(value)
        if normalized_value is None:
            self._draw_text_item(draw, center_x, str(value))
            return

        offset_x = 30
        offset_y = 18

        for position_name, x_sign, y_sign in self._CROSS_POSITIONS:
            text_x = center_x + (x_sign * offset_x)
            text_y = self.FOOTER_CENTER_Y + (y_sign * offset_y)
            text_value = normalized_value[position_name]
            text_font = r.font_commits if y_sign < 0 else r.font_xs

            r.draw_centered_text(
                draw,
                text_x,
                text_y,
                text_value,
                font=text_font,
                align_y_center=True,
            )

        self.layout.draw_cross_divider(
            draw,
            center_x,
            self.FOOTER_CENTER_Y,
            h_length=(offset_x + 25) * 2,
            v_length=(offset_y + 10) * 2,
        )

    def _build_cross_value(
        self, top_left: Any, top_right: Any, bottom_left: Any, bottom_right: Any
    ) -> dict[str, str]:
        """Build a normalized cross value dictionary."""
        return {
            "top_left": str(top_left),
            "top_right": str(top_right),
            "bottom_left": str(bottom_left),
            "bottom_right": str(bottom_right),
        }

    def _normalize_cross_value(self, value: Any) -> dict[str, str] | None:
        """Normalize legacy/new cross payloads to directional keys."""
        if not isinstance(value, dict):
            return None

        normalized: dict[str, str] = {}
        for position_name, aliases in self._CROSS_KEY_ALIASES.items():
            matched_value = None
            for key in aliases:
                if key in value:
                    matched_value = value[key]
                    break

            if matched_value is None:
                return None

            normalized[position_name] = str(matched_value)

        return normalized
