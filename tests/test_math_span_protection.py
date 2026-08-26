"""Tests for `$...$`/`$$...$$` formula protection during Markdown rendering.

Covers the shared core (`math_span_protection.py`) directly, plus both thin
wrappers (`answer_special_shared.py`/`blatt_kern_shared_parsing.py`) to prove
they behave identically -- the two `_new_markdown_converter()` factories stay
deliberately unconsolidated, but the math-protection logic they share must
not drift between them.
"""

import pytest

from app.core import answer_special_shared
from app.core import blatt_kern_shared_parsing
from app.core.answer_line_markers import filter_answer_content_for_mode
from app.core.math_span_protection import protect_math_spans, restore_math_spans, restore_math_spans_as_text

_WRAPPER_MODULES = [answer_special_shared, blatt_kern_shared_parsing]


def _convert(module, text):
    md = module._new_markdown_converter()
    return module.convert_markdown_with_math(md, text)


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_inline_math_survives_unmangled_alongside_bold(module):
    html = _convert(module, r"Formel: $x_i + \{a,b\}$ und **fett**.")
    assert r"$x_i + \{a,b\}$" in html
    assert "<strong>fett</strong>" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_display_math_survives_unmangled_alongside_italic(module):
    html = _convert(module, r"Bruch: $$\frac{a}{b}$$ und *kursiv*.")
    assert r"$$\frac{a}{b}$$" in html
    assert "<em>kursiv</em>" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_underscore_inside_math_is_not_treated_as_emphasis(module):
    # Without protection, python-markdown would still leave plain `a_b`
    # alone by default (underscores need word boundaries), but real LaTeX
    # relies on backslashes/braces that ARE stripped/misinterpreted --
    # this pins the concrete case the feature exists for.
    html = _convert(module, r"$\frac{a}{b} * c$ Ende.")
    assert r"$\frac{a}{b} * c$" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_two_separate_display_math_spans_stay_separate(module):
    # Must not be misread as four inline `$...$` spans (or one big span
    # spanning both) -- the display-math alternative must win first.
    html = _convert(module, r"$$a$$ $$b$$")
    assert r"$$a$$" in html
    assert r"$$b$$" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_unpaired_dollar_sign_is_not_recognized_as_math(module):
    html = _convert(module, "Der Preis betraegt 5$ heute.")
    assert "5$" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_pathological_currency_followed_by_real_math_is_handled_correctly(module):
    # The exact pathological example called out during planning: an
    # unpaired "$" (currency) immediately followed by genuine inline math
    # in the same text.
    html = _convert(module, "Preis: $5 und $x$")
    assert "$5" in html
    assert "$x$" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_currency_amounts_are_not_misread_as_a_math_span(module):
    html = _convert(module, "Preis: $5 und $10 zusammen.")
    assert "$5" in html
    assert "$10" in html
    # Neither "5 und " nor anything else should have been swallowed into a
    # phantom math span and dropped from the visible text.
    assert "und" in html


@pytest.mark.parametrize("module", _WRAPPER_MODULES)
def test_text_without_any_dollar_sign_is_unaffected(module):
    html = _convert(module, "Ganz normaler Text mit **fett** und *kursiv*.")
    assert "<strong>fett</strong>" in html
    assert "<em>kursiv</em>" in html


def test_protect_then_restore_is_a_no_op_round_trip_for_plain_text():
    protected, spans = protect_math_spans("Kein Formeltext hier.")
    assert protected == "Kein Formeltext hier."
    assert spans == []
    assert restore_math_spans("<p>Kein Formeltext hier.</p>", spans) == "<p>Kein Formeltext hier.</p>"


def test_protect_replaces_each_span_with_a_distinct_placeholder():
    protected, spans = protect_math_spans(r"$a$ und $$b$$ und $c$")
    assert spans == ["$a$", "$$b$$", "$c$"]
    assert "$a$" not in protected
    assert "$$b$$" not in protected
    assert "$c$" not in protected


def test_restore_html_escapes_the_recovered_formula_source():
    protected, spans = protect_math_spans("$<script>$")
    restored = restore_math_spans(protected, spans)
    assert "<script>" not in restored
    assert "&lt;script&gt;" in restored


def test_restore_leaves_html_without_placeholders_untouched():
    assert restore_math_spans("<p>nothing to restore</p>", []) == "<p>nothing to restore</p>"


def test_empty_and_none_input_do_not_crash_protect_math_spans():
    assert protect_math_spans("") == ("", [])
    assert protect_math_spans(None) == (None, [])


def test_restore_as_text_does_not_html_escape_the_recovered_formula_source():
    # Unlike restore_math_spans, this variant is for callers whose result is
    # NOT yet final HTML (it will itself be run through convert_markdown_with_math
    # later) -- HTML-escaping here would double-escape, e.g. turning `$a < b$`
    # into the literal text `$a &lt; b$` instead of `$a < b$`.
    protected, spans = protect_math_spans("$a < b$")
    restored = restore_math_spans_as_text(protected, spans)
    assert restored == "$a < b$"


def test_restore_as_text_leaves_text_without_placeholders_untouched():
    assert restore_math_spans_as_text("plain text", []) == "plain text"


def test_task_body_pipeline_preserves_backslash_commands_in_formulas():
    # End-to-end regression for the originally reported bug: the real
    # task/subtask rendering pipeline runs filter_answer_content_for_mode()
    # (answer_line_markers.py) BEFORE convert_markdown_with_math() -- see
    # blatt_kern_task_render.py::_render_task_content/_render_subtask_body.
    # Backslash LaTeX commands must survive that composition unmangled.
    content = r"Loese: $\frac{a}{b} = \mid c \mid$"
    filtered = filter_answer_content_for_mode(content, include_solutions=False, default_show="both")

    md = blatt_kern_shared_parsing._new_markdown_converter()
    html = blatt_kern_shared_parsing.convert_markdown_with_math(md, filtered)

    assert r"$\frac{a}{b} = \mid c \mid$" in html
