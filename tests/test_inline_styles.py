"""Inline-Stile `-<SPEC> … -<>` (Wunschliste Schritt 5b)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_validator import inspect_markdown_text
from app.core.color_mentions import find_color_mentions
from app.core.inline_markup import parse_inline_markup
from app.core.inline_markup.html_renderer import render_inline_markup_html
from app.core.inline_markup.style_spans import STYLE_MARKER_REGEX, parse_style_spec, protect_style_markers
from app.core.pptx_font_hint import bundled_font_hint
from app.core.blatt_kern_pptx_export_editable_convert import first_font_family

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("spec", "font", "size", "color"),
    [
        ("Arial-#red-12", "Arial", 12.0, "#c62828"),
        ("Times New Roman-10,5", "Times New Roman", 10.5, None),
        ("#ABC", None, None, "#abc"),
        ("comic neue-#gruen", "Comic Neue", None, "#2e7d32"),
        ('"Arial"-20', "Arial", 20.0, None),
    ],
)
def test_spec_parsing(spec, font, size, color):
    style, error = parse_style_spec(spec)
    assert error is None
    assert (style.font_family, style.size_pt, style.color) == (font, size, color)


@pytest.mark.parametrize("spec", ["Papyrus", "#lilablassblau", "12-14", "#red-#blue", "3", '"Arial-12', "Arial--12"])
def test_invalid_specs_are_rejected(spec):
    style, error = parse_style_spec(spec)
    assert style is None and error


def _html(text):
    runs, diagnostics = parse_inline_markup(text)
    return render_inline_markup_html(runs), [d.code for d in diagnostics]


def test_nesting_inherits_per_property_over_three_levels():
    html, codes = _html("-<Arial-#rot> a -<20> b -<#blau> c -<> -<> -<>")
    assert codes == []
    assert "font-size: 20pt; color: #1565c0" in html and "Arial" in html.split(" c ")[0].rsplit("<span", 1)[1]


def test_literal_in_code_and_math_and_escape():
    html, codes = _html("`-<Arial>` und $-<x>$ und \\-<Arial>")
    assert codes == [] and "bw-style" not in html
    assert html.count("-&lt;Arial&gt;") == 2


@pytest.mark.parametrize("text", ["-<12>a\n\nb", "-<12>a\n- Punkt", "| -<12>a | b |", "-<12>offen"])
def test_unclosed_at_boundary_is_im004(text):
    assert "IM004" in [d.code for d in protect_style_markers(text)[2]]


def test_spoiler_pipes_are_no_boundary():
    _html_text, codes = _html("||x|| -<12>a-<>")
    assert codes == []


def test_validator_reports_im004_as_error():
    text = "---\nTitel: T\nFach: M\nThema: X\n---\n:::task\n-<Papyrus>x-<>\n:::\n"
    found = [d for d in inspect_markdown_text(text).diagnostics if d.code == "IM004"]
    assert len(found) == 1 and found[0].severity == "error"


def test_render_embeds_inline_only_bundled_font_once():
    html = render_html({"Titel": "T"}, [("task", {}, "-<Andika>a-<> -<Andika-12>b-<>")], font_profile="segoe")
    assert html.count("font-family: 'Andika';") == 4
    assert 'class="bw-style"' in html


def test_color_mentions_include_inline_colors():
    assert "#c62828" in find_color_mentions("-<#c62828>x-<>")


def test_vscode_grammar_uses_parser_regex():
    grammar = json.loads((REPO_ROOT / "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json").read_text(encoding="utf-8"))
    matches = [p.get("match") for p in grammar["patterns"] if p.get("name") == "markup.other.inline-style.blattwerk"]
    assert matches == [STYLE_MARKER_REGEX]


def test_pptx_font_name_and_hint():
    assert first_font_family("'Comic Neue', 'Comic Sans MS', cursive") == "Comic Neue"
    run = type("R", (), {"font_name": "Comic Neue"})()
    result = type("S", (), {"elements": [type("E", (), {"runs": [run]})()]})()
    hint = bundled_font_hint([result])
    assert hint.code == "PPTX003" and "Comic Sans MS" in hint.message
    assert bundled_font_hint([]) is None
