"""Bewertungstabelle `:::evaluation:::` (Phase 7)."""

from decimal import Decimal

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import inspect_markdown_text
from app.core.block_insert_menu_families import BLOCK_INSERT_FAMILIES
from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.core.evaluation_table import build_evaluation_table, render_evaluation_html

HEAD = "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n"
BODY = ":::task points=2\nA\n:::\n:::task\nB\n:::\n:::subtask points=1\na\n:::\n:::subtask points=2\nb\n:::\n"


def _table(body, options=None, document_type="worksheet"):
    return build_evaluation_table(parse_blocks(body), options or {}, document_type)


def test_task_level_uses_effective_points_including_subtask_sums():
    table = _table(BODY)
    cells = table.groups[0].cells
    assert [(c.label, c.points) for c in cells] == [("1", Decimal(2)), ("2", Decimal(3))]
    assert table.groups[0].total == Decimal(5)


def test_subtask_level_splits_pointed_subtasks():
    cells = _table(BODY, {"level": "subtask"}).groups[0].cells
    assert [c.label for c in cells] == ["1", "2a", "2b"]


def test_missing_and_inconsistent_cells_and_no_sum():
    body = ":::task\nA\n:::\n:::task points=9\nB\n:::\n:::subtask points=1\na\n:::\n:::subtask points=2\nb\n:::\n"
    table = _table(body)
    assert [c.marker for c in table.groups[0].cells] == ["–", "?"]
    assert table.groups[0].total is None
    html = render_evaluation_html(table)
    assert "–*" in html and "Summe nicht ausgewiesen" in html


def test_parts_only_with_valid_aid_split_in_exam():
    body = ":::task points=2 afb=1\nA\n:::\n--hm\n:::task points=3 afb=1\nB\n:::\n"
    with_parts = _table(body, {"parts": "true"}, "exam")
    assert [g.title for g in with_parts.groups] == ["Teil A", "Teil B"]
    assert with_parts.grand_total == Decimal(5)
    assert "Gesamt: 5 P" in render_evaluation_html(with_parts)
    assert [g.title for g in _table(body, {"parts": "true"}, "worksheet").groups] == [None]
    assert [g.title for g in _table(body, {}, "exam").groups] == [None]


def test_rendered_in_worksheet_and_exam_but_not_in_presentation():
    blocks = parse_blocks(BODY + ":::evaluation:::\n")
    for document_type, expected in (("worksheet", True), ("exam", True), ("presentation", False)):
        body_html = render_html({"Titel": "T"}, blocks, document_type=document_type).split("</style>")[-1]
        assert ("evaluation-table" in body_html) is expected


def test_ev001_and_ev002():
    worksheet = [d.code for d in inspect_markdown_text(HEAD + ":::task\nA\n:::\n:::evaluation:::\n").diagnostics]
    presentation = [
        d.code
        for d in inspect_markdown_text(HEAD + ":::task points=1\nA\n:::\n:::evaluation:::\n", document_type="presentation").diagnostics
    ]
    assert "EV001" in worksheet and "EV002" in presentation


def test_level_value_is_validated():
    codes = [d.code for d in inspect_markdown_text(HEAD + ":::evaluation level=foo:::\n").diagnostics]
    assert "OP002" in codes


def test_insert_menu_and_snippet():
    families = dict(BLOCK_INSERT_FAMILIES)
    assert ("Bewertungstabelle (evaluation)", "evaluation") in families["Aufgaben"]
    assert BLOCK_INSERT_SNIPPETS["evaluation"].startswith(":::evaluation")
