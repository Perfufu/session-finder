"""Fake Claude Code folder (~/.claude) built in a temporary directory.

Entirely fictional data: no real conversation ever goes into the repository.
"""
import json
import os

import pytest

ID_MAIN = "11111111-1111-4111-8111-111111111111"
ID_RENAMED = "22222222-2222-4222-8222-222222222222"
ID_EMPTY = "33333333-3333-4333-8333-333333333333"
ID_RUNNING = "44444444-4444-4444-8444-444444444444"


def write_jsonl(path, entries, extra_lines=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e) for e in entries] + list(extra_lines)
    path.write_text("\n".join(lines) + "\n")


def user(text, cwd, ts, **extra):
    return {"type": "user", "cwd": cwd, "timestamp": ts, "gitBranch": "main",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}, **extra}


def assistant(ts):
    return {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": []}}


def dead_pid():
    """A PID that does not exist (to simulate an orphan session file)."""
    pid = 4_000_000
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except PermissionError:
            pass
        pid += 1


@pytest.fixture
def claude(tmp_path):
    root = tmp_path / "claude"
    work = tmp_path / "work"
    # path with underscores: the encoded folder name cannot be decoded back to it
    project = work / "Dev_Ops" / "AWX_Lab"
    project.mkdir(parents=True)
    encoded = root / "projects" / str(project).replace("/", "-").replace("_", "-")

    write_jsonl(encoded / f"{ID_MAIN}.jsonl", [
        {"type": "mode", "mode": "normal"},
        user("<command-name>/clear</command-name>", str(project), "2026-01-01T10:00:00Z"),
        user("Hi <pasted_content id=\"x\">log\nlog</pasted_content> look at this", str(project), "2026-01-01T10:00:01Z"),
        assistant("2026-01-01T10:00:02Z"),
        {"type": "ai-title", "aiTitle": "First title"},
        user("and then?", str(project), "2026-01-01T10:05:00Z"),
        {"type": "user", "cwd": str(project), "timestamp": "2026-01-01T10:05:01Z",
         "message": {"content": [{"type": "tool_result", "content": "output"}]}},
        {"type": "user", "isMeta": True, "cwd": str(project), "message": {"content": "meta"}},
        assistant("2026-01-01T10:05:02Z"),
        {"type": "ai-title", "aiTitle": "Final title"},
        {"type": "last-prompt", "lastPrompt": "and then?"},
    ], extra_lines=['{"type": "user", "trunc'])  # cut line (write in progress)

    write_jsonl(encoded / f"{ID_RENAMED}.jsonl", [
        user("question", str(project), "2026-01-02T09:00:00Z"),
        assistant("2026-01-02T09:00:01Z"),
        {"type": "ai-title", "aiTitle": "Auto title"},
        {"type": "custom-title", "customTitle": "title-in-the-jsonl"},
    ])
    side = encoded / ID_RENAMED
    (side / "subagents").mkdir(parents=True)
    (side / "custom-title.json").write_text(json.dumps({"customTitle": "my-title"}))
    write_jsonl(side / "subagents" / "agent-abc.jsonl", [assistant("2026-01-02T09:00:02Z")])

    write_jsonl(encoded / f"{ID_EMPTY}.jsonl", [user("test", str(project), "2026-01-03T08:00:00Z")])

    gone = work / "deleted"
    write_jsonl(root / "projects" / "-gone" / f"{ID_RUNNING}.jsonl", [
        user("still there?", str(gone), "2026-01-04T08:00:00Z"),
        assistant("2026-01-04T08:00:01Z"),
    ])
    sessions = root / "sessions"
    sessions.mkdir()
    (sessions / "1.json").write_text(json.dumps(
        {"pid": os.getpid(), "sessionId": ID_RUNNING, "status": "busy"}))
    (sessions / "2.json").write_text(json.dumps(
        {"pid": dead_pid(), "sessionId": ID_MAIN, "status": "idle"}))

    return {"root": root, "cache": tmp_path / "cache" / "index.json",
            "project": str(project), "gone": str(gone)}
