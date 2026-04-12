from app.core import wiring
from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_kern_layout_render import render_html


def test_wiring_exposes_stable_build_entrypoints():
    assert wiring.build_worksheet is build_worksheet
    assert wiring.render_html is render_html


def test_wiring_all_contains_expected_public_names():
    assert "build_worksheet" in wiring.__all__
    assert "build_help_cards" in wiring.__all__
    assert "inspect_markdown_text" in wiring.__all__
