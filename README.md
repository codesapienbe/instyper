# Instyper — Run locally with uv

Instyper runs as a desktop application and can be built and run locally using `uv`. This repository no longer supports or distributes Docker-based workflows.

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
