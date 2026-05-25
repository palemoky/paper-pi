#!/usr/bin/env bash
set -euo pipefail

# Install (or update) the sync-tokens LaunchAgent from the plist template.
#
# Usage (remote):
#   bash <(curl -fsSL https://raw.githubusercontent.com/palemoky/paper-pi/main/scripts/install_launchd.sh)
#   bash <(curl -fsSL https://raw.githubusercontent.com/palemoky/paper-pi/main/scripts/install_launchd.sh) uninstall
#
# Usage (local):
#   ~/.paper-pi/install_launchd.sh
#   ~/.paper-pi/install_launchd.sh uninstall

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Error: this script only works on macOS (launchd). Current OS: $(uname -s)" >&2
  exit 1
fi

LABEL="com.paper-pi.sync-tokens"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

# Detect local run: script is a real file with the plist template alongside it
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_TEMPLATE="$SCRIPT_DIR/com.paper-pi.sync-tokens.plist"

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

prompt() {
  local var_name="$1" prompt_text="$2" default="$3"
  read -rp "$prompt_text [$default]: " input
  printf -v "$var_name" '%s' "${input:-$default}"
}

render_plist() {
  local script_dir="$1" pi_target="$2" pi_secrets_dir="$3"
  local template_path="$LOCAL_TEMPLATE"

  if [[ ! -f "$template_path" ]]; then
    template_path="$script_dir/$PLIST_TEMPLATE"
  fi

  if [[ ! -f "$template_path" ]]; then
    echo "Error: plist template not found at $template_path" >&2
    return 1
  fi

  local python3_path
  # Prefer Homebrew python3 over macOS system python3 (which may be too old)
  python3_path="$(
    for p in /opt/homebrew/bin/python3 /usr/bin/python3; do
      [[ -x "$p" ]] && echo "$p" && break
    done
  )"
  if [[ -z "$python3_path" ]]; then
    python3_path="$(command -v python3)" || {
      echo "Error: python3 not found" >&2
      return 1
    }
  fi

  sed \
    -e "s|__SCRIPT_DIR__|$script_dir|g" \
    -e "s|__PI_TARGET__|$pi_target|g" \
    -e "s|__PI_SECRETS_DIR__|$pi_secrets_dir|g" \
    -e "s|__PYTHON3__|$python3_path|g" \
    "$template_path"
}

GITHUB_RAW="https://raw.githubusercontent.com/palemoky/paper-pi/main"
SYNC_SCRIPT="sync_ai_tokens_to_pi.py"
PLIST_TEMPLATE="com.paper-pi.sync-tokens.plist"

fetch_sync_script() {
  local dest_dir="$1"
  local dest="$dest_dir/$SYNC_SCRIPT"
  if [[ -f "$dest" ]]; then
    echo "  $SYNC_SCRIPT already exists, skipping download."
    return
  fi
  echo "  Downloading $SYNC_SCRIPT..."
  mkdir -p "$dest_dir"
  curl -fsSL "$GITHUB_RAW/scripts/$SYNC_SCRIPT" -o "$dest"
  chmod +x "$dest"
  echo "  Saved to $dest"
}

fetch_plist_template() {
  local dest_dir="$1"
  local dest="$dest_dir/$PLIST_TEMPLATE"
  if [[ -f "$dest" ]]; then
    echo "  $PLIST_TEMPLATE already exists, skipping download."
    return
  fi
  echo "  Downloading $PLIST_TEMPLATE..."
  mkdir -p "$dest_dir"
  curl -fsSL "$GITHUB_RAW/scripts/$PLIST_TEMPLATE" -o "$dest"
  echo "  Saved to $dest"
}

install() {
  echo "Configure sync-tokens LaunchAgent:"
  prompt REPO_DIR       "  Local repo path" "$HOME/.paper-pi"
  prompt PI_TARGET      "  Pi SSH host"     "pi"
  prompt PI_SECRETS_DIR "  Secrets dir on Pi" "/home/pi/paper-pi/secrets"
  echo ""

  # Download sync script when not running from a local clone
  if [[ ! -f "$LOCAL_TEMPLATE" ]]; then
    fetch_sync_script "$REPO_DIR"
    fetch_plist_template "$REPO_DIR"
    echo ""
  fi

  mkdir -p "$HOME/Library/LaunchAgents"
  render_plist "$REPO_DIR" "$PI_TARGET" "$PI_SECRETS_DIR" > "$DEST"

  if launchctl list "$LABEL" &>/dev/null; then
    launchctl unload "$DEST" 2>/dev/null || true
  fi

  launchctl load "$DEST"
  echo "Installed and loaded $LABEL"
  echo "  Plist:  $DEST"
  echo "  Script: $REPO_DIR/sync_ai_tokens_to_pi.py"
  echo ""
  echo "View logs:  tail -f /tmp/sync_ai_tokens.log"
}

case "${1:-install}" in
  uninstall) uninstall ;;
  install|*) install ;;
esac
