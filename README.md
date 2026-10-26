# Session Finder for Claude Code

> *It was going to be called **CSV** — Claude Session Visualizer. Then we remembered a spreadsheet format had already taken the name.*

Find and resume your Claude Code conversations, **whichever folder they were started from**.

`claude --resume` only lists the conversations of the current folder. Session Finder lists all of them as a **per-folder graph** (like Obsidian's graph view) + a **searchable list**, and reopens the chosen conversation in a terminal, in the right place.

## Speedrun

Don't read READMEs? Same, honestly. Linux, self-contained install (details below if something breaks):

```sh
# Install (copy-paste the whole block)
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"     # uv was maybe just installed: make it visible now
uv tool install "session-finder[qt] @ git+https://github.com/Perfufu/session-finder"
session-finder --install-desktop         # optional: launcher entry + icon (fuzzel, rofi, GNOME, KDE…)
session-finder

# Update (later)
uv tool upgrade session-finder

# Uninstall (later)
session-finder --uninstall && uv tool uninstall session-finder
```

## What it does

- **Graph**: launch folders form a tree, each conversation is a dot attached to its folder. Size = conversation length, colour = age, animated aura = conversation currently open.
- **Search** (title, messages, path, git branch), case- and accent-insensitive. When nothing matches exactly, it falls back to a typo-tolerant match (one slip allowed from 4 letters, two from 7).
- **Hidden conversations**: `claude -p` runs (non-interactive) and folders you exclude are hidden by default; the **eye button** next to the search box shows them (see [Configuration](#configuration)).
- **Conversations that went wrong**: one Claude never answered (offline, API error…) stays in the list with a ⚠ triangle and a greyed title (a triangle node in the graph), so you can still reopen it.
- **Click a folder**: filters the list to that folder.
- **Resume** (Enter, double-click or button): opens a terminal in the conversation's folder running `claude --resume <id>`; when you quit Claude, you stay in a shell there.
- **Palettes**: built-in presets, personal palettes, light/dark — picked right in the window.
- **Keyboard**: ↑↓ select · Enter resume · Esc clears the search / filter, then **twice** to close.

## Privacy

Everything stays local. Session Finder **reads** Claude Code's folder (`~/.claude`, or `$CLAUDE_CONFIG_DIR`) and **never writes to it**. No network access: the graph library ([force-graph](https://github.com/vasturiano/force-graph), MIT) is bundled (see `src/session_finder/vendor/README.md`).

## Installation (Linux)

Needs [uv](https://docs.astral.sh/uv/) (step 1 below installs it if you don't have it). Two window engines, picked automatically:

### Self-contained (any distro, any window manager)

```sh
# 1. uv, only if missing (official installer, installs to ~/.local/bin)
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Session Finder
uv tool install "session-finder[qt] @ git+https://github.com/Perfufu/session-finder"

# 3. Optional: launcher entry + icon (fuzzel, rofi, GNOME/KDE menus…), see "Launcher entry" below
session-finder --install-desktop

session-finder
```

If `uv` is still "not found" right after installing it, open a new terminal (or `export PATH="$HOME/.local/bin:$PATH"`): its install directory was not yet in your `PATH`.

Brings its own Python and Qt WebEngine: nothing to install with your package manager, nothing to compile, no browser. About 650 MB once installed (~140 MB download). Requires glibc ≥ 2.34 (Debian 12+, Ubuntu 22.04+, Fedora 35+, Arch…).

**Updating**: `uv tool upgrade session-finder` (the tool lives in its own uv-managed environment, so your package manager won't touch it).

**Launcher entry** (fuzzel, rofi, wofi, GNOME/KDE menus…): `session-finder --install-desktop` writes `~/.local/share/applications/session-finder.desktop` and the icon `~/.local/share/icons/hicolor/scalable/apps/session-finder.svg` (never overwrites; delete it to regenerate, e.g. if you move the command). It uses the command's absolute path, because launchers often lack `~/.local/bin` in their `PATH`.

### Uninstalling

```sh
session-finder --uninstall        # lists what it will delete, asks, then deletes
uv tool uninstall session-finder  # removes the program itself
```

`uv tool uninstall` alone only removes the program: your config, personal palettes, cache, remembered choices and launcher entry would stay behind. `--uninstall` deletes exactly these (it prints the list first; `--yes` skips the question): `~/.config/session-finder/`, `~/.cache/session-finder/`, `~/.local/state/session-finder/`, and the launcher entry and icon under `~/.local/share/` if you ran `--install-desktop`. Run it **before** `uv tool uninstall`, since it needs the command. It never touches Claude Code or your conversations (`~/.claude`). If you made an alias or shortcut, remove it yourself.

### System WebKitGTK (lighter, if you already have it)

On Arch:

```sh
sudo pacman -S --needed python-pywebview webkit2gtk-4.1
git clone https://github.com/Perfufu/session-finder && cd session-finder
uv venv --system-site-packages --python /usr/bin/python3   # sees the system's pywebview/GTK
uv pip install -e .
.venv/bin/session-finder
```

To update this variant: `git pull` in the clone (the install is editable).

With both available, GTK is preferred; `--engine qt` or `--engine gtk` forces one. Without any engine, the list is still available in the terminal: `session-finder --table`.

### Command, alias, shortcut

The command is `session-finder`. A shorter alias or a keyboard shortcut is **up to you**, depending on your setup. Note: `sf` is already the Salesforce CLI command.

On Wayland the window's app-id is **`session-finder`**: that is the target of a "floating window" rule in your window manager (Hyprland, Sway, niri…).

## Keep your conversations

By default, **Claude Code deletes conversations inactive for 30 days** — Session Finder can only show what is still on disk. To keep them much longer, set `cleanupPeriodDays` in `~/.claude/settings.json`, for example:

```json
{ "cleanupPeriodDays": 36500 }
```

There is no "never" value: `0` is rejected (it used to silently disable saving conversations altogether), so use a large number (36500 days = 100 years).

## Configuration

Optional. To start from a commented template:

```sh
session-finder --init-config      # creates ~/.config/session-finder/config.toml (never overwrites)
```

Every option is explained in it: language, palette, light/dark, translucent background, terminal. A missing or invalid file never prevents anything from working (defaults + a warning).

- **Language**: the **Language menu** in the window (top right, e.g. `FR ▾`) switches instantly and is remembered. Default: your system locale (`[ui] language` = `"auto"`, `"en"` or `"fr"` in the config; the window's choice takes precedence). The window is translated; terminal messages (`--help`, errors) stay in English. Missing a language? A translation is one more object in `STRINGS` (top of `ui/app.js`) plus its code in `LANGUAGES` (`config.py`): pull requests welcome.
- **Hidden conversations** (`[sessions]`): `hide_non_interactive` (default `true`) hides conversations started with `claude -p` or the Agent SDK, detected from the `entrypoint` Claude Code writes in each conversation file (`sdk-cli`, `sdk-ts`, `sdk-py`); `exclude_folders = ["~/scripts/nightly"]` hides every conversation started in these folders and their subfolders. Nothing is deleted: the **eye button** next to the search box (remembered between launches; greyed when nothing is hidden) or `session-finder --table --all` shows them again. Set `hide_non_interactive = false` to list `claude -p` runs like any other conversation.
- **Terminal**: `[terminal] command`, otherwise `$TERMINAL`, otherwise the first one found among kitty, ghostty, foot, alacritty, wezterm, gnome-terminal, konsole, xfce4-terminal, xterm.
- **Translucent background**: only if your compositor blurs what is behind windows, otherwise text gets hard to read.

## Palettes

The window's **Palette** menu offers:

- the **presets**: Default, Red, Green, Yellow, Blue, Purple, Orange — same neutral backgrounds, only the accent changes (each in light and dark — ◐ button next to it);
- **your palettes**, dropped in `~/.config/session-finder/palettes/`;
- **Other…**: open a `.toml` palette file from anywhere.

The choice made in the window is remembered and takes precedence over the config ("Back to config" entry to undo it). Your `config.toml` is never modified by the tool.

### Make your own palette

```sh
session-finder --new-palette my-palette   # creates ~/.config/session-finder/palettes/my-palette.toml
```

The created file is commented: 10 colours as `"#rrggbb"`, in a `[dark]` and/or `[light]` section (with only one of them, the light/dark toggle is hidden). A missing or invalid colour falls back to the default palette's. A palette file only holds data: it is never executed.

### Reuse the colours of a shell-based theme system

If your colours already live in a shell file (`BG="#…"`, `FG="#…"`…), `preset = "palette-sh"` + `[theme.palette_sh]` in the config reads them directly (details in the config template). ⚠ That file is **executed** by bash: this option only exists in the config, never through "Other…".

## See the tool as a new user would

```sh
session-finder --defaults
```

Ignores your config, palettes and remembered choices, and saves nothing: the tool as it looks right after installation. Handy for testing or a demo.

## Under niri

Detected automatically: resuming a conversation that is **already open** brings its window to the front instead of starting it twice, and relaunching Session Finder brings the existing window back. Elsewhere, an already-open conversation is simply flagged.

## Tests

```sh
uv pip install pytest && .venv/bin/pytest
```

The tests use an entirely fictional Claude Code folder (`tests/conftest.py`).

## Reporting a problem / feedback

Something broken, confusing, or missing? [Open an issue](https://github.com/Perfufu/session-finder/issues/new/choose): there are templates for a bug report and for feedback / ideas. Short and rough is fine.

For a bug, run `session-finder --report` and paste its output: versions, system, window engine, Claude Code version. It contains **no path and no conversation content** (it is worth a glance before pasting anyway). If an error popup showed up, include its text. `session-finder --debug` opens the window with developer tools.

## Known limitations

- The conversation file format (`~/.claude/projects/*/*.jsonl`) is **internal to Claude Code and undocumented**: it is read defensively, but a Claude Code update may change it. If sessions look wrong or missing after a Claude Code update, please [report it](#reporting-a-problem--feedback).
- Linux only for now. The interface is available in English and French.
