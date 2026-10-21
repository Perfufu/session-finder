"""The selector window (pywebview).

The page (ui/ + vendor/) is assembled in memory and handed to pywebview:
no HTTP server, no open port.
"""
import copy
import fcntl
import json
import os
import re
from importlib import resources
from pathlib import Path

from . import config, engines, index, launchers, niri, themes

APP_ID = "session-finder"  # Wayland app-id: the target of window manager rules
TITLE = "Session Finder"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def state_path():
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state"
    return Path(base) / "session-finder" / "state.json"


def load_state():
    try:
        return json.loads(state_path().read_text())
    except (OSError, ValueError):
        return {}


def save_state(state):
    try:
        path = state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
    except OSError:
        pass


class Api:
    """Exposed to JS as window.pywebview.api (attributes starting with _ stay private)."""

    def __init__(self, terminal, persist=True):
        self._window = None
        self._terminal = terminal
        self._persist = persist  # False with --defaults: the default view never touches the user's state

    def _remember(self, key, value):
        if not self._persist:
            return
        state = load_state()
        if value is None:
            state.pop(key, None)
        else:
            state[key] = value
        save_state(state)

    def resume(self, session_id):
        if not isinstance(session_id, str) or not UUID.match(session_id):
            return {"ok": False, "error": "invalid session id"}
        session = next((s for s in index.build_index(include_hidden=True)
                        if s["id"] == session_id), None)  # state read now, not when the window opened
        if session is None:
            return {"ok": False, "error": "session not found"}

        if session["pid"]:
            window_id = niri.window_of_pid(session["pid"]) if niri.available() else None
            if window_id is None:
                return {"ok": False, "error": "already open in another terminal"}
            niri.focus(window_id)
            self._window.destroy()
            return {"ok": True}

        if not session["cwd_exists"]:
            return {"ok": False, "error": f"folder not found: {session['cwd']}"}
        if not self._terminal:
            return {"ok": False, "error": "no terminal found (see [terminal] in the config)"}
        launchers.launch(self._terminal, session["cwd"], session_id)
        self._window.destroy()
        return {"ok": True}

    def set_mode(self, mode):
        if mode in themes.MODES:
            self._remember("mode", mode)

    def set_palette(self, choice_id):
        """Remembers the choice made in the Palette menu; None = back to the config."""
        if choice_id is None or isinstance(choice_id, str):
            self._remember("palette", choice_id)

    def browse_palette(self):
        """"Other…": native dialog, .toml files only (data, never executed —
        a palette.sh is only accepted from the config)."""
        import webview
        paths = self._window.create_file_dialog(
            webview.FileDialog.OPEN, directory=str(config.palettes_dir()),
            file_types=("Session Finder palettes (*.toml)",))
        if not paths:
            return None
        loaded = themes.load_palette_toml(paths[0])
        if loaded is None:
            return {"error": "unreadable palette (see the template: session-finder --new-palette <name>)"}
        return loaded

    def close(self):
        self._window.destroy()


def build_page(data):
    pkg = resources.files("session_finder")
    parts = {
        "STYLE": (pkg / "ui/style.css").read_text(),
        "VENDOR": (pkg / "vendor/force-graph-1.51.4.min.js").read_text(),
        # "</" escaped: a title containing </script> must not close the tag
        "DATA": "window.__DATA__ = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";",
        "APP": (pkg / "ui/app.js").read_text(),
    }
    # Single pass: a "/*DATA*/" inside an inserted file is not replaced again
    return re.sub(r"/\*(STYLE|VENDOR|DATA|APP)\*/", lambda m: parts[m.group(1)],
                  (pkg / "ui/index.html").read_text())


def single_instance():
    """True if we are the only instance. Under niri, an existing instance is
    brought to the front; elsewhere, a plain lock file (kept open until exit)."""
    if niri.available():
        existing = niri.window_of_app(APP_ID)
        if existing is not None:
            niri.focus(existing)
            return False
        return True
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    lock = open(Path(runtime) / f"{APP_ID}.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    single_instance.lock = lock  # keep a reference: the lock lives as long as the process
    return True


def run(engine, debug=False, defaults=False):
    """engine: "gtk" or "qt" (see engines.choose).
    defaults=True: the tool as a new user sees it (config, personal palettes and
    remembered choices ignored, nothing saved)."""
    if not single_instance():
        return
    if defaults:
        cfg, state, palettes = copy.deepcopy(config.DEFAULTS), {}, None
    else:
        cfg, state, palettes = config.load(), load_state(), config.palettes_dir()
    theme = themes.resolve(cfg["theme"], state, palettes)
    terminal = launchers.find_terminal(cfg["terminal"]["command"])

    data = {"sessions": index.build_index(), "theme": theme, "defaults_view": defaults,
            "home": str(Path.home()), "can_focus": niri.available(),
            "language": config.resolve_language(cfg["ui"]["language"])}

    engines.prepare(engine, APP_ID)
    import webview

    api = Api(terminal, persist=not defaults)
    current = next(c for c in theme["catalog"] if c["id"] == theme["selected"])
    first = current["palettes"]["light" if theme["mode"] == "light" else "dark"]
    api._window = webview.create_window(
        TITLE + (" — default view" if defaults else ""), html=build_page(data), js_api=api,
        width=1280, height=800, transparent=theme["translucent"], background_color=first["BG"])
    webview.start(gui=engine, debug=debug)
