"""Time-related utilities for the E-Ink dashboard application.

This module provides utilities for handling quiet hours and time-based logic.
"""

import logging

import pendulum

logger = logging.getLogger(__name__)


class QuietHours:
    """Manages quiet hours functionality.

    Quiet hours prevent display updates during specified time periods,
    typically used to avoid disturbing sleep or saving power.

    Example:
        >>> quiet = QuietHours(start_hour=1, end_hour=6, timezone="Asia/Shanghai")
        >>> is_quiet, sleep_seconds = quiet.check()
        >>> if is_quiet:
        >>>     await asyncio.sleep(sleep_seconds)
    """

    def __init__(self, start_hour: int, end_hour: int, timezone: str):
        """Initialize quiet hours.

        Args:
            start_hour: Start hour (0-23)
            end_hour: End hour (0-23)
            timezone: IANA timezone name
        """
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.timezone = timezone

    def check(self, now: pendulum.DateTime | None = None) -> tuple[bool, int]:
        """Check if current time is within quiet hours.

        Args:
            now: Current time (defaults to now in configured timezone)

        Returns:
            Tuple of (is_quiet: bool, sleep_seconds: int)
            - is_quiet: True if currently in quiet hours
            - sleep_seconds: Seconds until quiet hours end (0 if not quiet)
        """
        if now is None:
            now = pendulum.now(self.timezone)

        # Build today's start and end time points
        start_time = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=self.end_hour, minute=0, second=0, microsecond=0)

        # Handle cross-day scenarios (e.g., 23:00 to 06:00)
        if self.start_hour > self.end_hour:
            if now.hour >= self.start_hour:
                # It's evening, end time is tomorrow
                end_time = end_time.add(days=1)
            elif now.hour < self.end_hour:
                # It's early morning, start time was yesterday
                start_time = start_time.subtract(days=1)

        # Check if within range
        if start_time <= now < end_time:
            sleep_seconds = (end_time - now).total_seconds()
            # Ensure at least 1 second sleep to avoid busy-wait at boundary
            return True, max(1, int(sleep_seconds))

        return False, 0

    def __repr__(self) -> str:
        return f"QuietHours({self.start_hour:02d}:00-{self.end_hour:02d}:00, {self.timezone})"
