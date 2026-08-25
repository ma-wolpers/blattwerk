from app.core.answer_special_writebox import estimate_writebox_weight, render_writebox_block


def _line_count(html):
    return html.count("<div class='line'></div>")


def test_render_writebox_block_default_style_and_line_count():
    html = render_writebox_block({}, "")
    assert "writebox-style-frame" in html
    assert _line_count(html) == 5


def test_render_writebox_block_without_prompt_has_no_prompt_div():
    html = render_writebox_block({}, "")
    assert "writebox-prompt" not in html
    assert "writebox-lines" in html


def test_render_writebox_block_with_prompt_renders_prompt_div():
    html = render_writebox_block({}, "Schreib einen Steckbrief.")
    assert "writebox-prompt" in html
    assert "Schreib einen Steckbrief." in html


def test_render_writebox_block_respects_custom_line_count():
    html = render_writebox_block({"lines": "8"}, "")
    assert _line_count(html) == 8


def test_render_writebox_block_non_positive_line_count_falls_back_to_default():
    assert _line_count(render_writebox_block({"lines": "0"}, "")) == 5
    assert _line_count(render_writebox_block({"lines": "-3"}, "")) == 5


def test_render_writebox_block_clamps_line_count_to_valid_maximum():
    assert _line_count(render_writebox_block({"lines": "99"}, "")) == 20


def test_render_writebox_block_style_variants():
    for style in ("bubble", "cloud", "frame", "letter"):
        html = render_writebox_block({"style": style}, "")
        assert f"writebox-style-{style}" in html


def test_render_writebox_block_unknown_style_falls_back_to_frame():
    html = render_writebox_block({"style": "unbekannt"}, "")
    assert "writebox-style-frame" in html


def test_render_writebox_block_prompt_supports_markdown():
    html = render_writebox_block({}, "Schreib etwas **Wichtiges**.")
    assert "<strong>Wichtiges</strong>" in html


def test_estimate_writebox_weight_scales_with_line_count_not_prompt_length():
    # An empty prompt with many lines must not collapse to the generic
    # text-length heuristic's 0.6 floor -- the ruled-lines area, driven by
    # `lines`, is what actually takes up space on the page.
    few_lines = estimate_writebox_weight({"lines": "2"}, "")
    many_lines = estimate_writebox_weight({"lines": "15"}, "")
    assert many_lines > few_lines
    assert few_lines >= 0.8


def test_estimate_writebox_weight_ignores_line_count_when_no_lines_option_set():
    assert estimate_writebox_weight({}, "") == estimate_writebox_weight({"lines": "5"}, "")
