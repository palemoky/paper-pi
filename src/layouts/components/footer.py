"""Footer component for dashboard layout."""

import logging
from typing import Any

from PIL import ImageDraw

from ...renderer.dashboard import DashboardRenderer
from ..utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class FooterComponent:
    """Handles rendering of the dashboard footer section."""

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
        claude_usage: dict[str, int | str] | None = None,
    ) -> None:
        """Draw the footer section: supports dynamic slot distribution.

        Args:
            draw: PIL ImageDraw object
            width: Canvas width
            commits: GitHub commit count
            vps_data: VPS usage data
            btc_data: Bitcoin price data
            week_prog: Week progress percentage
            claude_usage: Claude usage values with keys hourly_usage/weekly_usage and reset strings
        """
        r = self.renderer

        # Construct BTC string
        btc_val = f"${btc_data.get('usd', 0):,}"
        change = btc_data.get("usd_24h_change", 0.0)
        btc_label = f"BTC ({change:+.1f}%)"

        # Define footer components
        left_item = {"label": "Weekly", "value": week_prog, "type": "ring"}
        if isinstance(claude_usage, dict):
            hourly_usage = max(
                0, min(100, int(claude_usage.get("hourly_usage", claude_usage.get("hourly", 0))))
            )
            weekly_usage = max(
                0, min(100, int(claude_usage.get("weekly_usage", claude_usage.get("weekly", 0))))
            )
            left_item = {
                "label": "AI Usage",
                "value": {
                    "provider_name": str(claude_usage.get("provider_name", "Claude")),
                    "hourly_usage": hourly_usage,
                    "weekly_usage": weekly_usage,
                    "hourly_reset": str(claude_usage.get("hourly_reset", "--")),
                    "weekly_reset": str(claude_usage.get("weekly_reset", "--")),
                },
                "type": "usage_table",
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
            elif item["type"] == "usage_table":
                self._draw_usage_table_item(draw, center_x, item["value"])
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

    def _draw_usage_table_item(
        self, draw: ImageDraw.ImageDraw, center_x: int, value: dict[str, int | str]
    ) -> None:
        """Draw Claude usage as a 3-column table: Claude/Hourly/Weekly."""
        r = self.renderer
        hourly_usage = max(0, min(100, int(value.get("hourly_usage", value.get("hourly", 0)))))
        weekly_usage = max(0, min(100, int(value.get("weekly_usage", value.get("weekly", 0)))))
        provider_name = str(value.get("provider_name", "Claude"))
        hourly_reset = str(value.get("hourly_reset", "--"))
        weekly_reset = str(value.get("weekly_reset", "--"))

        table_w = 150
        table_h = 57
        left = center_x - table_w // 2
        top = self.FOOTER_CENTER_Y - table_h // 2
        right = left + table_w
        bottom = top + table_h

        # Outer border
        draw.rectangle((left, top, right, bottom), outline=0, width=1)

        col_w = table_w // 3
        x1 = left + col_w
        x2 = left + 2 * col_w
        draw.line((x1, top, x1, bottom), fill=0, width=1)
        draw.line((x2, top, x2, bottom), fill=0, width=1)

        row_h = table_h // 3
        y1 = top + row_h
        y2 = top + 2 * row_h
        draw.line((left, y1, right, y1), fill=0, width=1)
        draw.line((left, y2, right, y2), fill=0, width=1)

        headers = [provider_name, "Hourly", "Weekly"]
        usage_row = ["Usage", f"{hourly_usage}%", f"{weekly_usage}%"]
        reset_row = ["Reset", hourly_reset, weekly_reset]

        rows = [headers, usage_row, reset_row]
        for row_index, row_values in enumerate(rows):
            center_y = top + row_h * row_index + row_h // 2
            for col_index, text in enumerate(row_values):
                cell_center_x = left + col_w * col_index + col_w // 2
                r.draw_centered_text(
                    draw,
                    cell_center_x,
                    center_y,
                    str(text),
                    font=r.font_xxs,
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

        # Special handling for GitHub stats (dictionary)
        if (
            isinstance(value, dict)
            and "day" in value
            and "week" in value
            and "month" in value
            and "year" in value
        ):
            offset_x = 25
            offset_y = 15

            # Define 2x2 grid positions: (key, x_offset, y_offset)
            positions = [
                ("day", -offset_x, -offset_y),  # Top-left
                ("week", +offset_x, -offset_y),  # Top-right
                ("month", -offset_x, +offset_y),  # Bottom-left
                ("year", +offset_x, +offset_y),  # Bottom-right
            ]

            # Draw all four values in a loop
            for key, x_offset, y_offset in positions:
                r.draw_centered_text(
                    draw,
                    center_x + x_offset,
                    self.FOOTER_CENTER_Y + y_offset,
                    str(value[key]),
                    font=r.font_commits,
                    align_y_center=True,
                )

            # Draw cross lines using LayoutHelper
            self.layout.draw_cross_divider(
                draw,
                center_x,
                self.FOOTER_CENTER_Y,
                h_length=(offset_x + 15) * 2,
                v_length=(offset_y + 10) * 2,
            )
        else:
            # Fallback to text if not a valid dict
            self._draw_text_item(draw, center_x, str(value))
