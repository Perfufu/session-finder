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

LANGUAGES = ("en", "fr")   # = the objects of STRINGS in ui/app.js (a test checks it)

DEFAULTS = {
    "ui": {"language": "auto"},
    "theme": {
        "preset": "default",
        "mode": "auto",
        "translucent": False,
        "palette_sh": {"path": "", "active_file": ""},
    },
    "terminal": {"command": ""},
    "sessions": {"hide_non_interactive": False, "exclude_folders": []},
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


def resolve_language(setting, env=None):
    """"auto" = system locale (LC_ALL > LC_MESSAGES > LANG, e.g. fr_FR.UTF-8 → fr);
    an unsupported or invalid value falls back to English."""
    env = os.environ if env is None else env
    if setting == "auto":
        setting = next((env[k] for k in ("LC_ALL", "LC_MESSAGES", "LANG") if env.get(k)), "")
    code = str(setting).replace("-", "_").split("_")[0].split(".")[0].lower()
    return code if code in LANGUAGES else "en"


def language_setting(setting):
    """What the window's Language menu shows as selected: "auto" or a supported code."""
    return "auto" if setting == "auto" else resolve_language(setting)


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


def hiding(cfg):
    """[sessions] options of the config, as index.build_index keyword arguments."""
    return {"hide_non_interactive": cfg["sessions"]["hide_non_interactive"],
            "exclude_folders": cfg["sessions"]["exclude_folders"]}


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
