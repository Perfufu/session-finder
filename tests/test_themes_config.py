import json
import tomllib

import pytest

from session_finder import app, cli, config, engines, themes


@pytest.fixture
def xdg(tmp_path, monkeypatch):
    """Config and state isolated in a temporary directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path


def ids(theme):
    return [c["id"] for c in theme["catalog"]]


def by_id(theme, choice_id):
    return next(c for c in theme["catalog"] if c["id"] == choice_id)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ---------- presets ----------
@pytest.mark.parametrize("name", list(themes.PRESETS))
def test_presets_complete_and_valid(name):
    for variant in ("dark", "light"):
        p = themes.PRESETS[name][variant]
        assert list(p) == themes.KEYS
        assert all(themes.HEX.match(v) for v in p.values())
    # the dark background really is darker than the light one
    assert themes.luminance(themes.PRESETS[name]["dark"]["BG"]) < themes.luminance(themes.PRESETS[name]["light"]["BG"])


def test_default_catalogue():
    t = themes.resolve(config.DEFAULTS["theme"])
    assert ids(t) == [f"preset:{n}" for n in themes.PRESETS]
    assert t["selected"] == t["config_selected"] == "preset:default"
    assert t["mode"] == "auto" and not t["translucent"]


def test_unknown_preset_and_mode():
    t = themes.resolve({"preset": "unicorn", "mode": "neon"})
    assert t["selected"] == "preset:default" and t["mode"] == "auto"


# ---------- TOML palettes ----------
def test_toml_palette_two_variants_lowercase_keys(tmp_path):
    p = write(tmp_path / "pal.toml", 'name = "Mine"\n[dark]\nbg = "#101020"\naccent = "#ff00ff"\n'
                                     '[light]\nBG = "#fafafa"\n')
    c = themes.load_palette_toml(p)
    assert c["name"] == "Mine" and not c["fixed"] and c["id"] == f"file:{p}"
    assert (c["palettes"]["dark"]["BG"], c["palettes"]["dark"]["ACCENT"]) == ("#101020", "#ff00ff")
    assert c["palettes"]["light"]["BG"] == "#fafafa"
    # missing colours: default of the matching variant (light background -> light default)
    assert c["palettes"]["light"]["FG"] == themes.PRESETS["default"]["light"]["FG"]


def test_single_variant_toml_palette_is_fixed(tmp_path):
    c = themes.load_palette_toml(write(tmp_path / "solo.toml", '[dark]\nbg = "#000000"\n'))
    assert c["fixed"] and c["name"] == "solo"
    assert c["palettes"]["dark"] == c["palettes"]["light"]


def test_toml_palette_invalid_values_and_rejected_files(tmp_path):
    c = themes.load_palette_toml(write(tmp_path / "p.toml", '[dark]\nbg = "#fff;}body{"\nfg = 12\n'))
    assert c["palettes"]["dark"]["BG"] == themes.PRESETS["default"]["dark"]["BG"]
    assert c["palettes"]["dark"]["FG"] == themes.PRESETS["default"]["dark"]["FG"]
    assert themes.load_palette_toml(write(tmp_path / "empty.toml", 'name = "x"\n')) is None
    assert themes.load_palette_toml(write(tmp_path / "palette.sh", 'BG="#000000"\n')) is None  # never a .sh
    assert themes.load_palette_toml(write(tmp_path / "broken.toml", "[dark\n")) is None


def test_personal_palettes_in_catalogue_and_config(tmp_path):
    d = tmp_path / "palettes"
    write(d / "mine.toml", 'name = "My own"\n[dark]\nbg = "#111111"\n')
    t = themes.resolve({"preset": "mine"}, palettes_dir=d)
    assert "user:mine" in ids(t)
    assert t["selected"] == "user:mine"


# ---------- remembered choice (window) vs config ----------
def test_remembered_choice_wins_over_config():
    t = themes.resolve({"preset": "green", "mode": "auto"}, state={"palette": "preset:orange", "mode": "light"})
    assert t["config_selected"] == "preset:green"
    assert t["selected"] == "preset:orange" and t["mode"] == "light"


def test_remembered_file_choice_and_stale_choice(tmp_path):
    f = write(tmp_path / "elsewhere.toml", '[dark]\nbg = "#222222"\n')
    t = themes.resolve({"preset": "default"}, state={"palette": f"file:{f}"})
    assert t["selected"] == f"file:{f}" and by_id(t, f"file:{f}")["palettes"]["dark"]["BG"] == "#222222"
    f.unlink()  # file gone since: back to the config, no error
    assert themes.resolve({"preset": "default"}, state={"palette": f"file:{f}"})["selected"] == "preset:default"
    assert themes.resolve({"preset": "green"}, state={"palette": "user:deleted"})["selected"] == "preset:green"


# ---------- palette.sh (config only) ----------
def test_palette_sh_with_active_theme(tmp_path):
    write(tmp_path / "themes" / "galaxy" / "palette.sh",
          'BG="#101020"\nFG="#eeeeee"\nACCENT="#ff00ff"  # comment\nERROR="red"\nWARNING="#fff;}body{"\n')
    write(tmp_path / "active", "galaxy\n")
    t = themes.resolve({"preset": "palette-sh", "palette_sh": {
        "path": str(tmp_path / "themes" / "{active}" / "palette.sh"),
        "active_file": str(tmp_path / "active")}})
    sh = by_id(t, "palette-sh")
    assert t["selected"] == "palette-sh" and sh["fixed"]
    p = sh["palettes"]["dark"]
    assert (p["BG"], p["ACCENT"]) == ("#101020", "#ff00ff")
    # invalid values (including a CSS injection attempt) replaced with the dark default
    assert p["ERROR"] == themes.PRESETS["default"]["dark"]["ERROR"]
    assert p["WARNING"] == themes.PRESETS["default"]["dark"]["WARNING"]


def test_palette_sh_missing_or_not_configured(tmp_path):
    t = themes.resolve({"preset": "palette-sh", "palette_sh": {"path": str(tmp_path / "nope.sh")}})
    assert "palette-sh" not in ids(t) and t["selected"] == "preset:default"
    assert "palette-sh" not in ids(themes.resolve(config.DEFAULTS["theme"]))


# ---------- config ----------
def test_config_template_matches_defaults():
    """config.example.toml documents exactly the code's default values."""
    assert tomllib.loads(config.example("config.example.toml")) == config.DEFAULTS


def test_palette_template_is_valid(tmp_path):
    c = themes.load_palette_toml(write(tmp_path / "m.toml", config.example("palette.example.toml")))
    assert c["palettes"] == themes.PRESETS["default"]


def test_missing_config(tmp_path):
    assert config.load(tmp_path / "missing.toml") == config.DEFAULTS


def test_config_merge_and_types(tmp_path):
    f = write(tmp_path / "config.toml",
              '[theme]\npreset = "green"\ntranslucent = "yes"\nunknown = 1\n[terminal]\ncommand = "foot"\n')
    cfg = config.load(f)
    assert cfg["theme"]["preset"] == "green"
    assert cfg["theme"]["translucent"] is False  # wrong type: default kept
    assert "unknown" not in cfg["theme"]
    assert cfg["terminal"]["command"] == "foot"


def test_invalid_config(tmp_path):
    assert config.load(write(tmp_path / "config.toml", "[theme\npreset = ")) == config.DEFAULTS


# ---------- --init-config / --new-palette commands ----------
def test_init_config_creates_then_refuses_to_overwrite(xdg):
    assert cli.main(["--init-config"]) == 0
    assert config.config_path().read_text() == config.example("config.example.toml")
    config.config_path().write_text('[theme]\npreset = "green"\n')
    assert cli.main(["--init-config"]) == 1
    assert config.config_path().read_text() == '[theme]\npreset = "green"\n'


def test_install_desktop_creates_then_refuses_to_overwrite(xdg, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg / "data"))
    monkeypatch.setattr("sys.argv", ["/opt/my tools/session-finder"])
    assert cli.main(["--install-desktop"]) == 0
    target = config.applications_dir() / "session-finder.desktop"
    text = target.read_text()
    assert 'Exec="/opt/my tools/session-finder"' in text and "@EXEC@" not in text
    assert "StartupWMClass=" + app.APP_ID in text
    target.write_text("mine")
    assert cli.main(["--install-desktop"]) == 1
    assert target.read_text() == "mine"


def test_new_palette(xdg):
    assert cli.main(["--new-palette", "my-palette"]) == 0
    t = themes.resolve(config.DEFAULTS["theme"], palettes_dir=config.palettes_dir())
    assert by_id(t, "user:my-palette")["name"] == "my-palette"
    assert cli.main(["--new-palette", "my-palette"]) == 1         # no overwrite
    assert cli.main(["--new-palette", "../escape"]) == 2          # stays inside palettes/
    assert not (config.config_dir() / "escape.toml").exists()


# ---------- remembered state ----------
def test_remembered_choices_and_default_view(xdg):
    api = app.Api(terminal=None)
    api.set_palette("preset:green")
    api.set_mode("light")
    assert json.loads(app.state_path().read_text()) == {"palette": "preset:green", "mode": "light"}
    api.set_palette(None)  # back to the config
    assert json.loads(app.state_path().read_text()) == {"mode": "light"}

    default_view = app.Api(terminal=None, persist=False)  # --defaults: nothing is written
    default_view.set_palette("preset:orange")
    default_view.set_mode("dark")
    assert json.loads(app.state_path().read_text()) == {"mode": "light"}


# ---------- window engine ----------
@pytest.mark.parametrize("gtk,qt,preferred,expected", [
    (True, True, "auto", "gtk"),     # GTK preferred when usable
    (False, True, "auto", "qt"),     # otherwise bundled Qt
    (True, True, "qt", "qt"),        # forced
    (False, False, "auto", None),
    (True, False, "qt", None),       # forced but not installed
])
def test_engine_choice(monkeypatch, gtk, qt, preferred, expected):
    monkeypatch.setattr(engines, "gtk_usable", lambda: gtk)
    monkeypatch.setattr(engines, "qt_usable", lambda: qt)
    engine, reason = engines.choose(preferred)
    assert engine == expected and (reason is None) == (expected is not None)


def test_no_engine_prints_install_help(monkeypatch, capsys):
    monkeypatch.setattr(engines, "gtk_usable", lambda: False)
    monkeypatch.setattr(engines, "qt_usable", lambda: False)
    assert cli.main([]) == 1
    err = capsys.readouterr().err
    assert "session-finder[qt]" in err and "--table" in err
