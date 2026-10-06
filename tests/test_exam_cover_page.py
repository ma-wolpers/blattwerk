"""Klausur-Deckblatt per zweitem `--hm` (Deckblatt | Teil A | Teil B).

Kernzusage: Ein Deckblatt darf keine bestehende Auswertung abschneiden. Dieselben
Aufgaben mit und ohne Deckblatt ergeben identische Punkte-Einheiten,
Lösungszuordnung, Klausur-Analyse, Erwartungshorizont und Evaluationsgruppen.
"""

from __future__ import annotations

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import inspect_markdown_text
from app.core.document_semantics import annotate_aid_parts, resolve_aid_split
from app.core.evaluation_table import build_evaluation_table
from app.core.exam_analysis import analyze_exam, format_analysis_lines
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.points_model import build_points_model
from app.core.solution_items import collect_solution_targets

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
COVER = (
    "Hinweise: Bearbeitungszeit 90 Minuten.\n\n"
    ":::info\nTaschenrechner erst in Teil B.\n:::\n\n"
    ":::evaluation parts=true:::\n\n"
    ":::evaluation:::\n\n"
)
PART_A = (
    ":::task afb=1\nTerme\n:::\n:::subtask points=2\na\n:::\n:::subtask points=3 afb=2\nb\n:::\n"
    ":::solution target=a\n1. x (2P)\n:::\n:::solution target=b\n1. y (3P)\n:::\n"
)
PART_B = ":::task points=5 afb=3\nModell\n:::\n:::solution\n1. z (5P)\n:::\n"
ONE_MARKER = PART_A + "--hm\n" + PART_B
WITH_COVER = COVER + "--hm\n" + PART_A + "--hm\n" + PART_B


def _blocks(body):
    return parse_blocks(body)


def _diagnostics(body):
    return inspect_markdown_text(HEAD + body, document_type="exam").diagnostics


def _units_signature(blocks):
    return [
        (unit.number, unit.status, unit.effective, [(sub.letter, sub.value) for sub in unit.subtasks])
        for unit in build_points_model(blocks)
    ]


def _targets_signature(blocks):
    targets, issues = collect_solution_targets(blocks)
    return [(t.unit_index, t.subtask_letter, [(i.text, i.points) for i in t.items]) for t in targets], [i.code for i in issues]


def test_resolve_with_cover_keeps_ab_boundary_and_marks_cover():
    blocks = _blocks(WITH_COVER)
    split = resolve_aid_split(blocks, "exam")
    markers = [i for i, (bt, _o, _c) in enumerate(blocks) if bt == "aidsplit"]
    assert split is not None and split.cover_end == markers[0] and split.index == markers[1]
    assert resolve_aid_split(_blocks(ONE_MARKER), "exam").cover_end is None


def test_realistic_cover_is_valid_without_errors():
    errors = [d for d in _diagnostics(WITH_COVER) if d.severity == "error"]
    assert errors == []


def test_points_and_solutions_identical_with_and_without_cover():
    assert _units_signature(_blocks(WITH_COVER)) == _units_signature(_blocks(ONE_MARKER))
    assert _targets_signature(_blocks(WITH_COVER)) == _targets_signature(_blocks(ONE_MARKER))


def test_exam_analysis_identical_with_and_without_cover():
    with_cover, plain = analyze_exam(_blocks(WITH_COVER), "exam"), analyze_exam(_blocks(ONE_MARKER), "exam")
    assert format_analysis_lines(with_cover) == format_analysis_lines(plain)
    assert [p.points for p in with_cover.parts] == [p.points for p in plain.parts] != []


def test_expectation_horizon_identical_with_and_without_cover():
    def horizon(body):
        html, diagnostics = build_expectation_horizon_html(HEAD + body)
        return html, [d.code for d in diagnostics]

    assert horizon(WITH_COVER) == horizon(ONE_MARKER)


def test_evaluation_groups_identical_with_and_without_cover():
    for options in ({}, {"parts": "true"}, {"level": "subtask", "parts": "true"}):
        with_cover = build_evaluation_table(_blocks(WITH_COVER), options, "exam")
        plain = build_evaluation_table(_blocks(ONE_MARKER), options, "exam")
        assert [(g.title, [(c.label, c.points) for c in g.cells]) for g in with_cover.groups] == [
            (g.title, [(c.label, c.points) for c in g.cells]) for g in plain.groups
        ]


def test_cover_has_no_part_heading_and_part_a_starts_on_new_page():
    html = render_html({"Titel": "T"}, _blocks(WITH_COVER), document_type="exam")
    assert html.index("Bearbeitungszeit") < html.index("Teil A – hilfsmittelfrei") < html.index("Aufgabe 1")
    assert html.index("Aufgabe 1") < html.index("Teil B – mit Hilfsmitteln") < html.index("Aufgabe 2")
    assert html.count("class='ab-pagebreak'") == 2
    annotated = annotate_aid_parts(_blocks(WITH_COVER), "exam")
    assert annotated[0][0] != "aidsplit"


@pytest.mark.parametrize("before", [":::task points=1 afb=1\nX\n:::\n", ":::subtask points=1\nx\n:::\n", ":::solution\n1. x\n:::\n"])
def test_task_related_block_before_cover_marker_is_kl007(before):
    body = before + "--hm\n" + PART_A + "--hm\n" + PART_B
    assert any(d.code == "KL007" and d.severity == "error" for d in _diagnostics(body))
    assert resolve_aid_split(_blocks(body), "exam") is None


def test_empty_part_a_is_kl004():
    body = COVER + "--hm\n--hm\n" + PART_B
    assert any(d.code == "KL004" and d.severity == "error" for d in _diagnostics(body))


def test_subtask_alone_does_not_count_as_task_in_part_a():
    body = COVER + "--hm\n:::subtask points=1\nlose\n:::\n--hm\n" + PART_B
    codes = {d.code for d in _diagnostics(body) if d.severity == "error"}
    assert codes & {"KL004", "KL005"}
    assert resolve_aid_split(_blocks(body), "exam") is None


def test_cover_followed_by_non_task_is_kl005():
    body = COVER + "--hm\n:::solution\n1. x\n:::\n" + PART_A + "--hm\n" + PART_B
    assert any(d.code == "KL005" and d.severity == "error" for d in _diagnostics(body))


def test_three_markers_report_kl001_and_no_split():
    body = WITH_COVER + "--hm\n:::task points=1 afb=1\nC\n:::\n"
    assert any(d.code == "KL001" and d.severity == "error" for d in _diagnostics(body))
    assert resolve_aid_split(_blocks(body), "exam") is None


def test_cover_markers_outside_exam_only_warn():
    codes = [d.code for d in inspect_markdown_text(HEAD + WITH_COVER, document_type="worksheet").diagnostics]
    assert codes.count("KL002") == 2
