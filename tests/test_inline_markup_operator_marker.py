"""Tests for the `!!Operator!!` inline marker (`app.core.inline_markup`).

Covers parsing (`Run.bold`/`Run.operator`), HTML rendering (visually
identical to `**fett**`), escaping, and cross-renderer parity between the
Kurzentwurf pipeline (`render_inline_markup`, direct `parse_inline_markup`
call) and the Arbeitsblatt pipeline (`markdown_bridge.py`'s preprocessor) --
both must interpret `!!...!!` identically, since `inline_markup` is the
single authoritative interpretation shared by both document types.
"""

import markdown

from app.core.inline_markup import parse_inline_markup, render_inline_markup
from app.core.inline_markup.markdown_bridge import register_inline_markup_bridge
from app.core.math_span_protection import convert_markdown_with_math


def test_operator_marker_sets_bold_and_operator_flags():
    runs, _diagnostics = parse_inline_markup("!!Bestimme!! die Nullstellen.")
    operator_run = next(r for r in runs if r.operator)
    assert operator_run.text == "Bestimme"
    assert operator_run.bold is True

    rest_run = next(r for r in runs if not r.operator)
    assert rest_run.text == " die Nullstellen."
    assert rest_run.bold is False


def test_operator_marker_renders_identical_to_plain_bold():
    assert render_inline_markup("!!Bestimme!!") == render_inline_markup("**Bestimme**")
    assert render_inline_markup("!!Bestimme!!") == "<strong>Bestimme</strong>"


def test_operator_marker_produces_no_extra_html_node():
    # operator=True is a pure semantic flag for operator_legend.py -- it
    # must not appear in the rendered HTML as its own tag/attribute.
    html = render_inline_markup("!!Bestimme!!")
    assert "operator" not in html


def test_operator_marker_escaped_stays_literal():
    assert render_inline_markup(r"\!\!Bestimme\!\!") == "!!Bestimme!!"


def test_operator_marker_same_runs_regardless_of_consumer():
    text = "!!Bestimme!! die Nullstellen von f."
    direct_runs, _ = parse_inline_markup(text)

    md = markdown.Markdown(extensions=["tables"])
    register_inline_markup_bridge(md)
    bridge_runs, _ = parse_inline_markup(text)

    assert direct_runs == bridge_runs


def test_operator_marker_same_visible_html_across_both_pipelines():
    text = "!!Bestimme!! die Nullstellen von f."

    kurzentwurf_html = render_inline_markup(text)

    md = markdown.Markdown(extensions=["tables"])
    register_inline_markup_bridge(md)
    worksheet_html = convert_markdown_with_math(md, text, lambda t: t)

    assert "<strong>Bestimme</strong>" in kurzentwurf_html
    assert "<strong>Bestimme</strong>" in worksheet_html
