import re

from app.core.answer_special_selfcheck import render_selfcheck_block

_CONTENT = "- Ich kann das Thema erklaeren.\n- Ich kann Aufgaben dazu loesen.\n"


def _row_count(html):
    return len(re.findall(r"<div class='selfcheck-row'>", html))


def _glyphs_in_first_row(html):
    first_row = re.search(r"<div class='selfcheck-row'>.*?</div>", html, re.DOTALL).group(0)
    return re.findall(r"<span class='selfcheck-glyph'>(.*?)</span>", first_row)


def _scale_groups_in_first_row(html):
    """Splits the first row's glyphs into one list per `.selfcheck-scale`
    span (one list normally, two in `dual=true` mode)."""
    first_row = re.search(r"<div class='selfcheck-row'>.*?</div>", html, re.DOTALL).group(0)
    scale_spans = re.findall(r"<span class='selfcheck-scale'>.*?</span></span>", first_row, re.DOTALL)
    return [re.findall(r"<span class='selfcheck-glyph'>(.*?)</span>", span) for span in scale_spans]


def test_render_selfcheck_block_empty_content_returns_empty_string():
    assert render_selfcheck_block({}, "") == ""
    assert render_selfcheck_block({}, "   \n  ") == ""


def test_render_selfcheck_block_renders_one_row_per_statement():
    html = render_selfcheck_block({}, _CONTENT)
    assert _row_count(html) == 2


def test_render_selfcheck_block_default_scale_and_steps():
    html = render_selfcheck_block({}, "- Aussage\n")
    assert len(_glyphs_in_first_row(html)) == 3


def test_render_selfcheck_block_respects_custom_steps():
    html = render_selfcheck_block({"steps": "5"}, "- Aussage\n")
    assert len(_glyphs_in_first_row(html)) == 5


def test_render_selfcheck_block_clamps_steps_to_valid_range():
    assert len(_glyphs_in_first_row(render_selfcheck_block({"steps": "0"}, "- A\n"))) == 2
    assert len(_glyphs_in_first_row(render_selfcheck_block({"steps": "99"}, "- A\n"))) == 7


def test_render_selfcheck_block_ampel_scale_has_curated_glyphs():
    html = render_selfcheck_block({"scale": "ampel", "steps": "3"}, "- Aussage\n")
    glyphs = _glyphs_in_first_row(html)
    assert glyphs == ["\U0001F534", "\U0001F7E1", "\U0001F7E2"]


def test_render_selfcheck_block_unknown_scale_falls_back_to_smiley():
    known_smiley = _glyphs_in_first_row(render_selfcheck_block({"scale": "smiley"}, "- A\n"))
    fallback = _glyphs_in_first_row(render_selfcheck_block({"scale": "unbekannt"}, "- A\n"))
    assert fallback == known_smiley


def test_render_selfcheck_block_scale_without_curated_preset_falls_back_to_numbers():
    glyphs = _glyphs_in_first_row(render_selfcheck_block({"scale": "ampel", "steps": "5"}, "- A\n"))
    assert glyphs == ["1", "2", "3", "4", "5"]


def test_render_selfcheck_block_statement_text_supports_markdown():
    html = render_selfcheck_block({}, "- Ich kann **fett** schreiben.\n")
    assert "<strong>fett</strong>" in html


def test_render_selfcheck_block_dual_false_is_the_default_and_unchanged():
    # Regression: dual=false / not set must render exactly today's
    # single-scale markup, no .selfcheck-scale-group / header row.
    without_option = render_selfcheck_block({}, _CONTENT)
    with_explicit_false = render_selfcheck_block({"dual": "false"}, _CONTENT)
    assert without_option == with_explicit_false
    assert "selfcheck-scale-group" not in without_option
    assert "selfcheck-header-row" not in without_option


def test_render_selfcheck_block_dual_renders_two_independent_scale_columns():
    html = render_selfcheck_block({"dual": "true", "steps": "3"}, "- Aussage\n")
    groups = _scale_groups_in_first_row(html)
    assert len(groups) == 2
    assert len(groups[0]) == 3
    assert len(groups[1]) == 3
    assert groups[0] == groups[1]  # same scale definition rendered twice


def test_render_selfcheck_block_dual_without_labels_has_no_header_row():
    html = render_selfcheck_block({"dual": "true"}, _CONTENT)
    assert "selfcheck-header-row" not in html


def test_render_selfcheck_block_dual_with_labels_renders_one_header_row():
    html = render_selfcheck_block({"dual": "true", "label1": "Ich", "label2": "Lehrkraft"}, _CONTENT)
    assert html.count("selfcheck-header-row") == 1
    header = re.search(r"<div class='selfcheck-header-row'>.*?</div>", html, re.DOTALL).group(0)
    assert "Ich" in header
    assert "Lehrkraft" in header


def test_render_selfcheck_block_dual_with_only_one_label_still_shows_header():
    html = render_selfcheck_block({"dual": "true", "label1": "Ich"}, _CONTENT)
    assert "selfcheck-header-row" in html
    assert "Ich" in html


def test_render_selfcheck_block_labels_without_dual_are_ignored():
    html = render_selfcheck_block({"label1": "Ich", "label2": "Lehrkraft"}, _CONTENT)
    assert "selfcheck-header-row" not in html
    assert "selfcheck-scale-group" not in html
