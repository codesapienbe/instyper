#!/usr/bin/env bash
set -euo pipefail

## Ensure a writable per-user config directory exists. Prefer $HOME if set, else fall back to /tmp.
if mkdir -p "${HOME:-/tmp}/.instyper" 2>/dev/null; then
    :
else
    mkdir -p "/tmp/.instyper" 2>/dev/null || true
fi

# If XAUTHORITY was bind-mounted, ensure env points to it
## If XAUTHORITY was bind-mounted from the host, point the variable inside the container to that path
if [ -n "${XAUTHORITY:-}" ]; then
    export XAUTHORITY=${XAUTHORITY}
fi

# Start pulseaudio if available (non-fatal)
pulseaudio --start || true

# Run the application via uv to match local development workflow.
# Prefer absolute path if available; fall back to python module if uv is missing or fails.
UV_BIN="/usr/local/bin/uv"
if [ -x "$UV_BIN" ]; then
    exec "$UV_BIN" run instyper
fi
if command -v uv >/dev/null 2>&1; then
    exec uv run instyper
fi
# Fallback: run directly with python if uv isn't available
exec python3 -m instyper
