"""Open a terminal in a session's folder, running `claude --resume <id>`.

Terminal chosen in this order: config [terminal] command, then $TERMINAL,
then the first known terminal found in PATH.
"""
import os
import shutil
import subprocess
from pathlib import Path

# How each terminal receives a starting folder and a command to run.
# None for the folder = no such option: rely on the process cwd.
TERMINALS = {
    "kitty":          (lambda d: ["--directory", d], []),
    "ghostty":        (lambda d: [f"--working-directory={d}"], ["-e"]),
    "foot":           (lambda d: ["--working-directory", d], []),
    "alacritty":      (lambda d: ["--working-directory", d], ["-e"]),
    "wezterm":        (lambda d: ["start", "--cwd", d], ["--"]),
    "gnome-terminal": (lambda d: [f"--working-directory={d}"], ["--"]),
    "konsole":        (lambda d: ["--workdir", d], ["-e"]),
    "xfce4-terminal": (lambda d: [f"--working-directory={d}"], ["-x"]),
    "xterm":          (None, ["-e"]),
}
DETECTION_ORDER = list(TERMINALS)


def find_terminal(configured=""):
    for candidate in (configured, os.environ.get("TERMINAL", "")):
        if candidate and shutil.which(candidate):
            return candidate
    return next((t for t in DETECTION_ORDER if shutil.which(t)), None)


def resume_argv(session_id, shell=None):
    """Interactive shell around claude: after quitting claude, you stay in a shell
    in the right folder. The id is passed as an argument, never inside the command string."""
    shell = shell or os.environ.get("SHELL") or "/bin/sh"
    if Path(shell).name == "fish":
        return [shell, "-ic", 'claude --resume $argv[1]; exec fish', session_id]
    # sh -c 'script' $0 $1: $0 = the shell itself (for the exec), $1 = the id
    return [shell, "-ic", 'claude --resume "$1"; exec "$0"', shell, session_id]


def terminal_argv(terminal, cwd, command):
    """Full command line to open `command` in `cwd`."""
    directory, exec_flag = TERMINALS.get(Path(terminal).name, (None, ["-e"]))  # unknown: -e convention
    return [terminal, *(directory(cwd) if directory else []), *exec_flag, *command]


def launch(terminal, cwd, session_id):
    argv = terminal_argv(terminal, cwd, resume_argv(session_id))
    # cwd= as well: covers terminals without a folder option (xterm, unknown ones)
    subprocess.Popen(argv, cwd=cwd, start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
