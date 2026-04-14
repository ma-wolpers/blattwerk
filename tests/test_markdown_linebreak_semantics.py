from app.core.answer_line_markers import render_answer_content_html_for_mode
from app.core.blatt_kern_task_render import render_block


def test_raw_single_newline_renders_as_shift_enter_break():
    html = render_block("raw", {}, "Erste Zeile\nZweite Zeile")

    assert "<br" in html
    assert "</p>\n<p>" not in html


def test_raw_double_newline_renders_as_paragraph_break():
    html = render_block("raw", {}, "Absatz A\n\nAbsatz B")

    assert "</p>\n<p>" in html


def test_raw_multiple_blank_lines_collapse_to_one_paragraph_break():
    html = render_block("raw", {}, "Absatz A\n\n\n\nAbsatz B")

    assert html.count("<p>") == 2
    assert "<p></p>" not in html


def test_block_types_share_single_newline_semantics():
    block_inputs = [
        ("material", {}, "M1\nM2", False),
        ("info", {}, "I1\nI2", False),
        ("task", {"_show_task_label": "1"}, "T1\nT2", False),
        ("solution", {}, "L1\nL2", True),
    ]

    for block_type, options, content, include_solutions in block_inputs:
        html = render_block(
            block_type,
            options,
            content,
            include_solutions=include_solutions,
        )
        assert "<br" in html


def test_answer_marker_renderer_keeps_own_line_joining_behavior():
    html = render_answer_content_html_for_mode(
        "Zeile A\n\nZeile B",
        include_solutions=False,
    )

    assert html == "Zeile A<br>Zeile B"
