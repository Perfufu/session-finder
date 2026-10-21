from conftest import ID_MAIN, assistant, user, write_jsonl

from session_finder import cli, report


def fake_claude(tmp_path, monkeypatch):
    root = tmp_path / "secret-claude-dir"
    work = tmp_path / "private-project-name"
    entries = [{**user("a private question", str(work), "2026-01-01T10:00:00Z"), "version": "9.9.9"},
               assistant("2026-01-01T10:00:01Z")]
    write_jsonl(root / "projects" / "-x" / f"{ID_MAIN}.jsonl", entries)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(root))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return root


def test_claude_code_versions_from_recent_files(tmp_path, monkeypatch):
    root = fake_claude(tmp_path, monkeypatch)
    assert report.claude_code_versions(root) == ["9.9.9"]
    assert report.claude_code_versions(tmp_path / "nowhere") == []


def test_report_has_diagnostics_but_nothing_private(tmp_path, monkeypatch, capsys):
    fake_claude(tmp_path, monkeypatch)
    assert cli.main(["--report"]) == 0
    out = capsys.readouterr().out
    assert "9.9.9" in out and "Session Finder" in out and report.ISSUES_URL in out
    for private in ("secret-claude-dir", "private-project-name", "a private question", str(tmp_path)):
        assert private not in out
