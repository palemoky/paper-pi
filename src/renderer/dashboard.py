"""Dashboard renderer - Main coordinator.

Coordinates text, shapes, and icon rendering using modular components.
"""

import logging
import os

from PIL import ImageFont

from ..config import Config
from .icons import HolidayIcons, WeatherIcons
from .shapes import ShapeRenderer
from .text import TextRenderer

logger = logging.getLogger(__name__)


class DashboardRenderer:
    """Handles all drawing operations for the dashboard.

    Coordinates text rendering, shape drawing, and icon rendering
    using modular components for better organization.
    """

    # Grayscale color constants
    COLOR_BLACK = 0
    COLOR_DARK_GRAY = 128
    COLOR_LIGHT_GRAY = 192
    COLOR_WHITE = 255

    def __init__(self):
        self._load_fonts()

        # Initialize component renderers
        self.text = TextRenderer()
        self.shapes = ShapeRenderer()
        self.weather_icons = WeatherIcons()
        self.holiday_icons = HolidayIcons()

    def _load_fonts(self):
        """Load fonts for rendering.

        Note: WaveShare font should be downloaded on application startup via
        ensure_fonts() in main.py. This method just loads the font file.
        """
        from ..utils.fonts import FontManager

        # Get WaveShare font path (should already be downloaded)
        font_path = FontManager.get_font_path("WaveShare.ttc")

        # Fall back to Config.paths.font_path if FontManager returns invalid path
        if not os.path.exists(font_path):
            logger.warning(f"Font not found at {font_path}, using Config.paths.font_path")
            font_path = Config.paths.font_path

        try:
            self.font_xxs = ImageFont.truetype(font_path, 10)
            self.font_xs = ImageFont.truetype(font_path, 18)
            self.font_s = ImageFont.truetype(font_path, 24)
            self.font_m = ImageFont.truetype(font_path, 28)
            self.font_value = ImageFont.truetype(font_path, 32)
            self.font_date_big = ImageFont.truetype(font_path, 34)
            self.font_date_small = ImageFont.truetype(font_path, 24)
            self.font_cross = ImageFont.truetype(font_path, 20)
            self.font_l = ImageFont.truetype(font_path, 48)
            self.font_xl = ImageFont.truetype(font_path, 60)
            logger.debug(f"Loaded fonts from {font_path}")
        except (IOError, OSError) as e:
            logger.warning(f"Failed to load font {font_path}: {e}, using default font")
            # Fallback to PIL default font
            default_font = ImageFont.load_default()
            self.font_s = self.font_m = self.font_l = self.font_xl = default_font
            self.font_xs = self.font_value = self.font_date_big = self.font_date_small = (
                default_font
            )
            self.font_cross = default_font

    # Convenience methods that delegate to component renderers

    def draw_text(self, draw, x, y, text, font, fill=0, anchor=None):
        """Draw text (delegates to TextRenderer)."""
        self.text.draw_text(draw, x, y, text, font, fill, anchor)

    def draw_centered_text(self, draw, x, y, text, font, fill=0, align_y_center=True):
        """Draw centered text (delegates to TextRenderer)."""
        self.text.draw_centered_text(draw, x, y, text, font, fill, align_y_center)

    def draw_truncated_text(self, draw, x, y, text, font, max_width, fill=0):
        """Draw truncated text (delegates to TextRenderer)."""
        return self.text.draw_truncated_text(draw, x, y, text, font, max_width, fill)

    def draw_progress_ring(self, draw, x, y, radius, percent, thickness=5):
        """Draw progress ring (delegates to ShapeRenderer)."""
        self.shapes.draw_progress_ring(
            draw, x, y, radius, percent, thickness, use_grayscale=Config.hardware.use_grayscale
        )

    def draw_weather_icon(self, draw, x, y, icon_name, size=30):
        """Draw weather icon (delegates to WeatherIcons)."""
        from ..config import BASE_DIR

        icons_dir = BASE_DIR / "resources" / "icons" / "weather"
        return self.weather_icons.draw_weather_icon(draw, x, y, icon_name, size, icons_dir)

    def draw_full_screen_message(self, draw, width, height, title, message, icon_type=None):
        """Draw full screen message (delegates to HolidayIcons)."""
        self.holiday_icons.draw_full_screen_message(
            draw, width, height, title, message, icon_type, self.font_l, self.font_m
        )
