#!/usr/bin/env bash
set -euo pipefail

# Run RobotEva inside the active desktop session so SDL window can appear over the DSI desktop.
# Works when launched from SSH/tty as the same user who owns the desktop session.

PROJECT_DIR="/home/pi/Projects/RobotEva"
VENV_PY="${PROJECT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "ERROR: venv python not found: ${VENV_PY}"
  exit 1
fi

UID_NUM="$(id -u)"

# Try Wayland first (Raspberry Pi OS Bookworm defaults to Wayland)
if [[ -e "/run/user/${UID_NUM}/wayland-0" ]]; then
  export XDG_RUNTIME_DIR="/run/user/${UID_NUM}"
  export WAYLAND_DISPLAY="wayland-0"
fi

# Also set DISPLAY if X11/XWayland is available
if [[ -S "/tmp/.X11-unix/X0" ]]; then
  export DISPLAY=":0"
fi

echo "Using env:"
echo "  DISPLAY=${DISPLAY-}"
echo "  WAYLAND_DISPLAY=${WAYLAND_DISPLAY-}"
echo "  XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR-}"

cd "${PROJECT_DIR}"
exec "${VENV_PY}" main.py



