"""Unified layout helper for consistent positioning and styling across all layouts.

Provides standardized constants, column layout utilities, divider drawing methods,
and decorative element tools to eliminate code duplication.
"""

import logging

from PIL import ImageDraw

logger = logging.getLogger(__name__)


class LayoutConstants:
    """Standardized layout constants for consistent spacing and sizing."""

    # Standard margins
    MARGIN_TINY = 10
    MARGIN_SMALL = 20
    MARGIN_MEDIUM = 30
    MARGIN_LARGE = 40
    MARGIN_XLARGE = 60
    MARGIN_XXLARGE = 80

    # Standard spacing
    SPACING_TIGHT = 10
    SPACING_NORMAL = 20
    SPACING_LOOSE = 40
    SPACING_XLOOSE = 60

    # Line widths
    LINE_THIN = 1
    LINE_NORMAL = 2
    LINE_THICK = 3

    # Corner decoration sizes
    CORNER_SMALL = 20
    CORNER_MEDIUM = 30
    CORNER_LARGE = 40


class ColumnLayout:
    """Helper class for column-based layouts."""

    def __init__(self, width: int, num_cols: int, padding: int = 20):
        """Initialize column layout.

        Args:
            width: Total width available
            num_cols: Number of columns
            padding: Padding on left and right edges
        """
        self.width = width
        self.num_cols = num_cols
        self.padding = padding
        self.content_width = width - 2 * padding
        self.col_width = self.content_width / num_cols

    def get_column_center(self, col_index: int) -> int:
        """Get the center x-coordinate of a column.

        Args:
            col_index: Column index (0-based)

        Returns:
            X-coordinate of column center
        """
        return int(self.padding + (col_index * self.col_width) + (self.col_width / 2))

    def get_column_left(self, col_index: int) -> int:
        """Get the left x-coordinate of a column.

        Args:
            col_index: Column index (0-based)

        Returns:
            X-coordinate of column left edge
        """
        return int(self.padding + (col_index * self.col_width))

    def get_column_right(self, col_index: int) -> int:
        """Get the right x-coordinate of a column.

        Args:
            col_index: Column index (0-based)

        Returns:
            X-coordinate of column right edge
        """
        return int(self.padding + ((col_index + 1) * self.col_width))


class GridLayout:
    """Helper class for grid-based layouts."""

    def __init__(
        self, width: int, height: int, rows: int, cols: int, margin_x: int = 0, margin_y: int = 0
    ):
        """Initialize grid layout.

        Args:
            width: Total width available
            height: Total height available
            rows: Number of rows
            cols: Number of columns
            margin_x: Horizontal margin
            margin_y: Vertical margin
        """
        self.width = width
        self.height = height
        self.rows = rows
        self.cols = cols
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.content_width = width - 2 * margin_x
        self.content_height = height - 2 * margin_y
        self.cell_width = self.content_width / cols
        self.cell_height = self.content_height / rows

    def get_cell_center(self, row: int, col: int) -> tuple[int, int]:
        """Get the center coordinates of a grid cell.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            Tuple of (x, y) coordinates
        """
        x = int(self.margin_x + (col * self.cell_width) + (self.cell_width / 2))
        y = int(self.margin_y + (row * self.cell_height) + (self.cell_height / 2))
        return (x, y)

    def get_cell_bounds(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Get the bounding box of a grid cell.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        left = int(self.margin_x + (col * self.cell_width))
        top = int(self.margin_y + (row * self.cell_height))
        right = int(self.margin_x + ((col + 1) * self.cell_width))
        bottom = int(self.margin_y + ((row + 1) * self.cell_height))
        return (left, top, right, bottom)


class LayoutHelper:
    """Unified layout helper providing common drawing utilities."""

    def __init__(self, use_grayscale: bool = False):
        """Initialize layout helper.

        Args:
            use_grayscale: Whether to use grayscale colors
        """
        self.use_grayscale = use_grayscale
        self.COLOR_BLACK = 0
        self.COLOR_DARK_GRAY = 128 if use_grayscale else 0
        self.COLOR_LIGHT_GRAY = 192 if use_grayscale else 0

    def draw_horizontal_divider(
        self,
        draw: ImageDraw.ImageDraw,
        y: int,
        start_x: int | None = None,
        end_x: int | None = None,
        width: int | None = None,
        color: int | None = None,
        line_width: int = LayoutConstants.LINE_NORMAL,
    ) -> None:
        """Draw a horizontal divider line.

        Args:
            draw: PIL ImageDraw object
            y: Y-coordinate of the line
            start_x: Starting x-coordinate (default: MARGIN_MEDIUM from left)
            end_x: Ending x-coordinate (default: MARGIN_MEDIUM from right)
            width: Canvas width (required if start_x or end_x not provided)
            color: Line color (default: dark gray if grayscale, else black)
            line_width: Line width in pixels
        """
        if color is None:
            color = self.COLOR_DARK_GRAY

        if start_x is None:
            if width is None:
                raise ValueError("Either start_x or width must be provided")
            start_x = LayoutConstants.MARGIN_MEDIUM

        if end_x is None:
            if width is None:
                raise ValueError("Either end_x or width must be provided")
            end_x = width - LayoutConstants.MARGIN_MEDIUM

        draw.line((start_x, y, end_x, y), fill=color, width=line_width)

    def draw_vertical_divider(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        start_y: int,
        end_y: int,
        color: int | None = None,
        line_width: int = LayoutConstants.LINE_THIN,
    ) -> None:
        """Draw a vertical divider line.

        Args:
            draw: PIL ImageDraw object
            x: X-coordinate of the line
            start_y: Starting y-coordinate
            end_y: Ending y-coordinate
            color: Line color (default: black)
            line_width: Line width in pixels
        """
        if color is None:
            color = self.COLOR_BLACK

        draw.line((x, start_y, x, end_y), fill=color, width=line_width)

    def draw_cross_divider(
        self,
        draw: ImageDraw.ImageDraw,
        center_x: int,
        center_y: int,
        h_length: int,
        v_length: int,
        color: int | None = None,
        line_width: int = LayoutConstants.LINE_THIN,
    ) -> None:
        """Draw a cross-shaped divider (horizontal + vertical lines intersecting).

        Args:
            draw: PIL ImageDraw object
            center_x: X-coordinate of intersection
            center_y: Y-coordinate of intersection
            h_length: Total horizontal line length
            v_length: Total vertical line length
            color: Line color (default: black)
            line_width: Line width in pixels
        """
        if color is None:
            color = self.COLOR_BLACK

        # Horizontal line
        h_half = h_length // 2
        draw.line(
            (center_x - h_half, center_y, center_x + h_half, center_y),
            fill=color,
            width=line_width,
        )

        # Vertical line
        v_half = v_length // 2
        draw.line(
            (center_x, center_y - v_half, center_x, center_y + v_half),
            fill=color,
            width=line_width,
        )

    def draw_corner_decorations(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        corner_size: int = LayoutConstants.CORNER_MEDIUM,
        margin: int = LayoutConstants.MARGIN_SMALL,
        line_width: int = LayoutConstants.LINE_NORMAL,
        color: int | None = None,
        corners: str = "all",
    ) -> None:
        """Draw decorative corner elements.

        Args:
            draw: PIL ImageDraw object
            width: Canvas width
            height: Canvas height
            corner_size: Size of corner decorations
            margin: Distance from edges
            line_width: Line width in pixels
            color: Line color (default: black)
            corners: Which corners to draw ("all", "top", "bottom", "left", "right", or combination like "tl,br")
        """
        if color is None:
            color = self.COLOR_BLACK

        # Parse corners parameter
        draw_tl = "all" in corners or "top" in corners or "left" in corners or "tl" in corners
        draw_tr = "all" in corners or "top" in corners or "right" in corners or "tr" in corners
        draw_bl = "all" in corners or "bottom" in corners or "left" in corners or "bl" in corners
        draw_br = "all" in corners or "bottom" in corners or "right" in corners or "br" in corners

        # Top-left corner
        if draw_tl:
            draw.line(
                [(margin, margin), (margin + corner_size, margin)],
                fill=color,
                width=line_width,
            )
            draw.line(
                [(margin, margin), (margin, margin + corner_size)],
                fill=color,
                width=line_width,
            )

        # Top-right corner
        if draw_tr:
            draw.line(
                [(width - margin - corner_size, margin), (width - margin, margin)],
                fill=color,
                width=line_width,
            )
            draw.line(
                [(width - margin, margin), (width - margin, margin + corner_size)],
                fill=color,
                width=line_width,
            )

        # Bottom-left corner
        if draw_bl:
            draw.line(
                [(margin, height - margin), (margin + corner_size, height - margin)],
                fill=color,
                width=line_width,
            )
            draw.line(
                [(margin, height - margin - corner_size), (margin, height - margin)],
                fill=color,
                width=line_width,
            )

        # Bottom-right corner
        if draw_br:
            draw.line(
                [
                    (width - margin - corner_size, height - margin),
                    (width - margin, height - margin),
                ],
                fill=color,
                width=line_width,
            )
            draw.line(
                [
                    (width - margin, height - margin - corner_size),
                    (width - margin, height - margin),
                ],
                fill=color,
                width=line_width,
            )

    def draw_decorative_line(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        length: int,
        orientation: str = "horizontal",
        color: int | None = None,
        line_width: int = LayoutConstants.LINE_NORMAL,
    ) -> None:
        """Draw a decorative line.

        Args:
            draw: PIL ImageDraw object
            x: Starting x-coordinate
            y: Starting y-coordinate
            length: Line length
            orientation: "horizontal" or "vertical"
            color: Line color (default: black)
            line_width: Line width in pixels
        """
        if color is None:
            color = self.COLOR_BLACK

        if orientation == "horizontal":
            draw.line([(x, y), (x + length, y)], fill=color, width=line_width)
        else:  # vertical
            draw.line([(x, y), (x, y + length)], fill=color, width=line_width)

    def create_column_layout(
        self, width: int, num_cols: int, padding: int = LayoutConstants.MARGIN_SMALL
    ) -> ColumnLayout:
        """Create a column layout helper.

        Args:
            width: Total width available
            num_cols: Number of columns
            padding: Padding on left and right edges

        Returns:
            ColumnLayout instance
        """
        return ColumnLayout(width, num_cols, padding)

    def create_grid_layout(
        self,
        width: int,
        height: int,
        rows: int,
        cols: int,
        margin_x: int = 0,
        margin_y: int = 0,
    ) -> GridLayout:
        """Create a grid layout helper.

        Args:
            width: Total width available
            height: Total height available
            rows: Number of rows
            cols: Number of columns
            margin_x: Horizontal margin
            margin_y: Vertical margin

        Returns:
            GridLayout instance
        """
        return GridLayout(width, height, rows, cols, margin_x, margin_y)
