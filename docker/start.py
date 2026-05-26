"""Start the single-container Pace Downloader runtime."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DATA_ROOT = Path(os.environ.get("PACE_DATA_DIR", "/var/lib/pace-downloader"))
BACKEND_APP_DIR = Path("/app/backend")
FRONTEND_DIR = Path("/app/frontend")

children: list[subprocess.Popen] = []
shutdown_requested = False


def ensure_runtime_dirs() -> None:
    for directory in [
        DATA_ROOT,
        DATA_ROOT / "data",
        DATA_ROOT / "data" / "eps-metadata",
        DATA_ROOT / "data" / "eps-metadata" / "One Pace",
        DATA_ROOT / "data" / "releases",
        DATA_ROOT / "data" / "sheets",
        DATA_ROOT / "logs",
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def start_processes() -> None:
    env = os.environ.copy()
    env.setdefault("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000")

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--app-dir",
            str(BACKEND_APP_DIR),
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=DATA_ROOT,
        env=env,
    )

    frontend_env = env.copy()
    frontend_env["HOST"] = "0.0.0.0"
    frontend_env["PORT"] = "3000"
    frontend = subprocess.Popen(["node", "build"], cwd=FRONTEND_DIR, env=frontend_env)

    children.extend([backend, frontend])


def stop_children(signum: int) -> None:
    for child in children:
        if child.poll() is None:
            child.send_signal(signum)

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if all(child.poll() is not None for child in children):
            return
        time.sleep(0.1)

    for child in children:
        if child.poll() is None:
            child.kill()


def handle_signal(signum: int, _frame: object) -> None:
    global shutdown_requested
    shutdown_requested = True
    stop_children(signum)


def wait_for_exit() -> int:
    while True:
        for child in children:
            returncode = child.poll()
            if returncode is not None:
                if shutdown_requested:
                    return 0

                stop_children(signal.SIGTERM)
                return returncode if returncode != 0 else 1

        time.sleep(0.5)


def main() -> int:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    ensure_runtime_dirs()
    start_processes()
    return wait_for_exit()


if __name__ == "__main__":
    raise SystemExit(main())
