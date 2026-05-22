"""AI usage providers for Claude and future model platforms."""

import logging
from typing import Any

import httpx
import pendulum

from ..config import Config
from ..core.cache import cached

logger = logging.getLogger(__name__)

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


@cached(ttl=300)  # Cache for 5 minutes
async def get_claude_usage(client: httpx.AsyncClient) -> dict[str, int | str] | None:
    """Fetch Claude Code usage and reset windows for 5h and weekly periods.

    Returns:
        dict with keys {
            "hourly_usage": int,
            "weekly_usage": int,
            "hourly_reset": str,
            "weekly_reset": str,
        } or None when token is not configured.
    """
    token = Config.api.claude_oauth_token.strip()
    if not token:
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "Accept": "application/json",
    }

    try:
        res = await client.get(CLAUDE_USAGE_URL, headers=headers, timeout=10.0)
        res.raise_for_status()
        payload: dict[str, Any] = res.json()

        hourly_window = payload.get("five_hour") or payload.get("hourly") or {}
        seven_day_window = payload.get("seven_day") or {}

        hourly_usage_raw = hourly_window.get("utilization", 0)
        weekly_usage_raw = seven_day_window.get("utilization", 0)

        hourly_usage = max(0, min(100, int(float(hourly_usage_raw))))
        weekly_usage = max(0, min(100, int(float(weekly_usage_raw))))
        return {
            "hourly_usage": hourly_usage,
            "weekly_usage": weekly_usage,
            "hourly_reset": _format_window_reset_left(hourly_window),
            "weekly_reset": _format_window_reset_left(seven_day_window),
        }
    except Exception as e:
        logger.warning(f"Claude usage API unavailable, fallback to 0% usage table: {e}")
        return {
            "hourly_usage": 0,
            "weekly_usage": 0,
            "hourly_reset": "--",
            "weekly_reset": "--",
        }


def _format_window_reset_left(window: dict[str, Any]) -> str:
    """Return compact "Left ..." text for a Claude usage window."""
    seconds = _extract_reset_seconds(window)
    if seconds is None:
        return "--"
    if seconds <= 0:
        return "0m"

    days, rem = divmod(seconds, 24 * 3600)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days > 0:
        return f"Left {days}d {hours}h"
    if hours > 0:
        return f"Left {hours}h"
    return f"Left {minutes}m"


def _extract_reset_seconds(window: dict[str, Any]) -> int | None:
    """Extract remaining reset seconds from known API fields."""
    remaining_keys = (
        "remaining_seconds",
        "reset_in_seconds",
        "reset_after_seconds",
        "time_remaining_seconds",
    )
    for key in remaining_keys:
        raw = window.get(key)
        if raw is None:
            continue
        try:
            return max(0, int(float(raw)))
        except (TypeError, ValueError):
            continue

    reset_at_keys = ("reset_at", "resets_at", "resetAt", "resetsAt")
    for key in reset_at_keys:
        raw = window.get(key)
        if not raw:
            continue
        try:
            local_tz = Config.hardware.timezone
            now_local = pendulum.now(local_tz)
            reset_at = pendulum.parse(str(raw))
            if reset_at.timezone is None:
                reset_at = reset_at.replace(tz="UTC")
            reset_local = reset_at.in_timezone(local_tz)
            return max(0, int((reset_local - now_local).total_seconds()))
        except Exception:
            continue

    return None
