"""Tests für den Autoren-Anleitungs-Generator (`tools/docs/generate_authoring_guides.py`)."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

_TOOLS_DOCS_DIR = Path(__file__).resolve().parents[1] / "tools" / "docs"
if str(_TOOLS_DOCS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DOCS_DIR))

import authoring_guide_prose  # noqa: E402
import generate_authoring_guides as guide_generator  # noqa: E402
from app.core.markdown_conventions import collect_markdown_conventions  # noqa: E402


def test_generate_guides_is_deterministic_across_calls():
    first = guide_generator.generate_guides()
    second = guide_generator.generate_guides()
    assert first == second


def test_generated_guides_are_nonempty_and_carry_autogen_header():
    guides = guide_generator.generate_guides()
    for content in guides.values():
        assert "Automatisch generiert" in content
        assert len(content) > 500


def test_prose_coverage_passes_for_real_catalog():
    catalog = collect_markdown_conventions()
    guide_generator.assert_prose_coverage(catalog)


def test_prose_coverage_detects_missing_block_prose(monkeypatch):
    catalog = collect_markdown_conventions()
    reduced_prose = dict(authoring_guide_prose.PROSE_SECTIONS)
    del reduced_prose["block:task"]
    monkeypatch.setattr(guide_generator, "PROSE_SECTIONS", reduced_prose)

    with pytest.raises(guide_generator.ProseCoverageError, match="block:task"):
        guide_generator.assert_prose_coverage(catalog)


def test_prose_coverage_detects_missing_geometry_section_prose(monkeypatch):
    catalog = collect_markdown_conventions()
    reduced_prose = dict(authoring_guide_prose.PROSE_SECTIONS)
    del reduced_prose["geometry:pairs"]
    monkeypatch.setattr(guide_generator, "PROSE_SECTIONS", reduced_prose)

    with pytest.raises(guide_generator.ProseCoverageError, match="geometry:pairs"):
        guide_generator.assert_prose_coverage(catalog)


def test_render_worksheet_presentation_guide_changes_when_catalog_changes():
    catalog = collect_markdown_conventions()
    baseline = guide_generator.render_worksheet_presentation_guide(catalog)

    # Simuliert eine neue Blockoption, um zu belegen, dass der Renderer
    # tatsaechlich vom Katalog abhaengt und nicht etwa gecachte/statische
    # Werte ausgibt.
    modified_blocks = tuple(
        replace(block, allowed_options=block.allowed_options | {"__test_marker_option__"})
        if block.name == "task"
        else block
        for block in catalog.blocks
    )
    modified_catalog = replace(catalog, blocks=modified_blocks)
    changed = guide_generator.render_worksheet_presentation_guide(modified_catalog)

    assert baseline != changed
    assert "__test_marker_option__" in changed


def test_main_check_mode_passes_against_freshly_written_guides(tmp_path, monkeypatch):
    worksheet_path = tmp_path / "worksheet.md"
    kurzentwurf_path = tmp_path / "kurzentwurf.md"

    def fake_generate_guides():
        catalog = collect_markdown_conventions()
        return {
            worksheet_path: guide_generator.render_worksheet_presentation_guide(catalog),
            kurzentwurf_path: guide_generator.render_kurzentwurf_guide(catalog),
        }

    monkeypatch.setattr(guide_generator, "generate_guides", fake_generate_guides)

    assert guide_generator.main(["--check"]) == 1  # Dateien existieren noch nicht.
    assert guide_generator.main([]) == 0
    assert guide_generator.main(["--check"]) == 0

    worksheet_path.write_text("veraltet", encoding="utf-8")
    assert guide_generator.main(["--check"]) == 1
