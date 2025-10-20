#!/usr/bin/env bash
set -euo pipefail

if mkdir -p /root/.instyper 2>/dev/null; then
    :
else
    mkdir -p "${HOME:-/tmp}/.instyper" 2>/dev/null || true
fi

# If XAUTHORITY was bind-mounted, ensure env points to it
if [ -n "${XAUTHORITY:-}" ]; then
    export XAUTHORITY=/root/.Xauthority
fi

# Start pulseaudio if available (non-fatal)
pulseaudio --start || true

# Run the application via uv to match local development workflow
exec uv run instyper
