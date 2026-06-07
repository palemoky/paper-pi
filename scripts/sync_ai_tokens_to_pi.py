#!/usr/bin/env python3
"""Sync macOS AI tokens to Raspberry Pi.

Daemon-style script for macOS that manages OAuth tokens for Claude Code,
ChatGPT (Codex), and Kimi, then syncs them to a Raspberry Pi over SSH.

Claude token lifecycle (modeled after codex-island UsageFetcher.refresh):
  1. Read credentials from macOS Keychain (accessToken, refreshToken, expiresAt)
  2. If accessToken expires within EARLY_REFRESH_SEC, use refreshToken to call
     platform.claude.com/v1/oauth/token
  3. Write new credentials (accessToken + rotated refreshToken) back to Keychain
  4. Sync fresh accessToken to Pi

Token sources (macOS):
  Claude  — macOS Keychain "Claude Code-credentials"
            (falls back to ~/.claude/.credentials.json if Keychain unavailable)
  ChatGPT — ~/.codex/auth.json → .tokens.access_token
  Kimi    — ~/.kimi/config.toml → api_key

Usage:
  # One-shot (reads, refreshes if needed, syncs, exits):
  python3 scripts/sync_ai_tokens_to_pi.py

  # Daemon mode (keeps running, smart sleep):
  python3 scripts/sync_ai_tokens_to_pi.py --daemon
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── Configuration ────────────────────────────────────────────────────────────

CLAUDE_OAUTH_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
# 通过命令 strings $(realpath $(which claude)) | grep -oE '.{50}CLIENT_ID:"[0-9a-f-]{36}".{100}' 从客户端提取两个ID，一个是local，另一个是prod，需要使用prod的ID
CLAUDE_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CLAUDE_KEYCHAIN_SERVICE = "Claude Code-credentials"
# Claude Code 默认把凭证存进 Keychain，Keychain 不可用时回退到此文件
# （两者保存同一份 {"claudeAiOauth": {...}} JSON）
CLAUDE_CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"

CODEX_AUTH_FILE = Path.home() / ".codex" / "auth.json"
KIMI_CONFIG_FILE = Path.home() / ".kimi" / "config.toml"

# ── Logging ──────────────────────────────────────────────────────────────────

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file: str) -> None:
    """Configure dual logging to console + file."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
        handlers=handlers,
    )


log = logging.getLogger("sync_tokens")


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ClaudeCredentials:
    """Parsed Claude OAuth credentials from macOS Keychain."""

    access_token: str
    refresh_token: str
    expires_epoch: int  # seconds
    raw_json: dict  # full credentials JSON, for preserving fields on write-back
    source: str = "keychain"  # "keychain" or "file" — where these were read from


@dataclass
class SyncState:
    """Track last synced values to avoid redundant SSH calls."""

    last_claude_token: str = ""
    last_chatgpt_token: str = ""
    last_kimi_key: str = ""
    claude_expires_epoch: int = 0


@dataclass
class Config:
    """Runtime configuration from env vars and CLI args."""

    pi_target: str = field(default_factory=lambda: os.getenv("PI_TARGET", "pi"))
    pi_secrets_dir: str = field(
        default_factory=lambda: os.getenv("PI_SECRETS_DIR", "/home/pi/paper-pi/secrets")
    )
    pi_ssh_opts: str = field(default_factory=lambda: os.getenv("PI_SSH_OPTS", ""))
    poll_interval: int = field(default_factory=lambda: int(os.getenv("POLL_INTERVAL", "3600")))
    early_refresh_sec: int = field(
        default_factory=lambda: int(os.getenv("EARLY_REFRESH_SEC", "300"))
    )
    log_file: str = field(default_factory=lambda: os.getenv("SYNC_LOG", "/tmp/sync_ai_tokens.log"))
    daemon: bool = False


# ── macOS Keychain ───────────────────────────────────────────────────────────


def _run_security(*args: str, input_data: str | None = None) -> str | None:
    """Run a macOS `security` command, return stdout or None on failure."""
    try:
        result = subprocess.run(
            ["security", *args],
            capture_output=True,
            text=True,
            input=input_data,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired, FileNotFoundError:
        return None


def _parse_claude_json(raw: str, *, source: str) -> ClaudeCredentials | None:
    """Parse a Claude credentials JSON blob (same shape in Keychain and file)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Claude credentials (%s) are not valid JSON", source)
        return None

    oauth = data.get("claudeAiOauth") or {}
    access_token = oauth.get("accessToken", "")
    if not access_token:
        return None

    return ClaudeCredentials(
        access_token=access_token,
        refresh_token=oauth.get("refreshToken", ""),
        # expiresAt is epoch milliseconds
        expires_epoch=_parse_expiry(oauth.get("expiresAt", 0)),
        raw_json=data,
        source=source,
    )


def _read_claude_file() -> ClaudeCredentials | None:
    """Read Claude credentials from ~/.claude/.credentials.json."""
    if not CLAUDE_CREDENTIALS_FILE.is_file():
        return None
    try:
        raw = CLAUDE_CREDENTIALS_FILE.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("Failed to read %s: %s", CLAUDE_CREDENTIALS_FILE, e)
        return None
    return _parse_claude_json(raw, source="file")


def read_claude_credentials() -> ClaudeCredentials | None:
    """Read Claude credentials, preferring the Keychain and falling back to file.

    Claude Code stores credentials in the macOS Keychain by default, but falls
    back to ~/.claude/.credentials.json when the Keychain is unavailable.
    """
    raw = _run_security("find-generic-password", "-s", CLAUDE_KEYCHAIN_SERVICE, "-w")
    if raw:
        creds = _parse_claude_json(raw, source="keychain")
        if creds:
            return creds
        log.warning("Keychain entry unusable, falling back to %s", CLAUDE_CREDENTIALS_FILE)

    return _read_claude_file()


def _write_claude_keychain(json_str: str) -> bool:
    """Write the credentials JSON into the macOS Keychain."""
    # Get the account name from existing entry
    acct_output = _run_security("find-generic-password", "-s", CLAUDE_KEYCHAIN_SERVICE)
    account = os.getenv("USER", "")
    if acct_output:
        for line in acct_output.splitlines():
            if '"acct"' in line:
                parts = line.split('="')
                if len(parts) >= 2:
                    account = parts[-1].rstrip('"')
                break

    try:
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-a",
                account,
                "-s",
                CLAUDE_KEYCHAIN_SERVICE,
                "-w",
                json_str,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            log.warning("Failed to write credentials to Keychain: %s", result.stderr.strip())
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning("Failed to write credentials to Keychain: %s", e)
        return False

    return True


def _write_claude_file(json_str: str) -> bool:
    """Write the credentials JSON to ~/.claude/.credentials.json (mode 0600)."""
    try:
        CLAUDE_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CLAUDE_CREDENTIALS_FILE.with_name(CLAUDE_CREDENTIALS_FILE.name + ".tmp")
        tmp.write_text(json_str, encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(CLAUDE_CREDENTIALS_FILE)
    except OSError as e:
        log.error("Failed to write %s: %s", CLAUDE_CREDENTIALS_FILE, e)
        return False
    return True


def write_claude_credentials(creds: ClaudeCredentials) -> bool:
    """Write updated credentials back, preferring Keychain and falling back to file.

    Anthropic rotates the refresh_token on every call, so we MUST persist the new
    pair — otherwise the next refresh attempt will 401. If the credentials were
    read from the file (Keychain unavailable), or the Keychain write fails, we
    persist to ~/.claude/.credentials.json — mirroring Claude Code's own fallback.
    """
    # Update the raw JSON with new tokens, preserving all other fields
    updated = creds.raw_json.copy()
    oauth = updated.setdefault("claudeAiOauth", {})
    oauth["accessToken"] = creds.access_token
    oauth["refreshToken"] = creds.refresh_token
    oauth["expiresAt"] = creds.expires_epoch * 1000  # back to epoch ms

    json_str = json.dumps(updated, separators=(",", ":"))

    if creds.source != "file" and _write_claude_keychain(json_str):
        log.info("Updated Claude credentials in macOS Keychain")
        return True

    if _write_claude_file(json_str):
        log.info("Updated Claude credentials in %s", CLAUDE_CREDENTIALS_FILE)
        return True

    return False


def _parse_expiry(value: int | float | str) -> int:
    """Parse expiry value to epoch seconds."""
    try:
        v = int(value)
    except TypeError, ValueError:
        return 0
    # epoch milliseconds → seconds
    if v > 9_999_999_999:
        return v // 1000
    return v


# ── Claude OAuth refresh ────────────────────────────────────────────────────


def refresh_claude_token(creds: ClaudeCredentials) -> ClaudeCredentials | None:
    """Refresh Claude OAuth token using refresh_token grant.

    On success, updates the Keychain with new accessToken + rotated refreshToken.
    Returns updated credentials, or None on failure.
    """
    if not creds.refresh_token:
        log.warning("No refresh_token available, cannot refresh")
        return None

    log.info("Refreshing Claude OAuth token via %s ...", CLAUDE_OAUTH_TOKEN_URL)

    payload = json.dumps(
        {
            "grant_type": "refresh_token",
            "refresh_token": creds.refresh_token,
            "client_id": CLAUDE_OAUTH_CLIENT_ID,
        }
    ).encode()

    req = Request(
        CLAUDE_OAUTH_TOKEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "claude-code/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()
        except Exception:
            pass
        log.error("Claude OAuth refresh failed (HTTP %d): %s", e.code, error_body)
        return None
    except (URLError, TimeoutError) as e:
        log.error("Claude OAuth refresh network error: %s", e)
        return None

    new_access = body.get("access_token", "")
    new_refresh = body.get("refresh_token", "") or creds.refresh_token
    expires_in = body.get("expires_in", 28800)  # default 8h

    if not new_access:
        log.error("Claude OAuth response missing access_token")
        return None

    new_expires_epoch = int(time.time()) + int(expires_in)

    updated = ClaudeCredentials(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_epoch=new_expires_epoch,
        raw_json=creds.raw_json,
        source=creds.source,
    )

    if not write_claude_credentials(updated):
        return None

    remaining_min = (new_expires_epoch - int(time.time())) // 60
    log.info("Claude token refreshed, new expiry in %dm", remaining_min)
    return updated


# ── Token extractors ─────────────────────────────────────────────────────────


def extract_claude_token(cfg: Config) -> tuple[str, int]:
    """Extract Claude access token, refreshing if near expiry.

    Returns (access_token, expires_epoch) or ("", 0) on failure.
    """
    creds = read_claude_credentials()
    if not creds:
        log.warning("No Claude credentials found in Keychain or %s", CLAUDE_CREDENTIALS_FILE)
        return "", 0

    now = int(time.time())
    remaining = creds.expires_epoch - now

    if creds.expires_epoch > 0 and remaining <= cfg.early_refresh_sec:
        if remaining > 0:
            log.info(
                "Claude token expires in %dm (< %ds threshold), refreshing...",
                remaining // 60,
                cfg.early_refresh_sec,
            )
        else:
            log.warning("Claude token is EXPIRED, refreshing...")

        refreshed = refresh_claude_token(creds)
        if refreshed:
            return refreshed.access_token, refreshed.expires_epoch

        log.warning("OAuth refresh failed, using existing token")

    return creds.access_token, creds.expires_epoch


def extract_chatgpt_token() -> str:
    """Extract ChatGPT/Codex access token from ~/.codex/auth.json."""
    if not CODEX_AUTH_FILE.is_file():
        return ""

    try:
        data = json.loads(CODEX_AUTH_FILE.read_text(encoding="utf-8"))
        return (data.get("tokens") or {}).get("access_token", "")
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to read Codex auth: %s", e)
        return ""


def extract_kimi_key() -> str:
    """Extract Kimi API key from ~/.kimi/config.toml."""
    if not KIMI_CONFIG_FILE.is_file():
        return ""

    try:
        data = tomllib.loads(KIMI_CONFIG_FILE.read_text(encoding="utf-8"))
        return data.get("api_key", "")
    except (tomllib.TOMLDecodeError, OSError) as e:
        log.warning("Failed to read Kimi config: %s", e)
        return ""


# ── SSH helpers ──────────────────────────────────────────────────────────────


def _ssh_cmd(cfg: Config) -> list[str]:
    """Build base SSH command with optional extra opts."""
    cmd = ["ssh"]
    if cfg.pi_ssh_opts:
        cmd.extend(cfg.pi_ssh_opts.split())
    cmd.append(cfg.pi_target)
    return cmd


def _ssh_run(cfg: Config, remote_cmd: str, *, input_data: str | None = None) -> tuple[bool, str]:
    """Run a command on Pi via SSH. Returns (success, stdout)."""
    try:
        result = subprocess.run(
            [*_ssh_cmd(cfg), remote_cmd],
            capture_output=True,
            text=True,
            input=input_data,
            timeout=15,
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.debug("SSH command failed: %s", e)
        return False, ""


def ensure_remote_dir(cfg: Config) -> bool:
    """Ensure secrets directory exists on Pi."""
    ok, _ = _ssh_run(cfg, f"mkdir -p '{cfg.pi_secrets_dir}'")
    if not ok:
        log.warning("Cannot reach Pi (%s), will retry later", cfg.pi_target)
    return ok


def sync_all_secrets(cfg: Config, secrets: dict[str, str]) -> list[str]:
    """Sync multiple secrets to Pi in at most 2 SSH calls.

    Returns list of names that were updated.
    """
    to_sync = {k: v for k, v in secrets.items() if v}
    if not to_sync:
        return []

    names = list(to_sync.keys())
    dir_ = cfg.pi_secrets_dir
    names_arg = " ".join(shlex.quote(n) for n in names)

    # One SSH call: read all current remote values (one line per file)
    ok, out = _ssh_run(
        cfg,
        f"for n in {names_arg}; do cat '{dir_}/'\"$n\" 2>/dev/null | tr -d '\\n'; echo; done",
    )
    remote_vals = out.splitlines() if ok else []
    while len(remote_vals) < len(names):
        remote_vals.append("")

    changed = [(n, to_sync[n]) for i, n in enumerate(names) if remote_vals[i] != to_sync[n]]
    if not changed:
        return []

    # One SSH call: write all changed files via stdin script
    script = "\n".join(
        f"printf '%s\\n' {shlex.quote(v)} > '{dir_}/{n}.tmp'"
        f" && mv '{dir_}/{n}.tmp' '{dir_}/{n}'"
        f" && chmod 0400 '{dir_}/{n}'"
        for n, v in changed
    )
    ok, _ = _ssh_run(cfg, "bash", input_data=script + "\n")
    if not ok:
        log.error("Failed to sync secrets to Pi")
        return []

    updated = [n for n, _ in changed]
    for n in updated:
        log.info("[sync] %s updated on %s", n, cfg.pi_target)
    return updated


# ── Main sync logic ──────────────────────────────────────────────────────────


def do_sync(cfg: Config, state: SyncState) -> None:
    """Perform one round of token extraction and sync."""
    token, expires = extract_claude_token(cfg)
    state.claude_expires_epoch = expires
    if token and expires > 0:
        remaining_min = (expires - int(time.time())) // 60
        if remaining_min > 0:
            log.info("Claude token expires in %dm", remaining_min)

    chatgpt_token = extract_chatgpt_token()
    if not chatgpt_token:
        log.warning("No ChatGPT token found in %s", CODEX_AUTH_FILE)

    kimi_key = extract_kimi_key()
    if not kimi_key:
        log.warning("No Kimi API key found in %s", KIMI_CONFIG_FILE)

    # Skip SSH entirely if nothing changed locally since last sync
    if (
        token == state.last_claude_token
        and chatgpt_token == state.last_chatgpt_token
        and kimi_key == state.last_kimi_key
    ):
        log.info("All tokens unchanged locally, skipping sync")
        return

    updated = sync_all_secrets(
        cfg,
        {
            "claude_oauth_token": token,
            "chatgpt_oauth_token": chatgpt_token,
            "kimi_api_key": kimi_key,
        },
    )

    if updated:
        if "claude_oauth_token" in updated:
            state.last_claude_token = token
        if "chatgpt_oauth_token" in updated:
            state.last_chatgpt_token = chatgpt_token
        if "kimi_api_key" in updated:
            state.last_kimi_key = kimi_key
        log.info("Sync completed with changes: %s", ", ".join(updated))
    else:
        log.info("Sync completed, all tokens up-to-date")


# ── Sleep strategy ───────────────────────────────────────────────────────────


def compute_sleep_seconds(cfg: Config, state: SyncState) -> int:
    """Calculate optimal sleep duration.

    If Claude has a known expiry, sleep until EARLY_REFRESH_SEC before it,
    capped by POLL_INTERVAL for ChatGPT/Kimi freshness.
    """
    if state.claude_expires_epoch > 0:
        wake_at = state.claude_expires_epoch - cfg.early_refresh_sec
        delta = wake_at - int(time.time())
        if delta > 0:
            return min(delta, cfg.poll_interval)

    return cfg.poll_interval


# ── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync AI tokens from macOS to Raspberry Pi")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode (loop)")
    args = parser.parse_args()

    cfg = Config(daemon=args.daemon)
    setup_logging(cfg.log_file)

    log.info("===== sync_ai_tokens_to_pi starting =====")
    log.info(
        "PI_TARGET=%s  PI_SECRETS_DIR=%s  POLL=%ds  EARLY_REFRESH=%ds  DAEMON=%s",
        cfg.pi_target,
        cfg.pi_secrets_dir,
        cfg.poll_interval,
        cfg.early_refresh_sec,
        cfg.daemon,
    )

    if not ensure_remote_dir(cfg):
        if not cfg.daemon:
            log.error("Cannot connect to Pi, aborting")
            sys.exit(1)
        log.warning("Pi unreachable on startup, will keep retrying...")

    state = SyncState()

    if cfg.daemon:
        while True:
            if ensure_remote_dir(cfg):
                do_sync(cfg, state)
            else:
                log.warning("Pi unreachable, will retry next cycle")

            sleep_sec = compute_sleep_seconds(cfg, state)
            log.info("Sleeping %ds until next sync...", sleep_sec)
            time.sleep(sleep_sec)
    else:
        do_sync(cfg, state)
        log.info("===== one-shot sync done =====")


if __name__ == "__main__":
    main()
