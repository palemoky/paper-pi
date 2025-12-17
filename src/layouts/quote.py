"""Quote layout for displaying famous quotes in elegant format.

Creates beautiful quote display with automatic text wrapping and decorative elements.
"""

import logging
import textwrap

from PIL import Image, ImageDraw, ImageFont

from ..renderer.dashboard import DashboardRenderer
from .utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class QuoteLayout:
    """Manages elegant quote layout for E-Ink display."""

    # Layout constants
    MARGIN_X = 60
    MARGIN_Y = 80
    QUOTE_FONT_SIZE_MAX = 40
    QUOTE_FONT_SIZE_MIN = 20
    QUOTE_FONT_SIZE_STEP = 2
    LINE_SPACING = 20
    QUOTE_GAP = 20  # Gap between quote marks and content
    AUTHOR_SECTION_HEIGHT = 120

    def __init__(self):
        """Initialize quote layout with renderer."""
        self.renderer = DashboardRenderer()
        self.layout = LayoutHelper(use_grayscale=False)

    def _get_text_width(self, draw: ImageDraw.ImageDraw, text: str, font) -> int:
        """Get the width of text in pixels.

        Args:
            draw: ImageDraw instance
            text: Text to measure
            font: Font to use for measurement

        Returns:
            Width of the text in pixels
        """
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return int(bbox[2] - bbox[0])
        except AttributeError:
            width, _ = draw.textsize(text, font=font)
            return width

    def _get_text_height(self, draw: ImageDraw.ImageDraw, text: str, font) -> int:
        """Get the height of text in pixels.

        Args:
            draw: ImageDraw instance
            text: Text to measure
            font: Font to use for measurement

        Returns:
            Height of the text in pixels
        """
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return int(bbox[3] - bbox[1])
        except AttributeError:
            _, height = draw.textsize(text, font=font)
            return height

    def create_quote_image(self, width: int, height: int, quote: dict) -> Image.Image:
        """Create elegant quote image with automatic text wrapping.

        Args:
            width: Display width in pixels
            height: Display height in pixels
            quote: Quote dictionary with content, author, source, type

        Returns:
            PIL Image object ready for E-Ink display
        """
        # Create canvas
        image = Image.new("1", (width, height), 1)  # White background
        draw = ImageDraw.Draw(image)

        if not quote:
            logger.warning("No quote data provided")
            return image

        content = quote.get("content", "")
        author = quote.get("author", "")
        source = quote.get("source", "")

        # Layout parameters (using class constants)
        content_width = width - 2 * self.MARGIN_X

        # Calculate available height for content
        max_content_height = height - (self.MARGIN_Y * 2) - 100

        # Dynamic font scaling
        quote_font_size = self.QUOTE_FONT_SIZE_MAX

        # Dynamic font scaling loop
        wrapped_lines = []
        total_content_height = 0

        while quote_font_size >= self.QUOTE_FONT_SIZE_MIN:
            # Wrap text with current font size
            wrapped_lines = self._wrap_text(content, quote_font_size, content_width)

            # Calculate total height
            total_content_height = len(wrapped_lines) * (quote_font_size + self.LINE_SPACING)

            if total_content_height <= max_content_height:
                break

            quote_font_size -= self.QUOTE_FONT_SIZE_STEP

        if quote_font_size < self.QUOTE_FONT_SIZE_MIN:
            logger.warning("Quote content too long even with minimum font size")
            quote_font_size = self.QUOTE_FONT_SIZE_MIN

        # Get quote mark height
        quote_mark_height = self._get_text_height(draw, "\u201c", self.renderer.font_xl)

        # Calculate total block height
        total_block_height = (
            quote_mark_height
            + self.QUOTE_GAP  # Opening quote + gap
            + total_content_height  # Content lines
            + self.QUOTE_GAP  # Gap before closing quote
            + self.AUTHOR_SECTION_HEIGHT  # Author section
        )

        # Center the entire block vertically
        block_start_y = (height - total_block_height) // 2
        block_start_y = max(block_start_y, self.MARGIN_Y // 2)  # Don't go too high

        # Draw opening quotation mark
        opening_quote = "\u201c"  # Left double quotation mark
        self.renderer.draw_text(
            draw,
            self.MARGIN_X - 10,
            block_start_y,
            opening_quote,
            self.renderer.font_xl,
        )

        # Content starts after opening quote
        start_y = block_start_y + quote_mark_height + self.QUOTE_GAP

        # Draw quote content
        current_y = start_y

        # Load font for current size
        try:
            font_path = self.renderer.font_path
            current_font = ImageFont.truetype(font_path, quote_font_size)
        except Exception:
            logger.warning("Failed to load dynamic font, using default")
            current_font = self.renderer.font_l

        for line in wrapped_lines:
            # Calculate text width for centering
            text_width = self._get_text_width(draw, line, current_font)

            self.renderer.draw_text(
                draw,
                (width - text_width) // 2,
                current_y,
                line,
                current_font,
            )
            current_y += quote_font_size + self.LINE_SPACING

        # Adjust current_y: remove the extra line_spacing added after last line
        last_line_top_y = current_y - self.LINE_SPACING
        content_bottom_y = last_line_top_y + quote_font_size  # Bottom of last text line

        # Draw closing quotation mark
        closing_quote = "\u201d"  # Right double quotation mark
        quote_width = self._get_text_width(draw, closing_quote, self.renderer.font_xl)

        # Use same gap as opening quote for symmetry
        closing_quote_y = content_bottom_y + self.QUOTE_GAP
        self.renderer.draw_text(
            draw,
            width - self.MARGIN_X - quote_width + 10,
            closing_quote_y,
            closing_quote,
            self.renderer.font_xl,
        )

        # Draw author and source with more breathing room
        author_y = closing_quote_y + quote_mark_height + 30
        if source:
            author_text = f"— {author}, {source}"
        else:
            author_text = f"— {author}"

        # Calculate text width for right alignment
        author_width = self._get_text_width(draw, author_text, self.renderer.font_value)

        self.renderer.draw_text(
            draw,
            width - self.MARGIN_X - author_width,
            author_y,
            author_text,
            self.renderer.font_value,
        )

        # Draw decorative line above author using LayoutHelper
        line_y = author_y - 20
        line_start_x = width - self.MARGIN_X - 200
        self.layout.draw_decorative_line(
            draw, line_start_x, line_y, 200, orientation="horizontal", line_width=2
        )

        # Draw subtle corner decorations using LayoutHelper
        self.layout.draw_corner_decorations(
            draw,
            width,
            height,
            corner_size=LayoutConstants.CORNER_SMALL,
            margin=LayoutConstants.MARGIN_MEDIUM,
            line_width=LayoutConstants.LINE_NORMAL,
        )

        logger.info(f"Created quote layout: {author} (font size: {quote_font_size})")
        return image

    def _wrap_text(self, text: str, font_size: int, max_width: int) -> list[str]:
        """Wrap text to fit within max width.

        Args:
            text: Text to wrap
            font_size: Font size in pixels
            max_width: Maximum width in pixels

        Returns:
            List of wrapped lines
        """
        # Estimate characters per line based on font size
        # This is approximate - actual width depends on font and characters
        avg_char_width = font_size * 0.6  # Rough estimate
        chars_per_line = int(max_width / avg_char_width)

        # Use textwrap for intelligent line breaking
        wrapped = textwrap.wrap(
            text,
            width=chars_per_line,
            break_long_words=False,
            break_on_hyphens=False,
        )

        return wrapped


# Suppress false positive lint warnings - all variables are actually used
# ruff: noqa: F841
