"""Aus `CONTROL_MARKERS` abgeleitete Kontrollmarker-Erkennung (BL005, Editor, VS Code)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.blatt_validator import inspect_markdown_text
from app.core.control_markers import CONTROL_MARKER_LINE_REGEX, control_marker_line_match, is_control_marker_line

REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_LINES = ["--", "--!", "-+", "--hf", "--hm", "--# Abschnitt", "-= 2cm"]


@pytest.mark.parametrize("line", VALID_LINES)
def test_every_marker_is_detected_and_highlighted(line):
    assert is_control_marker_line(line)
    match = control_marker_line_match("  " + line + " ")
    assert match and match.group(2) == line


@pytest.mark.parametrize("line", ["--#", "-=x"])
def test_prefix_attempts_count_for_bl005_but_are_not_highlighted(line):
    assert is_control_marker_line(line) and control_marker_line_match(line) is None


@pytest.mark.parametrize("line", ["---", "--x", "- Punkt", "Text --hm"])
def test_ordinary_lines_are_no_markers(line):
    assert not is_control_marker_line(line) and control_marker_line_match(line) is None


@pytest.mark.parametrize("line", VALID_LINES + ["--#"])
def test_marker_inside_block_is_bl005(line):
    text = "---\nTitel: T\n---\n:::info\nA\n" + line + "\nB\n:::\n"
    assert "BL005" in [d.code for d in inspect_markdown_text(text).diagnostics]


def test_vscode_grammar_uses_derived_regex():
    grammar = json.loads((REPO_ROOT / "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json").read_text(encoding="utf-8"))
    assert grammar["patterns"][0]["match"] == CONTROL_MARKER_LINE_REGEX
