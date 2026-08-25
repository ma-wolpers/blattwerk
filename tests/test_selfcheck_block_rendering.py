import re

from app.core.answer_special_selfcheck import render_selfcheck_block

_CONTENT = "- Ich kann das Thema erklaeren.\n- Ich kann Aufgaben dazu loesen.\n"


def _row_count(html):
    return len(re.findall(r"<div class='selfcheck-row'>", html))


def _glyphs_in_first_row(html):
    first_row = re.search(r"<div class='selfcheck-row'>.*?</div>", html, re.DOTALL).group(0)
    return re.findall(r"<span class='selfcheck-glyph'>(.*?)</span>", first_row)


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
