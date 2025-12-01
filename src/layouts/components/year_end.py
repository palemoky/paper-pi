"""Year-end summary component for dashboard layout."""

import datetime
import logging
from typing import Any

from PIL import ImageDraw

from src.config import BASE_DIR

from ...renderer.dashboard import DashboardRenderer
from ..utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class YearEndSummaryComponent:
    """Handles rendering of the year-end summary screen."""

    def __init__(self, renderer: DashboardRenderer):
        self.renderer = renderer
        self.layout = LayoutHelper(use_grayscale=False)  # Will be updated based on Config if needed

    def draw(
        self, draw: ImageDraw.ImageDraw, width: int, height: int, summary_data: dict[str, Any]
    ) -> None:
        """Draw year-end summary (displayed on Dec 31st).

        Args:
            draw: PIL ImageDraw object
            width: Canvas width
            height: Canvas height
            summary_data: Year-end summary statistics
        """
        r = self.renderer
        now = datetime.datetime.now()
        year = now.year
        center_x = width // 2

        # === Layout Constants (using standardized values) ===
        MARGIN_Y = LayoutConstants.MARGIN_XLARGE - 5  # 55
        TITLE_Y = MARGIN_Y
        DIVIDER_TOP_Y = 120
        DIVIDER_BOTTOM_Y = height - 100

        # Grid Layout
        GRID_START_Y = 150
        GRID_ROW_HEIGHT = 130
        GRID_LABEL_OFFSET_1 = 50  # First line of label
        GRID_LABEL_OFFSET_2 = 70  # Second line of label

        # Column Offsets (distance from column center)
        LEFT_COL_OFFSET_INNER = 45
        LEFT_COL_OFFSET_OUTER = 75
        RIGHT_COL_OFFSET_INNER = 55
        RIGHT_COL_OFFSET_OUTER = 55

        # Middle Column
        MID_CONTRIB_Y = GRID_START_Y
        MID_CONTRIB_LABEL_Y = GRID_START_Y + 50
        MID_LANG_TITLE_Y = GRID_START_Y + GRID_ROW_HEIGHT
        MID_LANG_ICONS_Y = MID_LANG_TITLE_Y + 60
        MID_SEPARATOR_Y = (MID_CONTRIB_LABEL_Y + MID_LANG_TITLE_Y) // 2

        # Bottom Message
        BOTTOM_MSG_Y = height - MARGIN_Y

        # === Draw Content ===

        # Title
        title = f"{year} Year in Review"
        r.draw_centered_text(draw, center_x, TITLE_Y, title, font=r.font_l, align_y_center=True)

        # Extract all statistics
        total_contributions = summary_data.get("total_contributions", summary_data.get("total", 0))
        total_commits = summary_data.get("total_commits", 0)
        total_prs = summary_data.get("total_prs", 0)
        total_reviews = summary_data.get("total_reviews", 0)
        total_issues = summary_data.get("total_issues", 0)
        longest_streak = summary_data.get("longest_streak", 0)
        current_streak = summary_data.get("current_streak", 0)
        total_stars = summary_data.get("total_stars", 0)
        top_languages = summary_data.get("top_languages", [])
        most_productive_day = summary_data.get("most_productive_day", "N/A")

        # === 3-Column Layout using LayoutHelper ===
        col_layout = self.layout.create_column_layout(width, 3, padding=0)
        left_center = col_layout.get_column_center(0)
        mid_center = col_layout.get_column_center(1)
        right_center = col_layout.get_column_center(2)

        # Vertical Dividers using LayoutHelper
        col_width = width // 3
        self.layout.draw_vertical_divider(draw, col_width, DIVIDER_TOP_Y, DIVIDER_BOTTOM_Y)
        self.layout.draw_vertical_divider(draw, col_width * 2, DIVIDER_TOP_Y, DIVIDER_BOTTOM_Y)

        # === LEFT COLUMN: Activity Details (2x2 Grid) ===
        l_col1_x = left_center - LEFT_COL_OFFSET_INNER
        l_col2_x = left_center + LEFT_COL_OFFSET_OUTER

        # Helper to draw grid item with auto-scaling
        def draw_grid_item(x, y, value, label, value_font=r.font_l, label_font=r.font_s):
            val_str = str(value)
            # Auto-scale font for long numbers
            font_to_use = value_font
            if len(val_str) > 4:
                font_to_use = r.font_m

            r.draw_centered_text(draw, x, y, val_str, font=font_to_use, align_y_center=True)

            # Split long labels if needed
            if "\n" in label:
                parts = label.split("\n")
                r.draw_centered_text(
                    draw, x, y + GRID_LABEL_OFFSET_1, parts[0], font=label_font, align_y_center=True
                )
                r.draw_centered_text(
                    draw, x, y + GRID_LABEL_OFFSET_2, parts[1], font=label_font, align_y_center=True
                )
            else:
                # Check if label is too long for single line
                if len(label) > 12:
                    r.draw_centered_text(
                        draw, x, y + GRID_LABEL_OFFSET_1, label, font=r.font_xs, align_y_center=True
                    )
                else:
                    r.draw_centered_text(
                        draw,
                        x,
                        y + GRID_LABEL_OFFSET_1,
                        label,
                        font=label_font,
                        align_y_center=True,
                    )

        # Row 1
        draw_grid_item(l_col1_x, GRID_START_Y, total_commits, "Commits")
        draw_grid_item(l_col2_x, GRID_START_Y, total_prs, "PRs")

        # Row 2
        draw_grid_item(l_col1_x, GRID_START_Y + GRID_ROW_HEIGHT, total_issues, "Issues")
        draw_grid_item(l_col2_x, GRID_START_Y + GRID_ROW_HEIGHT, total_reviews, "Reviews")

        # === MIDDLE COLUMN: Highlights ===
        # Total Contributions
        r.draw_centered_text(
            draw,
            mid_center,
            MID_CONTRIB_Y,
            str(total_contributions),
            font=r.font_l,
            align_y_center=True,
        )
        r.draw_centered_text(
            draw,
            mid_center,
            MID_CONTRIB_LABEL_Y,
            "Total Contributions",
            font=r.font_m,
            align_y_center=True,
        )

        # Separator inside middle column using LayoutHelper
        self.layout.draw_horizontal_divider(
            draw,
            MID_SEPARATOR_Y,
            start_x=mid_center - 40,
            end_x=mid_center + 40,
        )

        # Top Languages
        r.draw_centered_text(
            draw, mid_center, MID_LANG_TITLE_Y, "Top Languages", font=r.font_s, align_y_center=True
        )

        # Language Logo Mapping
        lang_map = {
            "Python": "Python.png",
            "Go": "Go.png",
            "Java": "Java.png",
            "Rust": "Rust.png",
            "PHP": "PHP.png",
            "TypeScript": "TypeScript.png",
            "JavaScript": "JavaScript.png",
        }

        # Draw languages horizontally
        langs_to_show = top_languages[:3]
        if langs_to_show:
            total_width = len(langs_to_show) * 50  # 40px icon + 10px spacing
            start_x = mid_center - (total_width // 2) + 25

            from ...renderer.icons.holiday import HolidayIcons

            for i, lang in enumerate(langs_to_show):
                icon_name = lang_map.get(lang)
                x = start_x + (i * 50)

                # Check if we have an icon for this language
                if icon_name:
                    HolidayIcons().draw_image_icon(
                        draw,
                        x,
                        MID_LANG_ICONS_Y,
                        f"{BASE_DIR}/resources/icons/languages/{icon_name}",
                        size=40,
                    )
                else:
                    # Fallback to text abbreviation if no icon
                    draw.ellipse(
                        (x - 20, MID_LANG_ICONS_Y - 20, x + 20, MID_LANG_ICONS_Y + 20),
                        outline=0,
                        width=1,
                    )
                    abbr = lang[:2]
                    r.draw_centered_text(
                        draw, x, MID_LANG_ICONS_Y, abbr, font=r.font_s, align_y_center=True
                    )

        # === RIGHT COLUMN: Achievements (2x2 Grid) ===
        r_col1_x = right_center - RIGHT_COL_OFFSET_INNER
        r_col2_x = right_center + RIGHT_COL_OFFSET_OUTER

        # Row 1
        draw_grid_item(r_col1_x, GRID_START_Y, longest_streak, "Longest\nStreak")
        draw_grid_item(r_col2_x, GRID_START_Y, current_streak, "Current\nStreak")

        # Row 2
        draw_grid_item(r_col1_x, GRID_START_Y + GRID_ROW_HEIGHT, total_stars, "Stars\nEarned")
        draw_grid_item(
            r_col2_x, GRID_START_Y + GRID_ROW_HEIGHT, most_productive_day, "Most\nProductive"
        )

        # Bottom greeting message
        r.draw_centered_text(
            draw,
            center_x,
            BOTTOM_MSG_Y,
            f"Cheers to {year + 1}!",
            font=r.font_m,
            align_y_center=True,
        )
