"""Quote layout for displaying famous quotes in elegant format.

Creates beautiful quote display with automatic text wrapping and decorative elements.
"""

import logging
import textwrap

from PIL import Image, ImageDraw

from ..renderer.dashboard import DashboardRenderer
from .utils.layout_helper import LayoutConstants, LayoutHelper

logger = logging.getLogger(__name__)


class QuoteLayout:
    """Manages elegant quote layout for E-Ink display."""

    def __init__(self):
        """Initialize quote layout with renderer."""
        self.renderer = DashboardRenderer()
        self.layout = LayoutHelper(use_grayscale=False)

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

        # Layout parameters
        margin_x = 60
        margin_y = 80
        content_width = width - 2 * margin_x

        # Calculate available height for content (excluding margins, author, and decorations)
        # Total height = margin_y (top) + content + line_spacing + author_height + margin_y (bottom)
        # We reserve space for author/source (~80px) and margins
        max_content_height = height - (margin_y * 2) - 100

        # Font sizes
        quote_font_size = 40
        min_font_size = 20
        line_spacing = 20

        # Dynamic font scaling loop
        wrapped_lines = []
        total_content_height = 0

        while quote_font_size >= min_font_size:
            # Wrap text with current font size
            wrapped_lines = self._wrap_text(content, quote_font_size, content_width)

            # Calculate total height
            total_content_height = len(wrapped_lines) * (quote_font_size + line_spacing)

            if total_content_height <= max_content_height:
                break

            quote_font_size -= 2

        if quote_font_size < min_font_size:
            logger.warning("Quote content too long even with minimum font size")
            quote_font_size = min_font_size

        # Draw opening quotation mark (no anchor for special Unicode chars)
        opening_quote = "\u201c"  # Left double quotation mark
        self.renderer.draw_text(
            draw,
            margin_x - 10,
            margin_y - 20,
            opening_quote,
            self.renderer.font_xl,
        )

        # Center vertically
        # Recalculate start_y based on actual content height
        start_y = (height - total_content_height) // 2

        # Ensure we don't start too high (overlapping with top margin/quote mark)
        start_y = max(start_y, margin_y)

        # Draw quote content
        current_y = start_y

        # Load font for current size
        try:
            from PIL import ImageFont

            font_path = self.renderer.font_path
            current_font = ImageFont.truetype(font_path, quote_font_size)
        except Exception:
            logger.warning("Failed to load dynamic font, using default")
            current_font = self.renderer.font_l

        for line in wrapped_lines:
            # Calculate text width for centering
            try:
                bbox = draw.textbbox((0, 0), line, font=current_font)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                text_width, _ = draw.textsize(line, font=current_font)

            self.renderer.draw_text(
                draw,
                (width - text_width) // 2,
                current_y,
                line,
                current_font,
            )
            current_y += quote_font_size + line_spacing

        # Draw closing quotation mark (no anchor for special Unicode chars)
        # Position at right side
        closing_quote = "\u201d"  # Right double quotation mark
        try:
            bbox = draw.textbbox((0, 0), closing_quote, font=self.renderer.font_xl)
            quote_width = bbox[2] - bbox[0]
        except AttributeError:
            quote_width, _ = draw.textsize(closing_quote, font=self.renderer.font_xl)

        self.renderer.draw_text(
            draw,
            width - margin_x - quote_width + 10,
            current_y - line_spacing,
            closing_quote,
            self.renderer.font_xl,
        )

        # Draw author and source
        author_y = current_y + 40  # noqa: F821
        if source:
            author_text = f"— {author}, {source}"
        else:
            author_text = f"— {author}"

        # Calculate text width for right alignment
        try:
            bbox = draw.textbbox((0, 0), author_text, font=self.renderer.font_value)
            author_width = bbox[2] - bbox[0]
        except AttributeError:
            author_width, _ = draw.textsize(author_text, font=self.renderer.font_value)

        self.renderer.draw_text(
            draw,
            width - margin_x - author_width,
            author_y,
            author_text,
            self.renderer.font_value,
        )

        # Draw decorative line above author using LayoutHelper
        line_y = author_y - 20
        line_start_x = width - margin_x - 200
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
