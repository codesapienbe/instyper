#!/usr/bin/env bash
set -euo pipefail

# Lightweight entrypoint for running the GUI using the host X server.
# Assumes the host has mounted /tmp/.X11-unix and optionally Xauthority.

# Ensure config dir exists in container
mkdir -p /root/.instyper

# If XAUTHORITY was bind-mounted, ensure env points to it
if [ -n "${XAUTHORITY:-}" ]; then
    export XAUTHORITY=/root/.Xauthority
fi

# Start pulseaudio if available (non-fatal)
pulseaudio --start || true

# Run the application via uv to match local development workflow
exec uv run instyper
