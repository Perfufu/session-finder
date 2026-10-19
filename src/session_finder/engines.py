"""Window engine selection.

- gtk: pywebview + the system's WebKitGTK (light, nothing to download, but
  PyGObject must come from the system: it only exists as source on PyPI).
- qt:  pywebview + Qt WebEngine from PyPI (`session-finder[qt]`): self-contained,
  works on any distro/window manager without system packages.

"auto" prefers GTK when it is usable, then Qt.
"""
import importlib.util

ENGINES = ("auto", "gtk", "qt")

INSTALL_HELP = """\
No window engine available ({reason}).
Install one of:
  - self-contained (any distro):  uv tool install "session-finder[qt] @ git+<repo URL>"
                                  (from a clone: uv pip install -e ".[qt]")
  - system WebKitGTK (Arch):      sudo pacman -S python-pywebview webkit2gtk-4.1
                                  + a venv created with --system-site-packages
Meanwhile, the list is available in the terminal: session-finder --table"""


def gtk_usable():
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        for version in ("4.1", "4.0"):  # same order as pywebview's GTK backend
            try:
                gi.require_version("WebKit2", version)
                break
            except ValueError:
                continue
        else:
            return False
        from gi.repository import Gtk, WebKit2  # noqa: F401
        import webview  # noqa: F401
        return True
    except (ImportError, ValueError):
        return False


def qt_usable():
    # Cheap check: the real Qt WebEngine import happens when the window starts.
    return all(importlib.util.find_spec(m) is not None for m in ("webview", "qtpy", "PySide6"))


def choose(preferred="auto"):
    """-> (engine, None) or (None, reason why nothing is usable)."""
    if preferred in ("auto", "gtk") and gtk_usable():
        return "gtk", None
    if preferred in ("auto", "qt") and qt_usable():
        return "qt", None
    if preferred == "auto":
        return None, "neither WebKitGTK nor Qt WebEngine found"
    return None, f"engine '{preferred}' not installed"


def prepare(engine, app_id):
    """Sets the Wayland app-id (the target of window manager rules). Must run
    before the toolkit creates its first window."""
    if engine == "gtk":
        from gi.repository import GLib
        GLib.set_prgname(app_id)  # GTK3 on Wayland: app-id = prgname
    else:
        from qtpy.QtGui import QGuiApplication
        QGuiApplication.setDesktopFileName(app_id)  # Qt on Wayland: app-id = desktop file name
