"""Header component for dashboard layout."""

import logging
from typing import Any

from PIL import ImageDraw

from ...config import Config
from ...renderer.dashboard import DashboardRenderer
from ..utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class HeaderComponent:
    """Handles rendering of the dashboard header section."""

    def __init__(self, renderer: DashboardRenderer):
        self.renderer = renderer
        self.layout = LayoutHelper(use_grayscale=Config.hardware.use_grayscale)
        self.TOP_Y = LayoutConstants.MARGIN_SMALL
        self.LINE_TOP_Y = 100
        self.WEATHER_ICON_SIZE = 30

    def draw(
        self, draw: ImageDraw.ImageDraw, width: int, now: Any, weather: dict[str, Any]
    ) -> None:
        """Draw header section with dynamic slot distribution.

        Args:
            draw: PIL ImageDraw object
            width: Canvas width
            now: Current datetime
            weather: Weather data dictionary
        """
        # Define components to display
        header_items = [
            {"type": "date", "data": now},
            {"type": "weather", "data": weather},
            {"type": "greeting"},
            {"type": "time", "data": now},
        ]

        # Calculate dynamic layout using LayoutHelper
        # Use MARGIN_SMALL to match footer's uniform distribution
        col_layout = self.layout.create_column_layout(
            width, len(header_items), padding=LayoutConstants.MARGIN_SMALL
        )

        # Draw each component
        for i, item in enumerate(header_items):
            center_x = col_layout.get_column_center(i)
            self._draw_component(draw, center_x, self.TOP_Y, item)

        # Draw divider line using LayoutHelper with matching margins
        self.layout.draw_horizontal_divider(
            draw,
            self.LINE_TOP_Y,
            start_x=LayoutConstants.MARGIN_SMALL,
            end_x=width - LayoutConstants.MARGIN_SMALL,
            line_width=LayoutConstants.LINE_NORMAL,
        )

    def _draw_two_line_text(
        self,
        draw: ImageDraw.ImageDraw,
        center_x: int,
        top_y: int,
        line1_text: str,
        line2_text: str,
        line1_font=None,
        line2_font=None,
        line1_offset: int = 0,
        line2_offset: int = 35,
    ) -> None:
        """Draw two lines of centered text with configurable fonts and offsets.

        Args:
            draw: PIL ImageDraw object
            center_x: X coordinate for center alignment
            top_y: Y coordinate for first line
            line1_text: Text for first line
            line2_text: Text for second line
            line1_font: Font for first line (defaults to font_m)
            line2_font: Font for second line (defaults to font_m)
            line1_offset: Y offset for first line from top_y
            line2_offset: Y offset for second line from top_y
        """
        r = self.renderer
        line1_font = line1_font or r.font_m
        line2_font = line2_font or r.font_m

        r.draw_centered_text(
            draw,
            center_x,
            top_y + line1_offset,
            line1_text,
            font=line1_font,
            fill=r.COLOR_BLACK,
            align_y_center=False,
        )
        r.draw_centered_text(
            draw,
            center_x,
            top_y + line2_offset,
            line2_text,
            font=line2_font,
            fill=r.COLOR_BLACK,
            align_y_center=False,
        )

    def _draw_component(
        self, draw: ImageDraw.ImageDraw, center_x: int, top_y: int, item_data: dict[str, Any]
    ) -> None:
        """Draw individual header component."""
        r = self.renderer
        item_type = item_data["type"]

        match item_type:
            case "weather":
                data = item_data["data"]
                # Line 1: City and temperature
                r.draw_centered_text(
                    draw,
                    center_x,
                    top_y,
                    f"{Config.api.city_name} {data.get('temp', '--')}°",
                    font=r.font_m,
                    fill=r.COLOR_BLACK,
                    align_y_center=False,
                )

                # Line 2: Icon + description (vertically centered)
                icon_y = top_y + 55
                w_main = data.get("icon", "")

                # Determine icon name based on weather condition
                icon_mapping = {
                    "sun": ["Clear", "Sun"],
                    "rain": ["Rain", "Drizzle"],
                    "snow": ["Snow"],
                    "thunder": ["Thunder"],
                }

                icon_name = "cloud"  # Default
                for icon, keywords in icon_mapping.items():
                    if any(keyword in w_main for keyword in keywords):
                        icon_name = icon
                        break

                # Process description text
                desc = data.get("desc", "--")
                if desc == "Clouds":
                    desc = "Cloudy"
                if desc == "Thunderstorm":
                    desc = "Storm"

                # Calculate centering for icon + text combination
                icon_size = self.WEATHER_ICON_SIZE
                try:
                    text_bbox = r.font_s.getbbox(desc)
                    text_width = text_bbox[2] - text_bbox[0]
                except Exception:
                    text_width = 40  # Fallback

                total_width = icon_size + 2 + text_width
                start_x = center_x - (total_width // 2)
                icon_x = start_x
                text_x = start_x + icon_size + 2

                r.draw_weather_icon(draw, icon_x, icon_y, icon_name, size=icon_size)
                draw.text((text_x, icon_y - 16), desc, font=r.font_s, fill=r.COLOR_BLACK)

            case "date":
                data = item_data["data"]
                weekday = data.strftime("%a")
                day = data.strftime("%d")
                month_year = data.strftime("%b %Y")

                self._draw_two_line_text(
                    draw,
                    center_x,
                    top_y,
                    f"{weekday}, {day}",
                    month_year,
                    line1_font=r.font_date_big,
                    line2_font=r.font_s,
                    line2_offset=40,
                )

            case "time":
                data = item_data["data"]
                self._draw_two_line_text(
                    draw,
                    center_x,
                    top_y,
                    "Updated",
                    data.strftime("%H:%M"),
                    line1_font=r.font_s,
                    line2_font=r.font_m,
                )

            case "greeting":
                self._draw_two_line_text(
                    draw,
                    center_x,
                    top_y,
                    Config.personal.greeting_label,
                    Config.personal.greeting_text,
                )

            case "custom":
                self._draw_two_line_text(
                    draw,
                    center_x,
                    top_y,
                    item_data["label"],
                    item_data["value"],
                    line1_font=r.font_s,
                    line2_font=r.font_value,
                )
