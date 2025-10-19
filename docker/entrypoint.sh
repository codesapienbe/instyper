#!/usr/bin/env bash
set -euo pipefail

# Start a headless X server and lightweight window manager, then run the app.
XDISPLAY=":99"
export DISPLAY=$XDISPLAY

# Start Xvfb
Xvfb $XDISPLAY -screen 0 1024x768x24 >/dev/null 2>&1 &
XVFB_PID=$!

# Start a minimal window manager
fluxbox >/dev/null 2>&1 &
WM_PID=$!

# Start x11vnc to expose the display on 5900
x11vnc -display $XDISPLAY -forever -nopw -shared >/dev/null 2>&1 &
VNC_PID=$!

# Start pulseaudio to provide sound device support
pulseaudio --start || true

trap "kill $VNC_PID $WM_PID $XVFB_PID 2>/dev/null || true" EXIT

python -m instyper


