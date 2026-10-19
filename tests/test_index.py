from conftest import ID_EMPTY, ID_MAIN, ID_RENAMED, ID_RUNNING

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


def test_session_without_reply_is_hidden(claude):
    assert ID_EMPTY not in build(claude)
    assert build(claude, include_hidden=True)[ID_EMPTY]["hidden"]


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
