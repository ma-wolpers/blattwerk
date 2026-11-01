"""Tests für die Diagramm-Registrierung und die gemeinsamen Textbausteine."""

from __future__ import annotations

from app.core._editable_convert_js import _IMAGE_ONLY_BLOCK_TYPES
from app.core.authoring_guide_prose import PROSE_SECTIONS
from app.core.blatt_validator_constants import BLOCK_ALLOWED_OPTIONS, KNOWN_BLOCK_TYPES
from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.core.diagram_block_catalog import DIAGRAM_BLOCKS, DIAGRAM_HEADER_RE
from app.core.diagram_block_dispatch import estimate_diagram_weight, render_diagram_block
from app.core.diagram_text import iter_source_lines, make_cell, render_cell

EXISTING_CODE_PREFIXES = {"AN", "BL", "CW", "EV", "FM", "IM", "KL", "MA", "MJ", "OP", "PK", "PT", "QR", "SC", "SL"}


def test_every_diagram_block_is_derived_everywhere():
    """Ein Katalogeintrag reicht: Validator, Snippets, PPTX-Liste und Prosa kennen den Block."""
    for spec in DIAGRAM_BLOCKS:
        assert spec.name in KNOWN_BLOCK_TYPES
        assert {"width", "show", "mode", "align"} <= BLOCK_ALLOWED_OPTIONS[spec.name]
        assert BLOCK_INSERT_SNIPPETS[spec.name] == spec.snippet
        assert spec.name in _IMAGE_ONLY_BLOCK_TYPES
        assert f"block:{spec.name}" in PROSE_SECTIONS
        assert DIAGRAM_HEADER_RE.match(f":::{spec.name} width=50%")


def test_diagram_names_are_lowercase_english_and_codes_are_unique():
    """Blocknamen ohne Umlaute; jeder Block hat einen eigenen Leer-Code außerhalb des Bestands."""
    codes = [spec.empty_code for spec in DIAGRAM_BLOCKS]
    assert len(codes) == len(set(codes))
    for spec in DIAGRAM_BLOCKS:
        assert spec.name.isascii() and spec.name.islower()
        assert spec.empty_code[:2] not in EXISTING_CODE_PREFIXES


def test_every_snippet_renders_and_estimates_a_weight():
    """Jedes Einfüge-Snippet ist gültig: Es rendert in beiden Fassungen etwas Sichtbares."""
    for spec in DIAGRAM_BLOCKS:
        content = "\n".join(spec.snippet.replace("\x01", "").splitlines()[1:-1])
        assert render_diagram_block(spec.name, {}, content, include_solutions=False)
        assert render_diagram_block(spec.name, {}, content, include_solutions=True)
        assert estimate_diagram_weight(spec.name, {}, content) > 0


def test_source_lines_keep_numbers_and_read_markers_after_indent():
    """Kommentar- und Leerzeilen zählen nicht, die sichtbare Zeilennummer bleibt."""
    lines = list(iter_source_lines("a\n\n%%Notiz%%\n    % b\n\t§ c\n"))
    assert [(line.number, line.width, line.show, line.text) for line in lines] == [
        (1, 0, "both", "a"),
        (4, 4, "solution", "b"),
        (5, 4, "worksheet", "c"),
    ]


def test_render_cell_hides_gap_in_worksheet_and_marks_it_in_solution():
    """Lücke: im Arbeitsblatt unsichtbar platzhaltend, in der Lösung sichtbar."""
    cell = make_cell("a %{b}")
    worksheet, worksheet_gap = render_cell(cell, include_solutions=False)
    solution, solution_gap = render_cell(cell, include_solutions=True)
    assert worksheet_gap and "diagram-hidden" in worksheet
    assert not solution_gap and "diagram-hidden" not in solution and "b" in solution


def test_render_cell_keeps_list_markers_and_escapes_html():
    """`- id` wird keine Liste, `a<b` kein HTML-Tag."""
    assert "<ul" not in render_cell(make_cell("- id: Ganzzahl"), False)[0]
    assert "a&lt;b" in render_cell(make_cell("a<b"), False)[0]
