#!/usr/bin/env bash
set -euo pipefail

# Install (or update) the sync-tokens LaunchAgent from the plist template.
#
# Usage:
#   ./scripts/install_launchd.sh            # install / update
#   ./scripts/install_launchd.sh uninstall  # remove

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: this script only works on macOS (launchd). Current OS: $(uname -s)" >&2
  exit 1
fi

LABEL="com.paper-pi.sync-tokens"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SCRIPT_DIR/com.paper-pi.sync-tokens.plist"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

uninstall() {
  if launchctl list "$LABEL" &>/dev/null; then
    launchctl unload "$DEST" 2>/dev/null || true
    echo "Unloaded $LABEL"
  fi
  if [[ -f "$DEST" ]]; then
    rm "$DEST"
    echo "Removed $DEST"
  fi
  echo "Done."
}

install() {
  if [[ ! -f "$TEMPLATE" ]]; then
    echo "Error: template not found at $TEMPLATE" >&2
    exit 1
  fi

  # Replace placeholder with actual path
  mkdir -p "$HOME/Library/LaunchAgents"
  sed "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" "$TEMPLATE" > "$DEST"

  # Reload if already loaded
  if launchctl list "$LABEL" &>/dev/null; then
    launchctl unload "$DEST" 2>/dev/null || true
  fi

  launchctl load "$DEST"
  echo "Installed and loaded $LABEL"
  echo "  Plist: $DEST"
  echo "  Script: $SCRIPT_DIR/sync_ai_tokens_to_pi.py"
  echo ""
  echo "View logs:  tail -f /tmp/sync_ai_tokens.log"
}

case "${1:-install}" in
  uninstall) uninstall ;;
  install|*) install ;;
esac
