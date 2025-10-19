# Instyper — Docker-first Voice Typing

Instyper runs as a desktop application but is distributed and supported to run only via Docker in this repo. It uses your host X11 server so the native GUI appears on your desktop while the app runs inside a container.

This README focuses on the Docker workflow: build, run, and troubleshoot.

Quick prerequisites on the host:

- Docker installed
- A running X server (typical on Linux desktops)
- If you want audio support, ensure `/dev/snd` exists and your user can access it

Quick start (3 commands)

1. Build the image:

   - `make build`

2. Allow the container to connect to your X server (one-time step):

   - `xhost +local:root`  # allow local root-owned clients to connect

3. Run the app:

   - `make run`

That's it — the app GUI should appear on your desktop.

Notes and useful options

- Persisted data: your models and config are stored on the host at `~/.instyper`. The container mounts this directory so models survive container restarts.
- Global hotkey and automatic paste are disabled by default in the container (fragile with X/clipboard).
  - To enable them (advanced / brittle), set environment variables when running the container:
    - `-e ENABLE_GLOBAL_HOTKEY=1 -e ENABLE_AUTO_PASTE=1`

Troubleshooting

- No window appears:
  - Verify `DISPLAY` is set in your shell: `echo $DISPLAY`
  - Ensure you ran `xhost +local:root` (or mount your Xauthority into the container).
  - Check `docker run` in `Makefile` mounts `/tmp/.X11-unix` and `~/.instyper`.

- Audio issues:
  - Make sure `/dev/snd` exists and is accessible to Docker. The Makefile mounts it by default.

- Permissions or missing models:
  - Models and config live in `~/.instyper`. If the app complains, check that directory and its permissions.

Advanced

- To run with host clipboard/hotkeys enabled (not recommended), run the container with `-e ENABLE_GLOBAL_HOTKEY=1 -e ENABLE_AUTO_PASTE=1` and ensure XAUTH or `xhost` allows access.

Help

- Issues & source: `https://github.com/codesapienbe/instyper`

License

MIT
