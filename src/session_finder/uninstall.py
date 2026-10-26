"""`session-finder --uninstall`: remove everything Session Finder wrote outside its own
uv environment. Only fixed, known paths; never anything under Claude Code's folder."""
import os
import shutil
import sys
from pathlib import Path

from . import app, config, index


def targets():
    """Paths Session Finder may have created (existing or not)."""
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return [
        config.config_dir(),                               # config.toml + personal palettes
        index.default_cache().parent,                      # index cache
        app.state_path().parent,                           # remembered choices
        config.applications_dir() / "session-finder.desktop",
        config.icons_dir() / "session-finder.svg",
        Path(runtime) / f"{app.APP_ID}.lock",
    ]


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def run(assume_yes=False, out=sys.stdout, err=sys.stderr):
    found = [p for p in targets() if p.exists() or p.is_symlink()]
    if not found:
        print("session-finder: nothing to remove (no config, cache, state or launcher entry).", file=out)
    else:
        print("session-finder: will delete:", file=out)
        for p in found:
            print(f"  {p}{'/' if p.is_dir() else ''}", file=out)
        print("Claude Code's own data (~/.claude) is never touched.", file=out)
        if not assume_yes:
            if not sys.stdin.isatty():
                print("session-finder: not a terminal, re-run with --yes to confirm.", file=err)
                return 1
            if input("Delete these? [y/N] ").strip().lower() not in ("y", "yes"):
                print("session-finder: cancelled.", file=out)
                return 1
        failed = 0
        for p in found:
            try:
                remove(p)
            except OSError as e:
                failed += 1
                print(f"session-finder: cannot delete {p}: {e}", file=err)
        if failed:
            return 1
        print("session-finder: data deleted.", file=out)
    print("Last step, removes the program itself:  uv tool uninstall session-finder", file=out)
    return 0
