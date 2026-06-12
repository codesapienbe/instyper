# Instyper

Instyper is a cross-platform desktop voice-typing application.

## Install with `uv`

Instyper is distributed directly from this Git repository — install it with [`uv`](https://docs.astral.sh/uv/):

```sh
# One-off run (downloads, installs into a temporary env, runs):
uvx --python 3.10 --from git+https://github.com/codesapienbe/instyper@v2026.06.12.1 instyper

# Permanent install (then just run `instyper`):
uv tool install --python 3.10 --from git+https://github.com/codesapienbe/instyper@v2026.06.12.1 instyper
instyper
```

Replace `v2026.06.12.1` with the tag you want, or use `main` for the latest. The `--python 3.10` flag is required because some dependencies (e.g. `stt`) don't ship wheels for newer Python versions; uv will download a managed CPython 3.10 if you don't have one.

Don't have `uv`? Install it first:

```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Run from source (for development)

Quick prerequisites on the host:

- A working Python 3 installation
- A running X server (typical on Linux desktops)
- If you want audio support, ensure `/dev/snd` exists and your user can access it

- **Build requirement (optional)**: If you plan to build packages that need PortAudio (e.g. `pyaudio`), install headers:
  - Debian/Ubuntu: `sudo apt-get install -y portaudio19-dev build-essential gcc pkg-config`
  - macOS (Homebrew): `brew install portaudio`

Quick start (2 commands)

1. Prepare the project (creates / syncs a virtualenv via `uv`):

   - `make build`

2. Run the app:

   - `make run`

That's it — the app GUI should appear on your desktop when run locally.

Notes and useful options

- Persisted data: your models and config are stored on the host at `~/.instyper`.

Troubleshooting

- No window appears:
  - Verify `DISPLAY` is set in your shell: `echo $DISPLAY`

- Audio issues:
  - Make sure `/dev/snd` exists and is accessible on your system.

- Permissions or missing models:
  - Models and config live in `~/.instyper`. If the app complains, check that directory and its permissions.

Help

- Issues & source: `https://github.com/codesapienbe/instyper`

License

MIT
