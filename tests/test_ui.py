"""JS safety net: a syntax error in the UI means a black window, silently."""
import re
import shutil
import subprocess
from importlib import resources

import pytest

from session_finder.app import build_page

node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def check_syntax(tmp_path, source, name):
    f = tmp_path / name
    f.write_text(source)
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@node
def test_app_js_syntax(tmp_path):
    check_syntax(tmp_path, (resources.files("session_finder") / "ui/app.js").read_text(), "app.js")


@node
def test_inline_scripts_syntax(tmp_path):
    page = build_page({"sessions": []})
    scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
    assert scripts
    for i, src in enumerate(scripts):
        check_syntax(tmp_path, src, f"inline{i}.js")


def test_error_handler_fallback_matches_strings():
    pkg = resources.files("session_finder")
    html, app = (pkg / "ui/index.html").read_text(), (pkg / "ui/app.js").read_text()
    fallback = dict(re.findall(r"(error\w+): '([^']*)'", html))
    in_strings = dict(re.findall(r"(error\w+): '([^']*)'", app))
    assert fallback and fallback == in_strings
