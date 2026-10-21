# Instructions for Claude — Session Finder for Claude Code

Tool that lists every Claude Code conversation (whichever folder it was started from), shows them as a **per-folder graph + list + search**, and reopens the chosen one in a terminal in the right place (`claude --resume`). User documentation: `README.md`.

This file is the project's source of truth (architecture, conventions, decisions, roadmap): no need to reread past conversations. **The repository is generic**: nothing specific to one machine or user goes in (no personal paths, no personal config — personalisation goes through the user config, outside the repo).

## Commands

```sh
uv venv --system-site-packages --python /usr/bin/python3   # sees the system's pywebview + GTK
uv pip install -e . pytest
.venv/bin/session-finder              # window (user view: their config, palettes, choices)
.venv/bin/session-finder --defaults   # a new user's view (writes nothing)
.venv/bin/session-finder --engine qt  # force an engine (auto | gtk | qt)
.venv/bin/session-finder --table      # quick check in the terminal (--all: hidden sessions)
.venv/bin/pytest -q                   # 54 tests
```

Testing the self-contained Qt engine like a user without system packages: a separate venv **without** `--system-site-packages` (e.g. `uv venv --python 3.13 /tmp/qtenv && VIRTUAL_ENV=/tmp/qtenv uv pip install -e ".[qt]"`).

## Architecture (`src/session_finder/`)

| File | Role |
|---|---|
| `index.py` | **Read-only** scan of `<claude>/projects/*/*.jsonl` (`CLAUDE_CONFIG_DIR` honoured), cache `~/.cache/session-finder/` invalidated by (mtime, size) |
| `config.py` | `~/.config/session-finder/config.toml` (defaults if missing/invalid); shipped templates copied, never overwriting |
| `config.example.toml`, `palette.example.toml` | Commented templates (`--init-config`, `--new-palette NAME`); a test guarantees the config template = `DEFAULTS` |
| `themes.py` | Palette catalogue: built-in `preset:*` (default + red/green/yellow/blue/purple/orange: shared neutral backgrounds, only the accent pair differs), `user:*` (`palettes/*.toml`), `file:*` ("Other…"), `palette-sh` (config only); colours validated as `#rrggbb` |
| `launchers.py` | Terminal: config > `$TERMINAL` > detection (9 known, unknown = `-e`); fish handled |
| `niri.py` | Optional (detected through `NIRI_SOCKET`): focus an already-open session, single instance |
| `engines.py` | Window engine: `gtk` (system WebKitGTK) preferred when usable, else `qt` (bundled Qt WebEngine, extra `[qt]`); sets the Wayland app-id per toolkit |
| `app.py` / `cli.py` | pywebview window (page assembled in memory, no server; state `~/.local/state/session-finder/`) / `session-finder` command |
| `ui/`, `vendor/` | HTML/CSS/JS interface (no hard-coded colour; **all user-facing text in `STRINGS` at the top of `app.js`** + `data-i18n*` attributes) + bundled force-graph 1.51.4 (provenance: `vendor/README.md`) |

**Colour settings priority**: choice made in the window (state) > `config.toml` > defaults. The tool **never** writes `config.toml`.

## Conventions

- **Dependency-free core** (standard library only); the window engine is the only external dependency (system GTK, or the `[qt]` extra).
- **Everything in English** (code, comments, messages, docs). UI strings only in `STRINGS` (a translation = one more language object); Python messages inline.
- **Never a real conversation in the repo**: tests use a fictional fake `~/.claude` (`tests/conftest.py`).
- **Never write to `~/.claude`.** Manual / load tests: fake folder through `CLAUDE_CONFIG_DIR` + `XDG_CACHE_HOME`/`XDG_STATE_HOME`/`XDG_CONFIG_HOME` pointing to a temporary directory, terminal set to `true` (no real resume possible), deleted afterwards.
- **Nothing executable from a UI choice**: "Other…" only accepts `.toml` (data); `palette-sh` (sourced by bash) only exists through the hand-written config.
- The session id is never concatenated into a shell command (positional argument, regex-validated). Palette names filtered (`[A-Za-z0-9_-]`).
- A bundled/pinned dependency = a release with some hindsight (≥ 2 weeks, not the one published right after a long gap), integrity checked against the registry, audit (network/eval) for vendored code, provenance in `vendor/README.md`. PySide6 pinned to 6.11.2 (6.12.0 was 11 days old).
- `.jsonl` format internal to Claude Code, undocumented: defensive reading everywhere.
- Personalisation = **config option**, never machine-specific code.

## Decisions

- **Name**: *Session Finder for Claude Code* ("for Claude Code" rather than "Claude X": Anthropic trademark). Command `session-finder`; alias (`sf` = Salesforce CLI, avoided by default) and keyboard shortcut left to each user. *CSV — Claude Session Visualizer* joke kept in the README.
- **Linux first.** Remote client/server rejected (sending one's transcripts elsewhere, no benefit).
- **One generic codebase + user config**, rather than "personal" / "generic" branches: the code does not differ, only the config; `--defaults` shows a new user's view.
- **Window engine**: no browser, whatever the window manager. System GTK when available; **otherwise bundled Qt via `uv`** (`[qt]` extra: own Python + PySide6/Qt WebEngine). Rejected: Flatpak (sandbox to open almost entirely: host terminal, `~/.claude`), WebKitGTK AppImage (fragile across distros). Reason: PyGObject only exists as source on PyPI and `uv tool install` cannot see system packages.
- **Personal palettes in TOML** (data only), Palette menu in the window with instant preview.
- **Animations** kept as they are despite the CPU cost below.
- **Opaque background by default**, translucent as an option.
- **No icon-font glyph in the UI**: the folder icon is a vector (`FOLDER_PATH` Path2D in the graph, `.folder-ico` CSS mask in the DOM). A Nerd Font codepoint showed as an empty rectangle on machines without that font.
- **Presets**: one neutral dark/light background shared by all, only `ACCENT`/`ACCENT_ALT` change (distinct character per preset); `green` moves `SUCCESS` to teal so open sessions stay distinguishable.
- **uv install**: README documents `command -v uv || curl … astral.sh/uv/install.sh | sh` (no install script in the repo) + the `PATH` pitfall.
- **JS safety net**: a tiny inline script in `index.html` (separate from `app.js`, since a syntax error there runs none of its code) catches `error` / `unhandledrejection` and shows an English popup with message + stack (fallback `file:line:col`: the stack can be empty). Only the first error is shown. Before `app.js` has finished (`window.__appReady` set on its last line) = **Close only** (nothing usable); afterwards = **Close / Continue** (the error may be harmless; after Continue, silence). Popup text lives in `STRINGS` with an identical English fallback inline (a test keeps them in sync). `tests/test_ui.py` runs `node --check` on `app.js` and the inline scripts (skipped without `node`).

## Measured facts (dev laptop, Arch + niri)

- Index: 1000 sessions from cache **0.11 s**; cold ~8 ms/MB of `.jsonl` (real sessions average ~0.9 MB because of base64 images → ~7 s for 1000, once). Data injected into the page: ~700 KB for 1000 sessions.
- **Idle CPU, WebKitGTK: any continuous animation costs ~60 % of a core, even a single circle** (static page: 0 %). Graph: ~92 % (52 sessions), ~135 % (1000) as measured with `top`. `autoPauseRedraw(true)` does not stop it; only `fg.pauseAnimation()` does (→ ~10 %). Window size/floating has no effect.
- **Same window, Qt WebEngine vs WebKitGTK** (51 sessions, measured over the whole process tree via `/proc`): **~25 % vs ~40 %**.
- `[qt]` install: ~650 MB on disk (~140 MB download). Harmless Qt warnings at startup: Vulkan driver not found (falls back), portal "App info not found for 'session-finder'" (no `.desktop` file).
- `auto` mode: with GNOME's `color-scheme` on `'default'`, WebKit thinks the system is light.
- **Claude Code deletes conversations inactive for 30 days by default** (`cleanupPeriodDays`, integer ≥ 1, no maximum; `0` rejected because it used to disable transcript writes). Documented in the README.

## Roadmap

Public repository: https://github.com/Perfufu/session-finder (MIT). Before each push, check that nothing personal is left (home paths, names, emails) and that `git add -n .` only lists intended files. Bug reports and merge requests are where details about other people's machines belong — not in this file.

1. **`.desktop` file** (`session-finder.desktop`): shows the tool in launchers (fuzzel, rofi…) and silences the Qt portal warning.
2. **Defensive reading**: record the Claude Code versions tested (`version` field of `.jsonl` lines); discreet warning if a newer version gives inconsistent results.
3. **French translation**: `STRINGS.fr` in `app.js` + language choice (config / system locale); Python messages to wrap if needed.
4. **Idea — other AI tools as "sources"**: only `index.py` (reading `~/.claude`) and the resume command (`claude --resume`) are specific to Claude Code; graph, list, search, palettes and terminal launchers are not. Supporting another CLI tool (Dust CLI, console ChatGPT clients…) = a source interface: list its conversations (id, folder, title, dates, running state) + the command that resumes one. The "for Claude Code" name would then become too narrow.
5. ~~JS safety net~~ — **done**, see Decisions.
