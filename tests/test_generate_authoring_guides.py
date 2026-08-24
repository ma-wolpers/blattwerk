"""Tests für den Autoren-Anleitungs-Generator (`tools/docs/generate_authoring_guides.py`)."""

import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

_TOOLS_DOCS_DIR = Path(__file__).resolve().parents[1] / "tools" / "docs"
if str(_TOOLS_DOCS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DOCS_DIR))

import authoring_guide_prose  # noqa: E402
import generate_authoring_guides as guide_generator  # noqa: E402
from app.core.answer_grid_plot import render_geometry_answer  # noqa: E402
from app.core.blatt_validator import inspect_markdown_text  # noqa: E402
from app.core.blatt_validator_constants import BlockOptionSpec  # noqa: E402
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


def test_prose_coverage_detects_missing_kurzentwurf_phase_prose(monkeypatch):
    catalog = collect_markdown_conventions()
    reduced_prose = dict(authoring_guide_prose.PROSE_SECTIONS)
    del reduced_prose["kurzentwurf:phase:sicherung"]
    monkeypatch.setattr(guide_generator, "PROSE_SECTIONS", reduced_prose)

    with pytest.raises(guide_generator.ProseCoverageError, match="kurzentwurf:phase:sicherung"):
        guide_generator.assert_prose_coverage(catalog)


def test_prose_coverage_detects_missing_kurzentwurf_marker_prose(monkeypatch):
    catalog = collect_markdown_conventions()
    reduced_prose = dict(authoring_guide_prose.PROSE_SECTIONS)
    del reduced_prose["kurzentwurf:marker:ant>"]
    monkeypatch.setattr(guide_generator, "PROSE_SECTIONS", reduced_prose)

    with pytest.raises(guide_generator.ProseCoverageError, match=re.escape("kurzentwurf:marker:ant>")):
        guide_generator.assert_prose_coverage(catalog)


def test_kurzentwurf_guide_phase_table_shows_hashtag_not_display_name_only():
    catalog = collect_markdown_conventions()
    guide_text = guide_generator.render_kurzentwurf_guide(catalog)
    assert "`#sicherung`" in guide_text
    assert "`#reserve`" in guide_text


def test_render_worksheet_presentation_guide_changes_when_catalog_changes(monkeypatch):
    catalog = collect_markdown_conventions()
    baseline = guide_generator.render_worksheet_presentation_guide(catalog)

    # Simuliert eine neue Blockoption, um zu belegen, dass der Renderer
    # tatsaechlich vom Katalog abhaengt und nicht etwa gecachte/statische
    # Werte ausgibt.
    marker_option = BlockOptionSpec(
        name="__test_marker_option__",
        kind="text",
        allowed_values=None,
        validated=False,
        default=guide_generator.MISSING,
    )
    augmented_prose = dict(authoring_guide_prose.PROSE_SECTIONS)
    augmented_prose["block:task.__test_marker_option__"] = "Testmarker-Erklärung."
    monkeypatch.setattr(guide_generator, "PROSE_SECTIONS", augmented_prose)

    modified_blocks = tuple(
        replace(block, options=block.options + (marker_option,))
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


def _extract_fenced_markdown_block(guide_text: str, needle: str) -> str:
    """Holt den Inhalt des ersten ` ```markdown ` -Codeblocks, der `needle` enthält."""
    for match in re.finditer(r"```markdown\n(.*?)\n```", guide_text, re.DOTALL):
        if needle in match.group(1):
            return match.group(1)
    raise AssertionError(f"Kein ```markdown-Codeblock mit {needle!r} gefunden.")


def test_geometry_example_in_generated_guide_actually_validates_and_renders():
    """Regressionstest fuer die manuelle Verifikation des Geometry-Beispiels.

    Das im generierten Leitfaden gezeigte Flow-Style-YAML-Beispiel muss
    tatsaechlich fehlerfrei validieren UND als SVG mit allen drei
    Objektarten (points/pairs/functions) rendern -- nicht nur syntaktisch
    aussehen wie gueltiges Blattwerk-Markdown. `axis=true` ohne `origin`
    wuerde funktions-Eintraege still verschlucken (siehe Besonderheit bei
    `block:geometry.axis`), deshalb ist genau dieser Fall hier verdrahtet.
    """
    catalog = collect_markdown_conventions()
    guide_text = guide_generator.render_worksheet_presentation_guide(catalog)
    block_markdown = _extract_fenced_markdown_block(guide_text, ":::geometry rows=20")

    document = "---\nTitel: T\nFach: M\nThema: X\n---\n" + block_markdown + "\n"
    result = inspect_markdown_text(document)
    assert result.diagnostics == [], f"Beispiel validiert nicht sauber: {result.diagnostics}"

    header_line, content_lines = block_markdown.split("\n", 1)
    block_content = content_lines.rsplit(":::", 1)[0]
    assert "axis=true" in header_line
    assert 'origin="10,10"' in header_line

    svg = render_geometry_answer(
        {"rows": "20", "cols": "20", "axis": "true", "origin": "10,10"},
        block_content,
        True,
        True,
    )
    assert "A" in svg
    assert "Strecke g" in svg
    assert "f(x)" in svg
    assert "grid-segment-dashed" in svg
