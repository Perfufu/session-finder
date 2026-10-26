# Instructions for Claude — Session Finder for Claude Code

Tool that lists every Claude Code conversation (whichever folder it was started from), shows them as a **per-folder graph + list + search**, and reopens the chosen one in a terminal in the right place (`claude --resume`). User documentation: `README.md`.

This file is the project's source of truth (architecture, conventions, decisions, roadmap): no need to reread past conversations. **The repository is generic**: nothing specific to one machine or user goes in (no personal paths, no personal config — personalisation goes through the user config, outside the repo).

## Scope

**Purpose, in one sentence**: see every Claude Code conversation, whichever folder it was started from, and reopen one in the right place. Session Finder is the *history* you consult to find something again (an ongoing task, a piece of information that went by) — not a dashboard of ongoing work.

**Goal: a finished object.** The aim is a tool that is complete and stable, not an ever-growing platform. "Done" means the purpose above is served well (fast, reliable, portable, documented); after that, only fixes, compatibility with Claude Code changes, and requests that pass the test below.

**Test for any new feature** — all three answers must be yes:
1. Does it help find or resume a conversation?
2. Does it work from `~/.claude` alone, offline, read-only?
3. Does it work without a daemon or any state to keep in sync?

A feature that fails one goes to *Out of scope*, or to another project.

**Out of scope** (decided; reopening one needs a new explicit decision recorded in *Decisions*):
- Supervision / "control tower": live state of running sessions, git state of projects (dirty tree, unpushed commits), merge requests, issue trackers, anything needing the network or a forge login.
- Being the client of a daemon, or running one.
- Acting on a folder rather than on a conversation (e.g. opening several terminals in it).
- Running inside Claude Code (mods/plugins): a mod lives in one session, this tool is global.

**Bricks, not a monolith.** The tool is standalone and complete on its own. A bridge to another tool is allowed only if it is **optional** (works identically when the other tool is absent), **one-way and read-only**, and detected at runtime (like `niri.py`). Another project can use Session Finder's data or be used by it; neither may become required for the other to make sense. Supporting another AI tool's conversations (roadmap 4) stays an idea until it can be expressed as a source behind the same finder purpose.

## Commands

```sh
uv venv --system-site-packages --python /usr/bin/python3   # sees the system's pywebview + GTK
uv pip install -e . pytest
.venv/bin/session-finder              # window (user view: their config, palettes, choices)
.venv/bin/session-finder --defaults   # a new user's view (writes nothing)
.venv/bin/session-finder --engine qt  # force an engine (auto | gtk | qt)
.venv/bin/session-finder --table      # quick check in the terminal (--all: also the sessions hidden by [sessions])
.venv/bin/pytest -q                   # 82 tests
```

Testing the self-contained Qt engine like a user without system packages: a separate venv **without** `--system-site-packages` (e.g. `uv venv --python 3.13 /tmp/qtenv && VIRTUAL_ENV=/tmp/qtenv uv pip install -e ".[qt]"`).

## Architecture (`src/session_finder/`)

| File | Role |
|---|---|
| `index.py` | **Read-only** scan of `<claude>/projects/*/*.jsonl` (`CLAUDE_CONFIG_DIR` honoured), cache `~/.cache/session-finder/` invalidated by (mtime, size; `CACHE_VERSION` bumped when a parsed field is added). Per session: `non_interactive` (from `entrypoint`), `hidden` + `hidden_reason` (`excluded` / `non-interactive`, from the config only), `no_reply` |
| `config.py` | `~/.config/session-finder/config.toml` (defaults if missing/invalid; `[sessions]` → `hiding()` feeds `build_index`); shipped templates copied, never overwriting; `LANGUAGES` + `resolve_language` |
| `session-finder.desktop`, `session-finder.svg` | Launcher entry template + icon (default dark preset colours, installed under `~/.local/share/icons/hicolor/scalable/apps/`) (`@EXEC@` filled in by `--install-desktop`: absolute path, since launchers often lack `~/.local/bin`); `StartupWMClass` must equal `APP_ID` |
| `config.example.toml`, `palette.example.toml` | Commented templates (`--init-config`, `--new-palette NAME`); a test guarantees the config template = `DEFAULTS` |
| `themes.py` | Palette catalogue: built-in `preset:*` (default + red/green/yellow/blue/purple/orange: shared neutral backgrounds, only the accent pair differs), `user:*` (`palettes/*.toml`), `file:*` ("Other…"), `palette-sh` (config only); colours validated as `#rrggbb` |
| `launchers.py` | Terminal: config > `$TERMINAL` > detection (9 known, unknown = `-e`); fish handled |
| `niri.py` | Optional (detected through `NIRI_SOCKET`): focus an already-open session, single instance |
| `engines.py` | Window engine: `gtk` (system WebKitGTK) preferred when usable, else `qt` (bundled Qt WebEngine, extra `[qt]`); sets the Wayland app-id per toolkit |
| `uninstall.py` | `--uninstall`: lists then deletes (confirmation, or `--yes`) the fixed paths the tool wrote: config dir, cache dir, state dir, `.desktop` + icon, lock file; never `~/.claude`; prints `uv tool uninstall session-finder` for the last step (a running program does not delete its own environment) |
| `report.py` | `--report`: diagnostic block for bug reports (versions, system, engine, Claude Code version of the newest conversations); never a path or conversation content (a test checks it) |
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
- **Languages**: `[ui] language` = `auto` (system locale: `LC_ALL` > `LC_MESSAGES` > `LANG`, English if unsupported) / `en` / `fr`, resolved in Python (testable) and passed as `data.language`. **Language menu** in the window (same pattern as the Palette menu: `.popup-menu`, one entry per `STRINGS` language + "System language"), applied instantly via `applyLanguage()` (re-applies the static texts, buttons, hint and re-renders), remembered in the state (`set_language`), never in `config.toml`; priority window choice > config > system. A new language appears in the menu by itself (`STRINGS.<code>.name`). Any text set once at startup must be re-applied in `applyLanguage()`. `T = {...STRINGS.en, ...STRINGS[language]}`: a missing key falls back to English. Python/CLI messages stay English. A test keeps `STRINGS` languages = `config.LANGUAGES` and every translation's keys (and function-ness) = English's.
- **Hidden sessions** (roadmap 7/8). The filter hides **only what the config asks for**, nothing else: `[sessions] hide_non_interactive` (default **true**) and `exclude_folders` (folder + subfolders, `~` expanded). `claude -p` is detected from the `entrypoint` field on each `.jsonl` line: `cli` = interactive, `sdk-cli` = `-p`, `sdk-ts` / `sdk-py` = Agent SDK (values read in the claude 2.1.294 binary, **and checked by running a real `claude -p`**); missing or unknown = interactive. The window receives every session, flagged (`hidden`, `hidden_reason`), and the **eye button** next to the search box shows/hides the hidden ones live (graph rebuilt, node positions kept, reframed after settling), remembered in the state (`set_show_hidden`), greyed when nothing is hidden; `--all` does the same in the CLI. Default first chosen as "visible", then switched to **hidden by default** after seeing the eye do nothing with the default config: an eye that has nothing to toggle is a trap.
- **"No reply" is a mark, not a filter**: a conversation Claude never answered (offline, API error…) is **never hidden**; it gets `no_reply` → warning triangle + greyed title in the list, greyed triangle node with a "!" in the graph, a legend line (only when one exists). Not flagged while the session is open (just started). Colour = the palette's `WARNING` (never the accent: a red preset would be confusable). A conversation with no user and no assistant message (empty shell) is not listed. Rule behind both: a filter does one thing; anything else that shows up must be explained, not silently filtered.
- **Fuzzy search** (roadmap 9): exact substring first; only when it finds nothing, a per-word approximate substring match (Sellers / Levenshtein, budget 0 edits under 4 letters, 1 from 4, 2 from 7). No indicator that results are approximate (could be added). `fuzzyIncludes` sits between `FUZZY-BEGIN`/`FUZZY-END` in `app.js` so `tests/test_ui.py` can run it with node.
- **Uninstall**: `--uninstall` (+ `--yes`) removes everything the tool wrote outside its uv environment, then points to `uv tool uninstall session-finder` (see `uninstall.py`).
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

1. ~~`.desktop` file~~ — **done** (`--install-desktop`, user-level, never overwrites).
2. ~~Defensive reading~~ — **abandoned** (decision: no version-based warning). Idea was: warn when sessions written by a Claude Code version newer than the last tested one lack `cwd`/`timestamp`. Rejected because it needs a hard-coded "last tested version" constant that someone must bump on every release, with no automatic reminder: forgotten, the warning becomes wrong or silent. The reading is already defensive (truncated lines, missing fields: nothing crashes). Cheap fallback if ever wanted: warn on anomalies alone (answered sessions with no `cwd`/`timestamp`: 0 on 56 real sessions with 2.1.276/2.1.294), no version involved. Replaced by guidance for users to report problems: README section, `.github/ISSUE_TEMPLATE/`, `--report`.
3. ~~French translation~~ — **done**, see Decisions.
4. **Idea, for later (a possible "DLC", only once the base project is finished — or never)** — other AI tools as "sources": only `index.py` (reading `~/.claude`) and the resume command (`claude --resume`) are specific to Claude Code; graph, list, search, palettes and terminal launchers are not. Supporting another CLI tool (Dust CLI, console ChatGPT clients…) = a source interface: list its conversations (id, folder, title, dates, running state) + the command that resumes one. The "for Claude Code" name would then become too narrow. **Stays an idea** until it can be expressed as a source behind the same finder purpose (see Scope); nothing to do before then.
5. ~~JS safety net~~ — **done**, see Decisions.
6. **Open question — launcher entry discoverability**: `--install-desktop` is one explicit command (a wheel cannot write to `~/.local/share`, `uv tool upgrade` runs no hook). Option under consideration: a discreet startup hint when the entry is missing (more discoverable, but chattier, needs a way to silence it). **Pending feedback from the target users** (colleagues, friends) — decide after that.
7. ~~Exclude folders~~ — **done** (`[sessions] exclude_folders`), see Decisions.
8. ~~Hide non-interactive sessions (`claude -p`)~~ — **done** (`entrypoint` is reliable, verified with a real run), see Decisions.
9. ~~Fuzzy matching in the search~~ — **done**, see Decisions.
10. ~~README: try without installing~~ — **done** (`uvx "session-finder[qt] @ git+…"` works as is, no `--from` needed; tested in a throw-away `UV_CACHE_DIR`: qt engine detected, ~670 MB; README warns against `--install-desktop` under uvx).

Ideas received and ruled out (control tower, daemon client, mods, opening several terminals in a folder): see **Scope → Out of scope**; not repeated here.
