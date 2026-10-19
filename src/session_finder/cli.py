"""Entry point of the `session-finder` command."""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from . import __version__, config, engines, index

PALETTE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")  # no "/" nor "..": stays inside palettes/


def short(path):
    if not path:
        return "?"
    home = str(Path.home())
    return "~" + path[len(home):] if path == home or path.startswith(home + "/") else path


def local_time(iso):
    """.jsonl timestamps are UTC (Z suffix): convert to local time."""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return " " * 16


def print_table(sessions):
    current = object()
    for s in sessions:
        if s["cwd"] != current:
            current = s["cwd"]
            flag = "" if s["cwd_exists"] else "   ⚠ folder not found"
            print(f"\n{short(current)}{flag}")
        mark = {"custom": "✎", "ai": " ", "prompt": "?"}[s["title_source"]]
        run = f"  ● {s['running']}" if s["running"] else ""
        hidden = "  (hidden: no reply)" if s["hidden"] else ""
        print(f"  {local_time(s['updated'])}  {s['id'][:8]}  {s['user_messages']:>3} msg  "
              f"{mark} {s['title'][:60]}{run}{hidden}")
    print(f"\n{len(sessions)} sessions  (✎ /rename title, ? no auto title → first message, ● running)")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="session-finder",
        description="Find and resume your Claude Code conversations.")
    parser.add_argument("--table", action="store_true", help="print the list in the terminal")
    parser.add_argument("--json", action="store_true", help="print the index as JSON")
    parser.add_argument("--all", action="store_true", help="include sessions Claude never replied to")
    parser.add_argument("--defaults", action="store_true",
                        help="default view, as a new user sees it (ignores config, personal palettes and remembered choices)")
    parser.add_argument("--engine", choices=engines.ENGINES, default="auto",
                        help="window engine: gtk (system WebKitGTK), qt (bundled Qt WebEngine), auto (default: gtk, then qt)")
    parser.add_argument("--init-config", action="store_true",
                        help="create ~/.config/session-finder/config.toml from the commented template")
    parser.add_argument("--new-palette", metavar="NAME",
                        help="create a personal palette ~/.config/session-finder/palettes/NAME.toml from the template")
    parser.add_argument("--debug", action="store_true", help="window with developer tools")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    if args.init_config or args.new_palette:
        if args.new_palette:
            if not PALETTE_NAME.match(args.new_palette):
                print("session-finder: palette name: letters, digits, - and _ only", file=sys.stderr)
                return 2
            target = config.palettes_dir() / f"{args.new_palette}.toml"
            ok, message = config.create_from_example(
                target, "palette.example.toml", {'name = "My palette"': f'name = "{args.new_palette}"'})
        else:
            ok, message = config.create_from_example(config.config_path(), "config.example.toml")
        print(f"session-finder: {message}", file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1

    if args.table or args.json:
        sessions = index.build_index(include_hidden=args.all)
        if args.table:
            print_table(sessions)
        else:
            json.dump(sessions, sys.stdout, ensure_ascii=False)
        return 0

    engine, reason = engines.choose(args.engine)
    if engine is None:
        print("session-finder: " + engines.INSTALL_HELP.format(reason=reason), file=sys.stderr)
        return 1
    from . import app
    app.run(engine, debug=args.debug, defaults=args.defaults)
    return 0


if __name__ == "__main__":
    sys.exit(main())
