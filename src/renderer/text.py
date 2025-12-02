"""Text rendering utilities.

Provides text drawing functions with various alignment and truncation options.
"""

from PIL import ImageDraw, ImageFont


class TextRenderer:
    """Handles text rendering operations."""

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: int | str = 0,
        anchor: str = None,
    ):
        """Draw text at specified coordinates."""
        draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

    def draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: int | str = 0,
        align_y_center: bool = True,
    ):
        """Draw centered text at specified coordinates."""
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(text, font=font)

        y_offset = (h // 2 + 3) if align_y_center else 0
        draw.text((x - w // 2, y - y_offset), text, font=font, fill=fill)

    def draw_truncated_text(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        fill: int | str = 0,
    ) -> tuple[float, float, float, float] | None:
        """Draw text with truncation if it exceeds max width.

        Returns:
            Bounding box (x1, y1, x2, y2) of the drawn text, or None if no text drawn
        """

        def get_w(t):
            try:
                return draw.textlength(t, font=font)
            except AttributeError:
                w, _ = draw.textsize(t, font=font)
                return w

        if get_w(text) <= max_width:
            draw.text((x, y), text, font=font, fill=fill)
            bbox = draw.textbbox((x, y), text, font=font)
            return bbox

        ellipsis = "..."
        for i in range(len(text), 0, -1):
            temp = text[:i]
            if get_w(temp) + get_w(ellipsis) <= max_width:
                final_text = temp + ellipsis
                draw.text((x, y), final_text, font=font, fill=fill)
                bbox = draw.textbbox((x, y), final_text, font=font)
                return bbox

        return None
