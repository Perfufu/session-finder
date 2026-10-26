"""JS safety net: a syntax error in the UI means a black window, silently."""
import json
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
    in_strings = dict(re.findall(r"(error\w+): '([^']*)'", strings_block(app, "en")))
    assert fallback and fallback == in_strings


def strings_block(app_js, lang):
    """Source text of one language object of STRINGS (top level: two-space indent)."""
    m = re.search(rf"^  {lang}: \{{\n(.*?)^  \}},\n", app_js, re.S | re.M)
    assert m, lang
    return m.group(1)


def string_keys(block):
    # entries are written at four-space indent; function-valued ones contain "=>"
    return {k: "=>" in v for k, v in re.findall(r"^    (\w+): (.*)$", block, re.M)}


def test_translations_cover_the_same_keys_as_english():
    from session_finder import config
    app_js = (resources.files("session_finder") / "ui/app.js").read_text()
    declared = re.findall(r"^  (\w+): \{$", app_js[app_js.index("const STRINGS"):], re.M)
    assert tuple(declared) == config.LANGUAGES
    en = string_keys(strings_block(app_js, "en"))
    for lang in config.LANGUAGES:
        assert string_keys(strings_block(app_js, lang)) == en, lang


@node
def test_fuzzy_includes(tmp_path):
    app_js = (resources.files("session_finder") / "ui/app.js").read_text()
    code = re.search(r"// FUZZY-BEGIN\n(.*?)// FUZZY-END", app_js, re.S).group(1)
    cases = [  # (haystack, word, expected)
        ("fix the websocket reconnect", "websocket", True),    # exact
        ("fix the websocket reconnect", "websockte", True),    # transposition
        ("fix the websocket reconnect", "reconect", True),     # missing letter
        ("fix the websocket reconnect", "wbsocket", True),     # missing letter, 8 chars
        ("fix the websocket reconnect", "reconnecting", False),  # beyond the budget
        ("fix the websocket reconnect", "dockerfile", False),
        ("fix the websocket reconnect", "fox", False),         # short words stay exact
        ("fix the websocket reconnect", "", True),
    ]
    script = code + "\nconst cases = " + json.dumps(cases) + """;
for (const [h, w, want] of cases) if (fuzzyIncludes(h, w) !== want) { console.error('FAIL', h, w, want); process.exit(1); }
"""
    f = tmp_path / "fuzzy.js"
    f.write_text(script)
    r = subprocess.run(["node", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
