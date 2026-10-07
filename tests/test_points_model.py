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


def _diags(body):
    return inspect_markdown_text(HEAD + body).diagnostics


def _partial(lines, points=3):
    return f":::task points={points}\nA\n:::\n:::solution\n" + "".join(f"{n}. Weg {n} {s}\n" for n, s in enumerate(lines, 1)) + ":::\n"


def test_partial_points_item_parses_numerator_and_denominator():
    from app.core.solution_items import parse_solution_items

    items, misplaced = parse_solution_items("1. Weg A (1/3P)\n2. Weg B (1,5 / 3 P)\n3. normal (2P)\n")
    assert not misplaced
    assert [(i.text, i.points, i.of_total) for i in items] == [
        ("Weg A", Decimal(1), Decimal(3)),
        ("Weg B", Decimal("1.5"), Decimal(3)),
        ("normal", Decimal(2), None),
    ]


def test_partial_points_surplus_is_normal_case_without_diagnostics_and_without_pk002():
    # Σx = 6 > n = 3: alternative Wege, nicht summativ -- beabsichtigt.
    body = _partial(["(1/3P)", "(2/3P)", "(3/3P)"])
    codes = [d.code for d in _diags(body)]
    assert not {"PK002", "SL009", "SL010", "SL011", "SL012", "SL013"} & set(codes)


def test_partial_points_denominator_must_match_target_points_sl009_error():
    diagnostics = _diags(_partial(["(2/4P)", "(3/4P)"]))
    assert any(d.code == "SL009" and d.severity == "error" for d in diagnostics)


def test_partial_points_numerator_above_denominator_is_sl010_error():
    diagnostics = _diags(_partial(["(4/3P)", "(1/3P)"]))
    assert any(d.code == "SL010" and d.severity == "error" for d in diagnostics)


def test_partial_points_sum_below_target_is_sl011_error():
    diagnostics = _diags(_partial(["(1/3P)", "(1/3P)"]))
    assert any(d.code == "SL011" and d.severity == "error" for d in diagnostics)


def test_partial_points_sum_equal_target_is_redundant_sl012_warning():
    diagnostics = _diags(_partial(["(1/3P)", "(2/3P)"]))
    assert [(d.code, d.severity) for d in diagnostics if d.code.startswith(("SL", "PK"))] == [("SL012", "warning")]


def test_mixed_plain_and_partial_points_is_sl013_warning_without_sum_checks():
    codes = [d.code for d in _diags(_partial(["(1P)", "(2/3P)", "(3/3P)"]))]
    assert "SL013" in codes
    assert not {"PK002", "SL011", "SL012"} & set(codes)


def test_partial_points_on_subtask_compare_with_subtask_points():
    body = ":::task\nA\n:::\n:::subtask points=2\na\n:::\n:::subtask points=1\nb\n:::\n:::solution target=a\n1. x (2/2P)\n2. y (1/2P)\n:::\n:::solution\n1. z (1P)\n:::\n"
    codes = [d.code for d in _diags(body)]
    assert not {"PK002", "SL009", "SL011"} & set(codes)


def test_expectation_horizon_shows_partial_points_as_fraction():
    from app.core.exam_expectation_horizon import build_expectation_horizon_html

    head = "---\ndocument_type: exam\nTitel: K\nFach: M\n---\n"
    html, diagnostics = build_expectation_horizon_html(head + ":::task points=3 afb=1\nA\n:::\n:::solution\n1. Weg A (3/3P)\n2. Weg B (2/3P)\n:::\n")
    assert "<td class='pts'>3/3</td>" in html and "<td class='pts'>2/3</td>" in html
    assert "Aufgabe 1 (3 P)" in html
    assert diagnostics == []


@pytest.mark.parametrize(("raw", "expected"), [("0.5", "0,5"), ("2,50", "2,5"), ("3", "3"), ("ca. 5", "ca. 5"), ("  ", None)])
def test_points_label_normalizes_numbers_and_keeps_text(raw, expected):
    from app.core.points_model import points_label

    assert points_label({"points": raw}) == expected


def test_renderer_shows_half_points_with_german_comma_and_escapes_task_points():
    from app.core.blatt_kern_task_render import render_block

    task_html = render_block("task", {"points": "0.5", "_show_task_label": "1"}, "A", include_solutions=False)
    sub_html = render_block("subtask", {"points": "1.5"}, "a", include_solutions=False)
    evil_html = render_block("task", {"points": "<b>", "_show_task_label": "1"}, "A", include_solutions=False)
    assert "<span class='task-points'>0,5 P</span>" in task_html
    assert "1,5 P" in sub_html
    assert "&lt;b&gt; P" in evil_html


def test_half_points_sum_in_evaluation_table():
    from app.core.evaluation_table import build_evaluation_table, render_evaluation_html

    body = ":::task\nA\n:::\n:::subtask points=0,5\na\n:::\n:::subtask points=1,5\nb\n:::\n:::task points=2,5\nB\n:::\n"
    table = build_evaluation_table(parse_blocks(body), {"level": "subtask"}, "worksheet")
    assert table.groups[0].total == Decimal("4.5")
    html = render_evaluation_html(table)
    assert "<td>0,5</td>" in html and "<td>1,5</td>" in html and "<td>4,5</td>" in html


def test_subtask_points_have_fixed_right_column_like_task_header():
    css = (Path(__file__).resolve().parents[1] / "assets" / "worksheet.css").read_text(encoding="utf-8")
    meta_rule = css.split(".subtask-meta {", 1)[1].split("}", 1)[0]
    assert "grid-column: 4;" in meta_rule
    for selector, column in ((".subtask-prefix {", 1), (".subtask-symbols {", 2), (".subtask-content {", 3)):
        assert f"grid-column: {column};" in css.split(selector, 1)[1].split("}", 1)[0]


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
