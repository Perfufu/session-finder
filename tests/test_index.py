import os

import pytest
from conftest import ID_EMPTY, ID_MAIN, ID_RENAMED, ID_RUNNING, assistant, user, write_jsonl

from session_finder import index


def build(claude, **kw):
    return {s["id"]: s for s in index.build_index(root=claude["root"], cache=claude["cache"], **kw)}


def test_cwd_read_from_the_file_not_from_the_folder_name(claude):
    s = build(claude)[ID_MAIN]
    assert s["cwd"] == claude["project"]  # with its underscores
    assert s["cwd_exists"]


def test_only_real_user_messages_count(claude):
    s = build(claude)[ID_MAIN]
    # /clear, tool_result and isMeta do not count; the truncated line is skipped
    assert s["user_messages"] == 2
    assert s["assistant_messages"] == 2
    assert s["first_prompt"] == "Hi [pasted] look at this"
    assert s["last_prompt"] == "and then?"


def test_last_auto_title_wins(claude):
    s = build(claude)[ID_MAIN]
    assert (s["title"], s["title_source"]) == ("Final title", "ai")


def test_rename_title_from_side_file_takes_priority(claude):
    s = build(claude)[ID_RENAMED]
    assert (s["title"], s["title_source"]) == ("my-title", "custom")


def test_subagents_are_ignored(claude):
    assert len(build(claude, include_hidden=True)) == 4


def test_session_without_reply_is_flagged_not_hidden(claude):
    sessions = build(claude)
    assert sessions[ID_EMPTY]["no_reply"] and not sessions[ID_EMPTY]["hidden"]
    assert not sessions[ID_MAIN]["no_reply"]
    assert not sessions[ID_RUNNING]["no_reply"]


def test_open_session_without_reply_yet_is_not_flagged(claude, tmp_path):
    # a session that was just started and is waiting for its first answer is not a failure
    (claude["root"] / "sessions" / "3.json").write_text(
        '{"pid": %d, "sessionId": "%s", "status": "busy"}' % (os.getpid(), ID_EMPTY))
    assert not build(claude)[ID_EMPTY]["no_reply"]


def test_empty_shell_is_not_listed(tmp_path):
    root = tmp_path / "claude"
    write_jsonl(root / "projects" / "-p" / "88888888-8888-4888-8888-888888888888.jsonl", [{"type": "mode", "mode": "normal"}])
    assert index.build_index(root=root, cache=tmp_path / "c.json") == []


def test_running_sessions_and_orphan_pid(claude):
    sessions = build(claude)
    assert sessions[ID_RUNNING]["running"] == "busy"
    assert sessions[ID_MAIN]["running"] is None  # its PID is dead


def test_missing_folder(claude):
    assert not build(claude)[ID_RUNNING]["cwd_exists"]


def test_cache_reused_then_invalidated(claude, monkeypatch):
    build(claude)
    calls = []
    real = index.parse_session
    monkeypatch.setattr(index, "parse_session", lambda p: calls.append(p) or real(p))
    build(claude)
    assert calls == []  # nothing changed: everything comes from the cache
    path = next((claude["root"] / "projects").glob(f"*/{ID_MAIN}.jsonl"))
    with path.open("a") as fh:
        fh.write('{"type": "ai-title", "aiTitle": "Yet another"}\n')
    assert build(claude)[ID_MAIN]["title"] == "Yet another"
    assert calls == [path]


def test_missing_claude_folder(tmp_path):
    assert index.build_index(root=tmp_path / "nothing", cache=tmp_path / "c.json") == []


@pytest.mark.parametrize("entrypoint, expected", [
    ("cli", False), ("sdk-cli", True), ("sdk-ts", True), ("sdk-py", True),
    ("claude-vscode", False), ("something-new", False), (None, False),   # unknown = interactive
])
def test_non_interactive_from_entrypoint(tmp_path, entrypoint, expected):
    extra = {"entrypoint": entrypoint} if entrypoint else {}
    root = tmp_path / "claude"
    sid = "55555555-5555-4555-8555-555555555555"
    write_jsonl(root / "projects" / "-p" / f"{sid}.jsonl",
                [user("hi", "/p", "2026-01-05T08:00:00Z", **extra), assistant("2026-01-05T08:00:01Z")])
    s = index.build_index(root=root, cache=tmp_path / "cache" / "index.json")[0]
    assert s["non_interactive"] is expected


def two_sessions(tmp_path):
    """One interactive session in /work/a/sub, one `claude -p` in /work/job."""
    root = tmp_path / "claude"
    for sid, cwd, ep in (("66666666-6666-4666-8666-666666666666", "/work/a/sub", "cli"),
                         ("77777777-7777-4777-8777-777777777777", "/work/job", "sdk-cli")):
        write_jsonl(root / "projects" / sid[:4] / f"{sid}.jsonl",
                    [user("hi", cwd, "2026-01-05T08:00:00Z", entrypoint=ep), assistant("2026-01-05T08:00:01Z")])
    return root, tmp_path / "cache" / "index.json"


def test_non_interactive_shown_by_default_hidden_on_request(tmp_path):
    root, cache = two_sessions(tmp_path)
    assert len(index.build_index(root=root, cache=cache)) == 2
    shown = index.build_index(root=root, cache=cache, hide_non_interactive=True)
    assert [s["cwd"] for s in shown] == ["/work/a/sub"]
    everything = index.build_index(root=root, cache=cache, hide_non_interactive=True, include_hidden=True)
    assert {s["cwd"]: s["hidden_reason"] for s in everything} == {"/work/a/sub": None, "/work/job": "non-interactive"}


def test_excluded_folders_cover_subfolders_but_not_lookalikes(tmp_path):
    root, cache = two_sessions(tmp_path)
    got = lambda folders: [s["cwd"] for s in index.build_index(root=root, cache=cache, exclude_folders=folders)]
    assert got(["/work/a"]) == ["/work/job"]            # subfolder covered
    assert got(["/work/a/su", "/work/jo"]) == ["/work/a/sub", "/work/job"]   # prefix of a name ≠ parent folder
    assert got([42, "", "/work/job/"]) == ["/work/a/sub"]   # junk ignored, trailing slash fine
