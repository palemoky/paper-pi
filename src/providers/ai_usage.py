"""AI usage providers for Claude and future model platforms."""

import logging
from pathlib import Path
from typing import Any

import httpx
import pendulum

from ..config import Config
from ..core.cache import cached

logger = logging.getLogger(__name__)

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CHATGPT_USAGE_PATH = "/wham/usage"
KIMI_USAGE_PATH = "/usages"


_INVALID_TOKEN_BY_PROVIDER: dict[str, str] = {}


def _fallback_usage(provider_name: str) -> dict[str, int | str]:
    """Return a stable fallback payload used when token is invalid/expired."""
    return {
        "provider_name": provider_name,
        "hourly_usage": "--",
        "weekly_usage": "--",
        "hourly_reset": "--",
        "weekly_reset": "--",
    }


def _read_secret_token(file_path: str) -> str:
    """Read token from a mounted secret file (first non-empty line)."""
    if not file_path:
        return ""

    try:
        raw = Path(file_path).read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"Cannot read secret token file '{file_path}': {e}")
        return ""

    for line in raw.splitlines():
        token = line.strip()
        if token:
            return token
    return ""


def _resolve_token(provider_name: str, file_path: str, env_token: str) -> tuple[str, bool]:
    """Resolve token by preferring mounted secret file over env var.

    Returns (token, is_configured). is_configured is True when a raw token exists
    in the file or env, even if that token is currently marked invalid.
    """
    raw = _read_secret_token(file_path) or (env_token or "").strip()
    if not raw:
        return "", False

    invalid_token = _INVALID_TOKEN_BY_PROVIDER.get(provider_name)
    if invalid_token and raw == invalid_token:
        return "", True

    return raw, True


def _mark_invalid_token(provider_name: str, token: str) -> None:
    """Remember invalid token and skip future requests until token changes."""
    if token:
        _INVALID_TOKEN_BY_PROVIDER[provider_name] = token


def _clear_invalid_token(provider_name: str, token: str) -> None:
    """Clear invalid marker once a request succeeds with current token."""
    if not token:
        return
    if _INVALID_TOKEN_BY_PROVIDER.get(provider_name) == token:
        _INVALID_TOKEN_BY_PROVIDER.pop(provider_name, None)


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
    token, is_configured = _resolve_token(
        "Claude",
        Config.api.claude_oauth_token_file,
        Config.api.claude_oauth_token,
    )
    if not token:
        return _fallback_usage("Claude") if is_configured else None

    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "Accept": "application/json",
    }

    try:
        res = await client.get(CLAUDE_USAGE_URL, headers=headers, timeout=10.0)
        res.raise_for_status()
        _clear_invalid_token("Claude", token)
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
    except httpx.HTTPStatusError as e:
        _mark_invalid_token("Claude", token)
        logger.warning(
            "Claude usage API returned non-200 (%s), waiting for refreshed token sync",
            e.response.status_code,
        )
        return _fallback_usage("Claude")
    except Exception as e:
        logger.warning(f"Claude usage API unavailable, fallback to '--': {e}")
        return _fallback_usage("Claude")


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
    token, is_configured = _resolve_token(
        "ChatGPT",
        Config.api.chatgpt_oauth_token_file,
        Config.api.chatgpt_oauth_token,
    )
    if not token:
        return _fallback_usage("ChatGPT") if is_configured else None

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
        _clear_invalid_token("ChatGPT", token)
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
    except httpx.HTTPStatusError as e:
        _mark_invalid_token("ChatGPT", token)
        logger.warning(
            "ChatGPT usage API returned non-200 (%s), waiting for refreshed token sync",
            e.response.status_code,
        )
        return _fallback_usage("ChatGPT")
    except Exception as e:
        logger.warning(f"ChatGPT usage API unavailable, fallback to '--': {e}")
        return _fallback_usage("ChatGPT")


@cached(ttl=300)  # Cache for 5 minutes
async def get_kimi_usage(client: httpx.AsyncClient) -> dict[str, int | str] | None:
    """Fetch Kimi Code usage from /usages endpoint."""
    api_key, is_configured = _resolve_token(
        "Kimi",
        Config.api.kimi_api_key_file,
        Config.api.kimi_api_key,
    )
    if not api_key:
        return _fallback_usage("Kimi") if is_configured else None

    base_url = (Config.api.kimi_base_url or "https://api.kimi.com/coding/v1").strip().rstrip("/")
    url = f"{base_url}{KIMI_USAGE_PATH}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "paper-pi",
        "Accept": "application/json",
    }

    try:
        res = await client.get(url, headers=headers, timeout=10.0)
        res.raise_for_status()
        _clear_invalid_token("Kimi", api_key)
        payload = res.json()
        if not isinstance(payload, dict):
            raise ValueError("Expected dict response from Kimi /usages")

        summary, limits = _parse_kimi_payload(payload)
        rows: list[dict[str, Any]] = []
        if summary:
            rows.append(summary)
        rows.extend(limits)
        rows = rows[:2]

        primary = rows[0] if rows else {"used_percent": 0, "reset_text": "--"}
        secondary = rows[1] if len(rows) > 1 else {"used_percent": 0, "reset_text": "--"}

        return {
            "provider_name": "Kimi",
            "hourly_usage": _parse_percent(primary.get("used_percent", 0)),
            "weekly_usage": _parse_percent(secondary.get("used_percent", 0)),
            "hourly_reset": str(primary.get("reset_text", "--")),
            "weekly_reset": str(secondary.get("reset_text", "--")),
        }
    except httpx.HTTPStatusError as e:
        _mark_invalid_token("Kimi", api_key)
        logger.warning(
            "Kimi usage API returned non-200 (%s), waiting for refreshed token sync",
            e.response.status_code,
        )
        return _fallback_usage("Kimi")
    except Exception as e:
        logger.warning(f"Kimi usage API unavailable, fallback to '--': {e}")
        return _fallback_usage("Kimi")


def _parse_kimi_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Parse Kimi /usages payload into summary and per-limit rows."""
    summary: dict[str, Any] | None = None
    limits: list[dict[str, Any]] = []

    usage = payload.get("usage")
    if isinstance(usage, dict):
        summary = _kimi_window_from_data(usage, default_label="Usage")

    raw_limits = payload.get("limits")
    if isinstance(raw_limits, list):
        for idx, item in enumerate(raw_limits):
            if not isinstance(item, dict):
                continue
            detail_raw = item.get("detail")
            detail = detail_raw if isinstance(detail_raw, dict) else item

            label = (
                item.get("name")
                or item.get("title")
                or detail.get("name")
                or detail.get("title")
                or f"Limit #{idx + 1}"
            )
            row = _kimi_window_from_data(detail, default_label=str(label))
            if row:
                limits.append(row)

    return summary, limits


def _kimi_window_from_data(data: dict[str, Any], default_label: str) -> dict[str, Any] | None:
    """Convert Kimi usage object to normalized row data."""
    limit = _kimi_to_int(data.get("limit"))
    used = _kimi_to_int(data.get("used"))
    if used is None:
        remaining = _kimi_to_int(data.get("remaining"))
        if remaining is not None and limit is not None:
            used = limit - remaining

    if used is None and limit is None:
        return None

    used_value = max(0, used or 0)
    if limit and limit > 0:
        used_percent = max(0, min(100, int((used_value / limit) * 100)))
    else:
        used_percent = 0

    reset_text = _kimi_reset_text(data) or "--"
    return {
        "label": str(data.get("name") or data.get("title") or default_label),
        "used_percent": used_percent,
        "reset_text": reset_text,
    }


def _kimi_to_int(value: Any) -> int | None:
    """Best-effort integer parser."""
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _kimi_reset_text(data: dict[str, Any]) -> str | None:
    """Parse reset hint fields from Kimi usage payload."""
    for key in ("reset_at", "resetAt", "reset_time", "resetTime"):
        value = data.get(key)
        if value:
            left = _format_window_reset_left({"resets_at": value})
            return left if left != "--" else None

    for key in ("reset_in", "resetIn", "ttl", "window"):
        seconds = _kimi_to_int(data.get(key))
        if seconds is None:
            continue
        return _format_seconds_left(seconds)

    return None


def _format_seconds_left(seconds: int) -> str:
    """Format seconds into compact `...` text."""
    if seconds <= 0:
        return "0m"

    days, rem = divmod(seconds, 24 * 3600)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days > 0:
        return f"{days}d"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}m"


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
    except TypeError, ValueError:
        return 0


def _format_window_reset_left(window: dict[str, Any]) -> str:
    """Return compact "..." text for a Claude usage window."""
    seconds = _extract_reset_seconds(window)
    if seconds is None:
        return "--"
    if seconds <= 0:
        return "0m"

    days, rem = divmod(seconds, 24 * 3600)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days > 0:
        return f"{days}d"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}m"


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
        except TypeError, ValueError:
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
                reset_at = reset_at.replace(tzinfo=pendulum.timezone("UTC"))
            reset_local = reset_at.in_timezone(local_tz)
            return max(0, int((reset_local - now_local).total_seconds()))
        except Exception:
            continue

    return None
