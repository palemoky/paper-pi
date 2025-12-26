"""HackerNews pagination background task.

This module contains the background task for rotating through HackerNews pages.
"""

import asyncio
import logging

from PIL import Image, ImageDraw

from src.config import Config
from src.layouts import DashboardLayout

logger = logging.getLogger(__name__)

# HackerNews region coordinates (for partial refresh)
HN_REGION = {
    "x": 0,
    "y": 115,  # LIST_HEADER_Y
    "w": 800,  # Full width
    "h": 250,  # From LIST_HEADER_Y to LINE_BOTTOM_Y
}

# Global lock to prevent concurrent display refreshes
_refresh_lock = asyncio.Lock()


async def hackernews_pagination_task(
    stop_event: asyncio.Event,
    epd,
    layout: DashboardLayout,
):
    """Independent async task for HackerNews page rotation.

    Args:
        stop_event: Event to signal task should stop
        epd: E-Paper Display driver instance
        layout: DashboardLayout instance
    """
    import httpx

    try:
        logger.info("🔄 Starting HackerNews pagination task")

        while not stop_event.is_set():
            # Wait for page duration or stop signal
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=Config.display.hackernews_page_seconds
                )
                # If we got here, stop_event was set
                break
            except asyncio.TimeoutError:
                # Timeout is normal - time to advance page
                pass

            # Check if in quiet hours before refreshing
            from src.core.time_utils import QuietHours

            quiet = QuietHours(
                Config.hardware.quiet_start_hour,
                Config.hardware.quiet_end_hour,
                Config.hardware.timezone,
            )
            is_quiet, _ = quiet.check()
            if is_quiet:
                logger.debug("⏸️  Skipping HN partial refresh (quiet hours)")
                continue

            # Fetch next page using on-demand HTTP connection
            from src.providers.hackernews import get_hackernews

            async with httpx.AsyncClient() as client:
                hn_data = await get_hackernews(client, advance_page=True)
            logger.info(
                f"📰 HN Page {hn_data.get('page', 1)}/{hn_data.get('total_pages', 1)} "
                f"({hn_data.get('start_idx', 1)}~{hn_data.get('end_idx', 0)})"
            )

            # Update layout data
            layout._current_hackernews = hn_data

            # Acquire lock to prevent concurrent refreshes
            async with _refresh_lock:
                # Create FULL-SIZE image (EPD requires full image for partial refresh)
                # Partial refresh usually requires 1-bit B/W image
                image_mode = "1"
                full_img = Image.new(image_mode, (epd.width, epd.height), 255)
                full_draw = ImageDraw.Draw(full_img)

                # Draw HN section at the correct position
                layout._draw_hackernews(full_draw, epd.width)

                # Partial refresh - EPD will only update the specified region
                try:
                    # Need to call init_part before partial refresh
                    if hasattr(epd, "init_part"):
                        epd.init_part()

                    buffer = epd.getbuffer(full_img)

                    # Log the refresh region for debugging
                    logger.debug(
                        f"Partial refresh region: x={HN_REGION['x']}, y={HN_REGION['y']}, "
                        f"x_end={HN_REGION['x'] + HN_REGION['w']}, y_end={HN_REGION['y'] + HN_REGION['h']}"
                    )

                    epd.display_partial_buffer(
                        buffer,
                        HN_REGION["x"],
                        HN_REGION["y"],
                        HN_REGION["x"] + HN_REGION["w"],
                        HN_REGION["y"] + HN_REGION["h"],
                    )
                    logger.debug("✅ HN partial refresh complete")
                except Exception as e:
                    logger.error(f"Failed to perform partial refresh: {e}")

    except asyncio.CancelledError:
        logger.info("🛑 HackerNews pagination task cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in HackerNews pagination task: {e}")
    finally:
        logger.info("👋 HackerNews pagination task stopped")
