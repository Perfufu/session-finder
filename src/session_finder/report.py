"""`session-finder --report`: a diagnostic block to paste into a bug report.

Deliberately limited to what helps reproduce a problem: versions, system, window
engine. Never a path, a conversation title or any conversation content.
"""
import json
import os
import platform
import sys

from . import __version__, config, engines, index, launchers

ISSUES_URL = "https://github.com/Perfufu/session-finder/issues"


def claude_code_versions(root, newest=5):
    """Claude Code versions that wrote the most recently modified conversations (the
    `version` field of the .jsonl lines): a format change shows up with a version."""
    files = []
    for path in (root / "projects").glob("*/*.jsonl"):
        try:
            files.append((path.stat().st_mtime_ns, path))
        except OSError:
            continue
    found = set()
    for _, path in sorted(files, reverse=True)[:newest]:
        try:
            with path.open(errors="replace") as fh:
                for line in fh:
                    try:
                        version = json.loads(line).get("version")
                    except (ValueError, AttributeError):
                        continue
                    if isinstance(version, str):
                        found.add(version)
                        break
        except OSError:
            continue
    return sorted(found)


def collect():
    engine, reason = engines.choose("auto")
    root = index.claude_dir()
    try:
        count = len(list((root / "projects").glob("*/*.jsonl")))
    except OSError:
        count = "?"
    return {
        "Session Finder": __version__,
        "Python": platform.python_version(),
        "OS": f"{platform.system()} {platform.release()}",
        "Desktop": os.environ.get("XDG_CURRENT_DESKTOP") or "?",
        "Session type": os.environ.get("XDG_SESSION_TYPE") or "?",
        "Window engine": engine or f"none ({reason})",
        "Terminal": launchers.find_terminal(config.load()["terminal"]["command"]) or "none found",
        "Claude Code (recent conversations)": ", ".join(claude_code_versions(root)) or "?",
        "Conversation files": count,
    }


def render(info):
    width = max(len(k) for k in info)
    lines = [f"{k.ljust(width)} : {v}" for k, v in info.items()]
    return "\n".join([
        f"Copy the block below into your report ({ISSUES_URL}).",
        "It contains no path and no conversation content.",
        "", "```", *lines, "```",
    ])
