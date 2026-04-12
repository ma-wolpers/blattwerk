from app.core.blatt_kern_answer_table import _render_answer_block


def test_mc_inline_without_question_renders_non_inline_group():
    options = {"type": "mc", "inline": "true"}
    content = "- [ ] W (wahr)\n- [x] F (falsch)"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "mc-group mc-inline" not in html
    assert "class='mc-group'" in html


def test_mc_inline_with_question_keeps_inline_group():
    options = {"type": "mc", "inline": "true"}
    content = "Ist die Aussage korrekt?\n- [ ] W (wahr)\n- [x] F (falsch)"

    html = _render_answer_block(options, content, include_solutions=False)

    assert "mc-group mc-inline" in html
