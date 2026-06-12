"""Instyper bootstrapper.

Ships a bundled `uv` binary plus the `instyper` wheel. On first run, uses uv
to install instyper as a managed tool (uv handles Python download, venv, and
PyPI deps automatically). Subsequent runs simply re-invoke the tool.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path.home() / ".instyper"


def bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def bundled_uv() -> Path:
    name = "uv.exe" if os.name == "nt" else "uv"
    path = bundle_dir() / name
    if not path.is_file():
        raise SystemExit(f"[instyper] Bundled uv not found at {path}")
    if os.name != "nt":
        path.chmod(0o755)
    return path


def bundled_wheel() -> Path:
    matches = sorted(bundle_dir().glob("instyper-*.whl"))
    if not matches:
        raise SystemExit("[instyper] Bundled instyper wheel not found")
    return matches[0]


def is_installed(uv: Path) -> bool:
    result = subprocess.run(
        [str(uv), "tool", "list"], capture_output=True, text=True, check=False
    )
    return result.returncode == 0 and "instyper" in result.stdout.lower()


def ensure_runtime(uv: Path) -> None:
    if is_installed(uv):
        return
    wheel = bundled_wheel()
    constraints = APP_DIR / "build-constraints.txt"
    constraints.write_text("setuptools<81\n")
    print(f"[instyper] First-time setup: installing {wheel.name}", flush=True)
    print("[instyper] This downloads Python and dependencies; may take several minutes.", flush=True)
    subprocess.check_call([
        str(uv), "tool", "install",
        "--python", "3.10",
        "--build-constraint", str(constraints),
        "--from", str(wheel),
        "instyper",
    ])


def run_instyper(uv: Path) -> int:
    cmd = [str(uv), "tool", "run", "--from", "instyper", "instyper", *sys.argv[1:]]
    return subprocess.call(cmd)


def main() -> int:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    uv = bundled_uv()
    try:
        ensure_runtime(uv)
    except subprocess.CalledProcessError as exc:
        print(f"[instyper] Setup failed (exit {exc.returncode})", file=sys.stderr)
        return exc.returncode
    return run_instyper(uv)


if __name__ == "__main__":
    raise SystemExit(main())
