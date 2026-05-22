"""AI usage providers for Claude and future model platforms."""

import logging
from typing import Any

import httpx
import pendulum

from ..config import Config
from ..core.cache import cached

logger = logging.getLogger(__name__)

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CHATGPT_USAGE_PATH = "/wham/usage"


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
            "provider_name": "Claude",
            "hourly_usage": hourly_usage,
            "weekly_usage": weekly_usage,
            "hourly_reset": _format_window_reset_left(hourly_window),
            "weekly_reset": _format_window_reset_left(seven_day_window),
        }
    except Exception as e:
        logger.warning(f"Claude usage API unavailable, fallback to 0% usage table: {e}")
        return {
            "provider_name": "Claude",
            "hourly_usage": 0,
            "weekly_usage": 0,
            "hourly_reset": "--",
            "weekly_reset": "--",
        }


@cached(ttl=300)  # Cache for 5 minutes
async def get_chatgpt_usage(client: httpx.AsyncClient) -> dict[str, int | str] | None:
    """Fetch ChatGPT/Codex usage from /wham/usage endpoint.

    Returns:
        dict with keys {
            "provider_name": str,
            "hourly_usage": int,
            "weekly_usage": int,
            "hourly_reset": str,
            "weekly_reset": str,
        } or None when token is not configured.
    """
    token = Config.api.chatgpt_oauth_token.strip()
    if not token:
        return None

    base_url = _normalize_chatgpt_base_url(Config.api.chatgpt_base_url)
    url = f"{base_url}{CHATGPT_USAGE_PATH}"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "paper-pi",
        "Accept": "application/json",
    }
    account_id = Config.api.chatgpt_account_id.strip()
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id

    try:
        res = await client.get(url, headers=headers, timeout=10.0)
        res.raise_for_status()
        payload: dict[str, Any] = res.json()

        primary, secondary = _extract_chatgpt_windows(payload)
        hourly_usage = _parse_percent(primary.get("used_percent", primary.get("usage_percent", 0)))

        weekly_usage = 0
        if secondary:
            weekly_usage = _parse_percent(
                secondary.get("used_percent", secondary.get("usage_percent", 0))
            )

        return {
            "provider_name": "ChatGPT",
            "hourly_usage": hourly_usage,
            "weekly_usage": weekly_usage,
            "hourly_reset": _format_window_reset_left(primary),
            "weekly_reset": _format_window_reset_left(secondary or {}),
        }
    except Exception as e:
        logger.warning(f"ChatGPT usage API unavailable, fallback to 0% usage table: {e}")
        return {
            "provider_name": "ChatGPT",
            "hourly_usage": 0,
            "weekly_usage": 0,
            "hourly_reset": "--",
            "weekly_reset": "--",
        }


def _normalize_chatgpt_base_url(url: str) -> str:
    """Normalize ChatGPT base URL, ensuring /backend-api suffix when needed."""
    trimmed = (url or "").strip().rstrip("/")
    if not trimmed:
        return "https://chatgpt.com/backend-api"

    if (
        trimmed.startswith("https://chatgpt.com") or trimmed.startswith("https://chat.openai.com")
    ) and "/backend-api" not in trimmed:
        return f"{trimmed}/backend-api"
    return trimmed


def _extract_chatgpt_windows(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Extract primary/secondary windows from /wham/usage payload variants."""
    usage = payload.get("usage")
    if isinstance(usage, dict):
        primary = usage.get("primary")
        secondary = usage.get("secondary")
        if isinstance(primary, dict):
            return _normalize_chatgpt_window(primary), _normalize_optional_window(secondary)

    rate_limit = payload.get("rate_limit")
    if isinstance(rate_limit, dict):
        primary = _normalize_optional_window(rate_limit.get("primary_window")) or {
            "used_percent": 0
        }
        secondary = _normalize_optional_window(rate_limit.get("secondary_window"))
        return primary, secondary

    rate_limits = payload.get("rate_limits")
    if isinstance(rate_limits, list) and rate_limits:
        primary = _normalize_chatgpt_window(rate_limits[0])
        secondary = _normalize_chatgpt_window(rate_limits[1]) if len(rate_limits) > 1 else None
        return primary, secondary

    return _normalize_chatgpt_window(payload), None


def _normalize_optional_window(window: Any) -> dict[str, Any] | None:
    """Normalize chatgpt window when value is a mapping."""
    if not isinstance(window, dict):
        return None
    return _normalize_chatgpt_window(window)


def _normalize_chatgpt_window(window: dict[str, Any]) -> dict[str, Any]:
    """Normalize window fields from /wham/usage payload."""
    reset_at = window.get("resets_at", window.get("reset_at"))
    if isinstance(reset_at, (int, float)):
        reset_at = pendulum.from_timestamp(reset_at, tz="UTC").to_iso8601_string()

    return {
        "used_percent": window.get("used_percent", window.get("usage_percent", 0)),
        "resets_at": reset_at,
    }


def _parse_percent(value: Any) -> int:
    """Parse and clamp usage percent to 0-100 integer."""
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 0


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
            if isinstance(raw, (int, float)):
                reset_at = pendulum.from_timestamp(raw, tz="UTC")
            else:
                reset_at = pendulum.parse(str(raw))
            if reset_at.timezone is None:
                reset_at = reset_at.replace(tz="UTC")
            reset_local = reset_at.in_timezone(local_tz)
            return max(0, int((reset_local - now_local).total_seconds()))
        except Exception:
            continue

    return None
