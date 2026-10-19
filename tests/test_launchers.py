import subprocess

import pytest

from session_finder import launchers

SID = "11111111-1111-4111-8111-111111111111"


def test_posix_resume_passes_id_as_argument():
    argv = launchers.resume_argv(SID, shell="/bin/zsh")
    assert argv == ["/bin/zsh", "-ic", 'claude --resume "$1"; exec "$0"', "/bin/zsh", SID]


def test_posix_resume_really_runs(tmp_path):
    """The script does pass the id to claude, then restarts the shell: checked with fake binaries."""
    log = tmp_path / "log"
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "claude").write_text(f'#!/bin/sh\necho "claude $*" >> {log}\n')
    (fake / "claude").chmod(0o755)
    argv = launchers.resume_argv(SID, shell="/bin/sh")
    argv[1] = "-c"  # no interactive shell in tests
    argv[2] = argv[2].replace('exec "$0"', 'echo "exec $0" >> ' + str(log))
    subprocess.run(argv, env={"PATH": f"{fake}:/usr/bin:/bin"}, check=True)
    assert log.read_text().splitlines() == [f"claude --resume {SID}", "exec /bin/sh"]


def test_fish_resume():
    assert launchers.resume_argv(SID, shell="/usr/bin/fish") == [
        "/usr/bin/fish", "-ic", "claude --resume $argv[1]; exec fish", SID]


@pytest.mark.parametrize("terminal,expected", [
    ("kitty", ["kitty", "--directory", "/w", "CMD"]),
    ("alacritty", ["alacritty", "--working-directory", "/w", "-e", "CMD"]),
    ("wezterm", ["wezterm", "start", "--cwd", "/w", "--", "CMD"]),
    ("gnome-terminal", ["gnome-terminal", "--working-directory=/w", "--", "CMD"]),
    ("xterm", ["xterm", "-e", "CMD"]),
    ("/opt/bin/unknown-terminal", ["/opt/bin/unknown-terminal", "-e", "CMD"]),
])
def test_terminal_command_line(terminal, expected):
    assert launchers.terminal_argv(terminal, "/w", ["CMD"]) == expected


def test_terminal_choice_order(monkeypatch):
    present = {"foot", "xterm", "myterm"}
    monkeypatch.setattr(launchers.shutil, "which", lambda c: c if c in present else None)
    monkeypatch.setenv("TERMINAL", "myterm")
    assert launchers.find_terminal("foot") == "foot"        # config first
    assert launchers.find_terminal("") == "myterm"          # then $TERMINAL
    monkeypatch.delenv("TERMINAL")
    assert launchers.find_terminal("missing") == "foot"     # then detection (foot before xterm)
    present.clear()
    assert launchers.find_terminal("") is None
