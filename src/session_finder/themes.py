"""Interface colours.

The interface only uses 10 colours, none hard-coded: a palette is just a set of
10 #rrggbb values, in a dark and/or light variant.

Catalogue offered in the window (Palette menu):
  preset:<name>  built-in presets (light + dark)
  user:<name>    TOML palettes from ~/.config/session-finder/palettes/<name>.toml
  file:<path>    TOML palette opened with "Other…"
  palette-sh     shell file set in the config (only when configured)
"""
import re
import subprocess
import tomllib
from pathlib import Path

from .config import warn

KEYS = ["BG", "BG_ALT", "BG_ELEVATED", "FG", "FG_DIM", "ACCENT",
        "ACCENT_ALT", "SUCCESS", "WARNING", "ERROR"]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
MODES = ("auto", "dark", "light")


def palette(bg, bg_alt, bg_elevated, fg, fg_dim, accent, accent_alt, success, warning, error):
    return dict(zip(KEYS, [bg, bg_alt, bg_elevated, fg, fg_dim, accent, accent_alt, success, warning, error]))


# Neutral dark/light backgrounds shared by every preset: only the accent pair
# (ACCENT, ACCENT_ALT) changes, so each preset has a clearly distinct character.
# "default" keeps the original blue-violet accent. SUCCESS is moved to teal in
# "green" so that open conversations stay distinguishable from the accent.
PRESETS = {
    "default": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#8b9cf7", "#c49af0", "#7cc48a", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#4457d6", "#8a4fc4", "#2f8a46", "#a86b00", "#c93445"),
    },
    "red": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#f0707a", "#f4a07a", "#7cc48a", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#c93445", "#b5562a", "#2f8a46", "#a86b00", "#c93445"),
    },
    "green": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#6fcf8a", "#a6d96a", "#5fd1c0", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#1f8a45", "#5f8a1f", "#14857a", "#a86b00", "#c93445"),
    },
    "yellow": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#e8c14f", "#e89f4f", "#7cc48a", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#946a00", "#a8501a", "#2f8a46", "#a86b00", "#c93445"),
    },
    "blue": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#6aa8f5", "#5ccfe0", "#7cc48a", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#1e66d0", "#0e8aa0", "#2f8a46", "#a86b00", "#c93445"),
    },
    "purple": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#b18af0", "#e08ad0", "#7cc48a", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#7a3fc4", "#b03f98", "#2f8a46", "#a86b00", "#c93445"),
    },
    "orange": {
        "dark": palette("#16181d", "#1f232a", "#2b313b", "#e6e8eb", "#8b93a1",
                        "#e8845a", "#f0b07a", "#7cc48a", "#e0b35c", "#ef7a85"),
        "light": palette("#f6f7f9", "#eceef2", "#dde1e8", "#1d2129", "#5f6773",
                         "#c2562a", "#a8731a", "#2f8a46", "#a86b00", "#c93445"),
    },
}
PRESET_NAMES = {"default": "Default", "red": "Red", "green": "Green", "yellow": "Yellow", "blue": "Blue", "purple": "Purple", "orange": "Orange"}


def luminance(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def complete(raw, source):
    """Keeps valid colours (#rrggbb) and fills the missing ones from the default
    preset, light or dark depending on the given background.
    Keys accepted in upper or lower case (BG / bg)."""
    raw = {str(k).upper(): v for k, v in raw.items()}
    valid = {}
    for k in KEYS:
        v = raw.get(k)
        if isinstance(v, str) and HEX.match(v):
            valid[k] = v
        elif v:
            warn(f"{source}: {k}={v!r} is not a #rrggbb colour, ignored")
    base = PRESETS["default"]["light" if "BG" in valid and luminance(valid["BG"]) > 0.5 else "dark"]
    return {k: valid.get(k, base[k]) for k in KEYS}


def choice(choice_id, name, dark, light):
    """Catalogue entry. A single variant -> fixed palette (no light/dark toggle)."""
    fixed = dark is None or light is None
    one = dark or light
    return {"id": choice_id, "name": name, "fixed": fixed,
            "palettes": {"dark": dark or one, "light": light or one}}


def preset_choice(name):
    return choice(f"preset:{name}", PRESET_NAMES.get(name, name), PRESETS[name]["dark"], PRESETS[name]["light"])


# ---------- TOML palettes (data only, never executed) ----------
def load_palette_toml(path, choice_id=None):
    path = Path(path)
    if path.suffix != ".toml" or not path.is_file():
        warn(f"palette not found or not a .toml file: {path}")
        return None
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        warn(f"unreadable palette ({path}): {e}")
        return None
    variants = {}
    for variant in ("dark", "light"):
        if isinstance(data.get(variant), dict):
            variants[variant] = complete(data[variant], f"{path} [{variant}]")
    if not variants:
        warn(f"{path}: neither [dark] nor [light], palette ignored")
        return None
    name = data.get("name") if isinstance(data.get("name"), str) else path.stem
    return choice(choice_id or f"file:{path}", name, variants.get("dark"), variants.get("light"))


def user_palettes(directory):
    if not directory or not Path(directory).is_dir():
        return []
    found = (load_palette_toml(p, f"user:{p.stem}") for p in sorted(Path(directory).glob("*.toml")))
    return [c for c in found if c]


# ---------- palette.sh (shell file, EXECUTED: only from the config) ----------
def palette_sh_path(cfg):
    path = cfg.get("path", "")
    if not path:
        return None
    if "{active}" in path:
        active_file = cfg.get("active_file", "")
        if not active_file:
            warn("palette_sh.path contains {active} but palette_sh.active_file is empty")
            return None
        try:
            path = path.replace("{active}", Path(active_file).expanduser().read_text().strip())
        except OSError as e:
            warn(f"unreadable palette_sh.active_file: {e}")
            return None
    return Path(path).expanduser()


def load_palette_sh(path):
    """Sources the file in bash (shell format KEY="#rrggbb"), as a theme script
    would, and keeps only our 10 keys. None if nothing usable."""
    if not path.is_file():
        warn(f"palette.sh not found: {path}")
        return None
    script = f'source "$1" >/dev/null 2>&1; for k in {" ".join(KEYS)}; do printf "%s\\t%s\\n" "$k" "${{!k}}"; done'
    try:
        out = subprocess.run(["bash", "-c", script, "_", str(path)],
                             capture_output=True, text=True, check=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError) as e:
        warn(f"unreadable palette.sh ({path}): {e}")
        return None
    raw = dict(line.split("\t", 1) for line in out.splitlines() if "\t" in line)
    # a file defining no valid colour must not become a "fixed" palette
    # entirely filled with the default one
    return raw if any(HEX.match(v) for v in raw.values()) else None


def palette_sh_choice(cfg):
    path = palette_sh_path(cfg)
    raw = load_palette_sh(path) if path else None
    if not raw:
        return None
    p = complete(raw, str(path))
    return choice("palette-sh", "System theme (palette.sh)", p, None)


# ---------- assembly ----------
def config_choice_id(preset, catalog_ids):
    """Config `preset` value -> catalogue id."""
    for candidate in ("palette-sh" if preset == "palette-sh" else None,
                      f"preset:{preset}", f"user:{preset}"):
        if candidate and candidate in catalog_ids:
            return candidate
    warn(f"palette {preset!r} not found (presets: {', '.join(PRESETS)}, personal palettes, palette-sh), using default")
    return "preset:default"


def resolve(theme_cfg, state=None, palettes_dir=None):
    """-> {"catalog", "selected", "config_selected", "mode", "translucent"}.
    selected = choice remembered from the window (state) if still valid,
    otherwise the config's."""
    state = state or {}
    catalog = [preset_choice(name) for name in PRESETS] + user_palettes(palettes_dir)
    sh_cfg = theme_cfg.get("palette_sh", {})
    if theme_cfg.get("preset") == "palette-sh" or sh_cfg.get("path"):
        sh = palette_sh_choice(sh_cfg)
        if sh:
            catalog.append(sh)

    ids = {c["id"] for c in catalog}
    config_selected = config_choice_id(theme_cfg.get("preset", "default"), ids)
    selected = config_selected
    saved = state.get("palette")
    if isinstance(saved, str):
        if saved in ids:
            selected = saved
        elif saved.startswith("file:"):
            extra = load_palette_toml(saved[len("file:"):])
            if extra:
                catalog.append(extra)
                selected = saved

    mode = state.get("mode") if state.get("mode") in MODES else theme_cfg.get("mode", "auto")
    if mode not in MODES:
        warn(f"theme.mode={mode!r} unknown (auto, dark, light), using auto")
        mode = "auto"
    return {"catalog": catalog, "selected": selected, "config_selected": config_selected,
            "mode": mode, "translucent": bool(theme_cfg.get("translucent"))}
