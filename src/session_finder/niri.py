"""Optional integration with the niri compositor: bring a window to the front.

Only active under niri (NIRI_SOCKET set + `niri` command available).
Elsewhere the tool works without it: no focusing of an existing window.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path


def available():
    return bool(os.environ.get("NIRI_SOCKET")) and shutil.which("niri") is not None


def windows():
    try:
        out = subprocess.run(["niri", "msg", "-j", "windows"],
                             capture_output=True, text=True, timeout=2).stdout
        return json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def focus(window_id):
    subprocess.run(["niri", "msg", "action", "focus-window", "--id", str(window_id)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)


def window_of_app(app_id):
    return next((w["id"] for w in windows() if w.get("app_id") == app_id), None)


def parent_pid(pid):
    try:
        # /proc/<pid>/stat: "pid (comm) state ppid ..."; comm may contain spaces
        return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
    except (OSError, IndexError, ValueError):
        return 0


def window_of_pid(pid):
    """Window hosting a process: walk up claude -> shell -> terminal until a
    PID known to niri is found."""
    by_pid = {w.get("pid"): w["id"] for w in windows()}
    while pid > 1:
        if pid in by_pid:
            return by_pid[pid]
        pid = parent_pid(pid)
    return None
