#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export QT_QPA_PLATFORM="wayland;xcb"
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
exec "${SCRIPT_DIR}/venv/bin/python3" "${SCRIPT_DIR}/jarvis.py" "$@"
