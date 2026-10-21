"""User configuration: $XDG_CONFIG_HOME/session-finder/config.toml (optional).

Every option is documented in config.example.toml (copied by
`session-finder --init-config`). A missing or invalid file blocks nothing:
default values + a warning.
"""
import copy
import os
import sys
import tomllib
from importlib import resources
from pathlib import Path

DEFAULTS = {
    "theme": {
        "preset": "default",
        "mode": "auto",
        "translucent": False,
        "palette_sh": {"path": "", "active_file": ""},
    },
    "terminal": {"command": ""},
}


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "session-finder"


def config_path():
    return config_dir() / "config.toml"


def palettes_dir():
    return config_dir() / "palettes"


def data_dir():
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def applications_dir():
    return data_dir() / "applications"


def icons_dir():
    return data_dir() / "icons" / "hicolor" / "scalable" / "apps"


def warn(message):
    print(f"session-finder: {message}", file=sys.stderr)


def merge(defaults, user, where=""):
    """Merges the user config over the defaults, keeping the expected types."""
    out = copy.deepcopy(defaults)
    for key, value in user.items():
        name = f"{where}{key}"
        if key not in defaults:
            warn(f"unknown option ignored: {name}")
        elif isinstance(defaults[key], dict):
            if isinstance(value, dict):
                out[key] = merge(defaults[key], value, f"{name}.")
            else:
                warn(f"{name} must be a section, ignored")
        elif type(value) is not type(defaults[key]):
            warn(f"{name}: unexpected type ({type(value).__name__}), default value kept")
        else:
            out[key] = value
    return out


def load(path=None):
    path = path or config_path()
    try:
        with open(path, "rb") as fh:
            user = tomllib.load(fh)
    except FileNotFoundError:
        return copy.deepcopy(DEFAULTS)
    except (OSError, tomllib.TOMLDecodeError) as e:
        warn(f"unreadable config ({path}): {e} — using default values")
        return copy.deepcopy(DEFAULTS)
    return merge(DEFAULTS, user)


def example(name):
    return (resources.files("session_finder") / name).read_text()


def create_from_example(target, example_name, replace=None):
    """Copies a template shipped with the tool. Never overwrites an existing file.
    Returns (ok, message)."""
    if target.exists():
        return False, f"{target} already exists: nothing was overwritten"
    text = example(example_name)
    for old, new in (replace or {}).items():
        text = text.replace(old, new, 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return True, f"created: {target}"
