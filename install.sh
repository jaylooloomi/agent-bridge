#!/usr/bin/env bash
set -euo pipefail

DEST="${AGENT_BRIDGE_HOME:-$HOME/.agent-bridge}"
echo "==> Installing agent-bridge into $DEST ..."

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" pull --ff-only
else
  git clone https://github.com/jaylooloomi/agent-bridge.git "$DEST"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m venv "$DEST/.venv"
if [ -x "$DEST/.venv/bin/pip" ]; then
  "$DEST/.venv/bin/pip" install --upgrade pip
  "$DEST/.venv/bin/pip" install -e "$DEST"
  "$DEST/.venv/bin/agent-bridge-install"
else
  "$DEST/.venv/Scripts/pip.exe" install --upgrade pip
  "$DEST/.venv/Scripts/pip.exe" install -e "$DEST"
  "$DEST/.venv/Scripts/agent-bridge-install.exe"
fi

echo "==> Done! Restart your session to use agent-bridge MCP tools."
