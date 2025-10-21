#!/bin/sh
set -euo pipefail

## Ensure a writable per-user config directory exists. Prefer $HOME if set, else fall back to /tmp.
HOME_DIR="${HOME:-/tmp}"
if mkdir -p "${HOME_DIR}/.instyper" 2>/dev/null; then
    :
else
    mkdir -p "/tmp/.instyper" 2>/dev/null || true
fi

# If XAUTHORITY was bind-mounted, ensure env points to it and the file exists
## If XAUTHORITY was bind-mounted from the host, point the variable inside the container to that path
if [ -n "${XAUTHORITY:-}" ] && [ -f "${XAUTHORITY}" ]; then
    export XAUTHORITY="${XAUTHORITY}"
else
    # Unset if not present to avoid pointing to a non-existent file
    unset XAUTHORITY 2>/dev/null || true
fi

# Start pulseaudio if available (non-fatal)
if command -v pulseaudio >/dev/null 2>&1; then
    pulseaudio --start || true
fi

## Run `uv sync` at container start to ensure the virtualenv is created in-container
if command -v uv >/dev/null 2>&1; then
    # Sync dependencies (non-fatal if it fails) and then run the app
    uv sync --no-install-project || true
    exec uv run instyper
fi

# Fallback: run directly with python if uv isn't available
exec python3 -m instyper
