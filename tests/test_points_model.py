"""Punktkern, Lösungszuordnung und Punkt-Diagnosen (Invariante I4, Phase 4)."""

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import inspect_markdown_text
from app.core.points_model import (
    NON_NUMERIC,
    STATUS_INCONSISTENT,
    STATUS_OK,
    build_points_model,
    parse_points,
)
from app.core.solution_items import collect_solution_targets

HEAD = "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n"


def _units(body):
    return build_points_model(parse_blocks(body))


def _codes(body, document_type="worksheet"):
    return [d.code for d in inspect_markdown_text(HEAD + body, document_type=document_type).diagnostics]


@pytest.mark.parametrize(("raw", "expected"), [("2", Decimal(2)), ("2,5", Decimal("2.5")), ("2.5", Decimal("2.5")), (None, None), ("", None), ("ca. 5", NON_NUMERIC)])
def test_parse_points(raw, expected):
    assert parse_points(raw) == expected


def test_subtasks_without_task_points_sum_up_without_diagnostic():
    body = ":::task\nA\n:::\n:::subtask points=3\na\n:::\n:::subtask points=4\nb\n:::\n"
    unit = _units(body)[0]
    assert (unit.status, unit.effective) == (STATUS_OK, Decimal(7))
    assert not {"PK001", "PK004"} & set(_codes(body))


def test_task_points_matching_sum_ok_and_mismatch_is_pk001():
    ok = ":::task points=7\nA\n:::\n:::subtask points=3\na\n:::\n:::subtask points=4\nb\n:::\n"
    bad = ok.replace("points=7", "points=10")
    assert _units(ok)[0].effective == Decimal(7)
    unit = _units(bad)[0]
    assert (unit.status, unit.effective) == (STATUS_INCONSISTENT, None)
    assert "PK001" in _codes(bad)


def test_partially_pointed_subtasks_is_pk004():
    body = ":::task points=5\nA\n:::\n:::subtask points=3\na\n:::\n:::subtask\nb\n:::\n"
    assert _units(body)[0].status == STATUS_INCONSISTENT
    assert "PK004" in _codes(body)


def test_non_numeric_points_warn_pk003_and_still_render():
    body = ":::task points=viele\nA\n:::\n"
    assert "PK003" in _codes(body)
    html_points = [d for d in inspect_markdown_text(HEAD + body).diagnostics if d.code == "PK003"]
    assert html_points[0].severity == "warning"


def test_solution_points_sum_matches_or_pk002():
    good = ":::task points=4\nA\n:::\n:::solution\n1. Ansatz (2P)\n2. Ergebnis (1,5P)\n3. Einheit (0,5P)\n:::\n"
    bad = good.replace("(0,5P)", "(1P)")
    assert "PK002" not in _codes(good)
    assert "PK002" in _codes(bad)


def test_solution_after_subtasks_belongs_to_last_subtask_and_target_overrides():
    body = (
        ":::task\nA\n:::\n:::subtask points=2\na\n:::\n:::subtask points=3\nb\n:::\n"
        ":::solution\n1. zu b (3P)\n:::\n"
        ":::solution target=a\n1. zu a (2P)\n:::\n"
        ":::solution target=B\n1. auch zu b\n:::\n"
    )
    targets, issues = collect_solution_targets(parse_blocks(body))
    assert issues == []
    by_letter = {t.subtask_letter: t for t in targets}
    assert [i.text for i in by_letter["b"].items] == ["zu b", "auch zu b"]
    assert [i.text for i in by_letter["a"].items] == ["zu a"]
    assert "SL006" in _codes(body)  # b: nur ein Teil annotiert


def test_target_task_after_subtasks_with_pointed_subtasks_is_pk005():
    body = ":::task\nA\n:::\n:::subtask points=2\na\n:::\n:::subtask points=2\nb\n:::\n:::solution target=task\n1. x (4P)\n:::\n"
    assert "PK005" in _codes(body)


@pytest.mark.parametrize("target", ["d", "zz", "1"])
def test_invalid_target_is_sl008_error(target):
    body = f":::task\nA\n:::\n:::subtask\na\n:::\n:::subtask\nb\n:::\n:::solution target={target}\n1. x\n:::\n"
    diagnostics = inspect_markdown_text(HEAD + body).diagnostics
    assert any(d.code == "SL008" and d.severity == "error" for d in diagnostics)


def test_target_letter_of_other_unit_is_sl008():
    body = ":::task\nA\n:::\n:::subtask\na\n:::\n:::subtask\nb\n:::\n:::task\nB\n:::\n:::solution target=b\n1. x\n:::\n"
    assert "SL008" in _codes(body)


def test_solution_without_preceding_task_is_sl001():
    assert "SL001" in _codes(":::solution\n1. x\n:::\n:::task\nA\n:::\n")


def test_solution_never_crosses_aid_split():
    # Blockliste direkt gebaut: die Zuordnung hängt nur am Pseudoblock `aidsplit`, nicht am Parser.
    blocks = [
        ("task", {"points": "2"}, "A"),
        ("aidsplit", {}, ""),
        ("solution", {}, "1. x (2P)"),
        ("task", {}, "B"),
    ]
    targets, issues = collect_solution_targets(blocks)
    assert targets == [] and [i.code for i in issues] == ["SL001"]


def test_misplaced_points_in_nested_or_bullet_item_is_sl004():
    body = ":::task points=2\nA\n:::\n:::solution\n1. Ansatz (2P)\n   - Detail (1P)\n- Stichpunkt (1P)\n:::\n"
    assert "SL004" in _codes(body)


def test_solution_points_without_task_points_is_pk006():
    assert "PK006" in _codes(":::task\nA\n:::\n:::solution\n1. x (2P)\n:::\n")


def test_points_diagnostics_only_for_worksheet_and_exam():
    body = ":::task points=10\nA\n:::\n:::subtask points=3\na\n:::\n:::subtask points=4\nb\n:::\n"
    assert "PK001" in _codes(body, "exam")
    assert "PK001" not in _codes(body, "presentation")


def test_errors_block_export():
    from app.core.blatt_validator import has_blocking_diagnostics

    body = ":::task points=10\nA\n:::\n:::subtask points=3\na\n:::\n:::subtask points=4\nb\n:::\n"
    assert has_blocking_diagnostics(inspect_markdown_text(HEAD + body).diagnostics)


def test_renderer_shows_points_display_also_non_numeric_and_subtask_points():
    from app.core.blatt_kern_task_render import render_block

    task_html = render_block("task", {"points": "ca. 5", "_show_task_label": "1"}, "A", include_solutions=False)
    sub_html = render_block("subtask", {"points": "2,5"}, "a", include_solutions=False)
    assert "ca. 5 P" in task_html and "2,5 P" in sub_html


def test_raw_points_option_is_read_only_in_points_model():
    app_root = Path(__file__).resolve().parents[1] / "app"
    offenders = []
    for path in app_root.rglob("*.py"):
        if path.name == "points_model.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            is_get = (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "points"
                and isinstance(node.func.value, ast.Name) and "option" in node.func.value.id
            )
            is_sub = (
                isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == "points"
                and isinstance(node.value, ast.Name) and "option" in node.value.id
            )
            if is_get or is_sub:
                offenders.append(f"{path.relative_to(app_root)}:{node.lineno}")
    assert offenders == []
