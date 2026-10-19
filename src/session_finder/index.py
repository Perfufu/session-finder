"""Index of Claude Code conversations.

Reads <claude>/projects/<encoded-folder>/<uuid>.jsonl (one conversation per
file) and produces a summary per session: where it was started, its title,
its dates. Read-only: never modifies anything in Claude Code's folder.

The .jsonl format is internal to Claude Code (undocumented): everything is read
defensively, a missing field or an unreadable line never crashes anything.
"""
import json
import os
import re
from pathlib import Path

CACHE_VERSION = 1

# "user" messages not typed by the user: output of /commands
COMMAND_WRAPPER = re.compile(r"^\s*<(command-name|command-message|command-args|local-command-stdout|local-command-caveat)\b")
# Pasted content: keep the surrounding text, not the block
PASTED = re.compile(r"<pasted_content\b[^>]*>.*?</pasted_content>", re.S)


def claude_dir():
    """Claude Code's folder (relocatable with CLAUDE_CONFIG_DIR, otherwise ~/.claude)."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def default_cache():
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "session-finder" / "index.json"


def user_texts(entry):
    """Text actually typed in a "user" entry (excluding tool results, meta entries, commands)."""
    if entry.get("isMeta") or entry.get("isSidechain"):
        return []
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        blocks = [content]
    elif isinstance(content, list):
        blocks = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    else:
        blocks = []
    return [t for t in blocks if isinstance(t, str) and t.strip() and not COMMAND_WRAPPER.match(t)]


def clean(text, limit=200):
    text = PASTED.sub("[pasted]", text)
    text = " ".join(text.split())
    return text[:limit] + ("…" if len(text) > limit else "")


def parse_session(path):
    """Reads a .jsonl once and extracts the session summary."""
    s = {
        "id": path.stem, "cwd": None, "git_branch": None,
        "created": None, "updated": None,
        "ai_title": None, "custom_title": None,
        "first_prompt": None, "last_prompt": None,
        "user_messages": 0, "assistant_messages": 0,
    }
    with path.open(errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue  # truncated line (session being written, crash)
            if not isinstance(e, dict):
                continue
            t = e.get("type")
            ts = e.get("timestamp")
            if isinstance(ts, str):
                s["created"] = s["created"] or ts
                s["updated"] = ts
            if t == "assistant" and not e.get("isSidechain"):
                s["assistant_messages"] += 1
            elif t == "user":
                s["cwd"] = s["cwd"] or e.get("cwd")
                s["git_branch"] = e.get("gitBranch") or s["git_branch"]
                texts = user_texts(e)
                if texts:
                    s["user_messages"] += 1
                    s["first_prompt"] = s["first_prompt"] or clean(texts[0])
            elif t == "ai-title":
                s["ai_title"] = e.get("aiTitle") or s["ai_title"]  # rewritten as the session goes: keep the last one
            elif t == "custom-title":
                s["custom_title"] = e.get("customTitle") or s["custom_title"]
            elif t == "last-prompt" and isinstance(e.get("lastPrompt"), str):
                s["last_prompt"] = clean(e["lastPrompt"])
    return s


def sidecar_title(path):
    """/rename also stores the title in <uuid>/custom-title.json, which takes priority."""
    try:
        return json.loads((path.with_suffix("") / "custom-title.json").read_text()).get("customTitle")
    except (OSError, ValueError, AttributeError):
        return None


def running_sessions(root):
    """sessionId -> {status, pid}, for sessions whose claude process is still running.
    (<claude>/sessions/<pid>.json; the neighbouring <pid>.<hash>.key is a secret, never read.)"""
    alive = {}
    for f in (root / "sessions").glob("*.json"):
        try:
            d = json.loads(f.read_text())
            pid = int(d["pid"])
            os.kill(pid, 0)  # signal 0: only tests that the PID exists
        except (OSError, ValueError, KeyError, TypeError):
            continue  # orphan file (crash) or unreadable
        alive[d.get("sessionId")] = {"status": d.get("status") or "running", "pid": pid}
    return alive


def load_cache(cache):
    try:
        c = json.loads(cache.read_text())
        return c["entries"] if c.get("version") == CACHE_VERSION else {}
    except (OSError, ValueError, KeyError, AttributeError):
        return {}


def save_cache(cache, entries):
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": CACHE_VERSION, "entries": entries}))
        tmp.replace(cache)  # atomic write: never a half-written cache
    except OSError:
        pass  # optional cache: skipped if the folder is not writable


def build_index(include_hidden=False, root=None, cache=None):
    root = root or claude_dir()
    cache = cache or default_cache()
    old = load_cache(cache)
    fresh = {}
    running = running_sessions(root)
    sessions = []
    # depth 1: subagents (<uuid>/subagents/*.jsonl) are excluded by construction
    for path in (root / "projects").glob("*/*.jsonl"):
        try:
            st = path.stat()
            stamp = [st.st_mtime_ns, st.st_size]
            hit = old.get(str(path))
            s = hit["data"] if hit and hit.get("stamp") == stamp else parse_session(path)
        except OSError:
            continue  # file deleted between the glob and the read
        fresh[str(path)] = {"stamp": stamp, "data": s}

        s = dict(s)
        custom = sidecar_title(path) or s["custom_title"]
        s["title"] = custom or s["ai_title"] or s["first_prompt"] or "(untitled)"
        s["title_source"] = "custom" if custom else "ai" if s["ai_title"] else "prompt"
        s["cwd_exists"] = bool(s["cwd"]) and os.path.isdir(s["cwd"])
        run = running.get(s["id"]) or {}
        s["running"] = run.get("status")
        s["pid"] = run.get("pid")
        s["size"] = st.st_size
        s["hidden"] = s["assistant_messages"] == 0  # never answered ("test" session, API error…)
        if include_hidden or not s["hidden"]:
            sessions.append(s)

    if fresh != old:
        save_cache(cache, fresh)
    sessions.sort(key=lambda s: (s["cwd"] or "", s["updated"] or ""))
    return sessions
