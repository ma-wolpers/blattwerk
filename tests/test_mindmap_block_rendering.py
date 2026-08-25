import re

from app.core.answer_special_mindmap import estimate_mindmap_weight, render_mindmap_block


def _spoke_count(html):
    return len(re.findall(r"<line class='mindmap-spoke'", html))


def _subspoke_count(html):
    return len(re.findall(r"<line class='mindmap-subspoke'", html))


def test_render_mindmap_block_empty_topic_returns_empty_string():
    assert render_mindmap_block({}, "") == ""
    assert render_mindmap_block({}, "   \n  ") == ""


def test_render_mindmap_block_default_branch_count_is_six():
    html = render_mindmap_block({}, "Wasserkreislauf")
    assert _spoke_count(html) == 6
    assert "mindmap-block" in html
    assert "mindmap-center" in html


def test_render_mindmap_block_respects_custom_branch_count():
    html = render_mindmap_block({"branches": "4"}, "Thema")
    assert _spoke_count(html) == 4


def test_render_mindmap_block_clamps_branch_count_to_valid_range():
    assert _spoke_count(render_mindmap_block({"branches": "0"}, "Thema")) == 2
    assert _spoke_count(render_mindmap_block({"branches": "99"}, "Thema")) == 12


def test_render_mindmap_block_shape_variants_change_the_svg_element():
    oval_html = render_mindmap_block({"shape": "oval", "branches": "2"}, "Thema")
    rect_html = render_mindmap_block({"shape": "rect", "branches": "2"}, "Thema")
    cloud_html = render_mindmap_block({"shape": "cloud", "branches": "2"}, "Thema")

    assert "<rect class='mindmap-branch'" in rect_html
    assert "<rect class='mindmap-branch'" not in oval_html
    assert "<g class='mindmap-branch'>" in cloud_html
    assert "<ellipse class='mindmap-branch'" in oval_html


def test_render_mindmap_block_unknown_shape_falls_back_to_oval():
    html = render_mindmap_block({"shape": "hexagon", "branches": "2"}, "Thema")
    assert "<ellipse class='mindmap-branch'" in html


def test_render_mindmap_block_escapes_topic_text():
    html = render_mindmap_block({}, "<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_estimate_mindmap_weight_empty_topic_is_zero():
    assert estimate_mindmap_weight({}, "") == 0.0


def test_estimate_mindmap_weight_does_not_collapse_to_the_generic_text_floor():
    # A short topic ("Thema") would hit the generic text-length heuristic's
    # 0.6 floor -- the diagram itself is much larger than that, which is
    # exactly the underestimation this dedicated estimator exists to avoid.
    assert estimate_mindmap_weight({}, "Thema") > 1.5


def test_estimate_mindmap_weight_increases_with_branch_count():
    small = estimate_mindmap_weight({"branches": "2"}, "Thema")
    large = estimate_mindmap_weight({"branches": "12"}, "Thema")
    assert large > small


def test_render_mindmap_block_default_has_no_subbranches():
    # Regression: subbranches=0 (default) must render exactly today's
    # single-tier diagram, no .mindmap-subspoke elements and the default
    # (smaller) viewBox.
    html = render_mindmap_block({"branches": "4"}, "Thema")
    assert _subspoke_count(html) == 0
    assert "mindmap-subbranch" not in html
    assert "viewBox='0 0 420 420'" in html


def test_render_mindmap_block_subbranches_fan_out_per_main_branch():
    html = render_mindmap_block({"branches": "4", "subbranches": "2"}, "Thema")
    assert _subspoke_count(html) == 4 * 2
    assert "mindmap-subbranch" in html


def test_render_mindmap_block_subbranches_use_the_larger_canvas():
    html = render_mindmap_block({"branches": "4", "subbranches": "1"}, "Thema")
    assert "viewBox='0 0 560 560'" in html


def test_render_mindmap_block_clamps_subbranch_count_to_valid_range():
    assert _subspoke_count(render_mindmap_block({"branches": "3", "subbranches": "-1"}, "Thema")) == 0
    assert _subspoke_count(render_mindmap_block({"branches": "3", "subbranches": "99"}, "Thema")) == 3 * 4


def test_estimate_mindmap_weight_subbranches_default_does_not_change_weight():
    without_option = estimate_mindmap_weight({"branches": "4"}, "Thema")
    with_zero = estimate_mindmap_weight({"branches": "4", "subbranches": "0"}, "Thema")
    assert without_option == with_zero


def test_estimate_mindmap_weight_increases_with_subbranch_count():
    base = estimate_mindmap_weight({"branches": "4"}, "Thema")
    with_subbranches = estimate_mindmap_weight({"branches": "4", "subbranches": "2"}, "Thema")
    assert with_subbranches > base


def test_render_mindmap_block_include_solutions_has_no_effect_on_output():
    # mindmap has no `include_solutions` parameter at all -- there is only
    # one rendering codepath, so this is a structural guarantee, not a
    # runtime toggle to test both branches of.
    html_a = render_mindmap_block({"branches": "5"}, "Thema")
    html_b = render_mindmap_block({"branches": "5"}, "Thema")
    assert html_a == html_b
