"""Bonuspunkte `bonus=true`: zählen nicht zur Punktzahl (= 100 %), sind aber zusätzlich erreichbar.

Abgedeckt: Punktkern (regulär/Bonus, PK001 gegen die reguläre Summe, Bonus-
Aufgabe), Klausuranalyse (Summen und AFB ohne Bonus), Bewertungstabelle (kein
Bonus), Anzeige am Kopf („+2 Bonuspunkte“), Erwartungshorizont und die
Lösungsprüfung einer Bonus-Teilaufgabe gegen ihre eigenen Punkte.
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import inspect_markdown_text
from app.core.evaluation_table import build_evaluation_table
from app.core.exam_analysis import analyze_exam, format_analysis_lines
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.points_model import build_points_model, points_badge

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
WITH_BONUS_SUBTASK = (
    ":::task afb=1\nA\n:::\n:::subtask points=2\na\n:::\n:::solution\n1. x (2P)\n:::\n"
    ":::subtask points=2 afb=2 bonus=true\nb\n:::\n:::solution\n1. y (1/2P)\n2. z (1/2P)\n3. w (1/2P)\n:::\n"
    "--hm\n:::task points=3 afb=2\nB\n:::\n:::solution\n1. v (3P)\n:::\n"
)
BONUS_TASK = ":::task points=4 afb=1\nA\n:::\n:::task points=2 bonus=true\nZusatz\n:::\n:::solution\n1. q (2P)\n:::\n"


def _codes(body):
    """(Code, Schwere) der Punkt-/Lösungs-/Klausurdiagnosen."""
    return sorted((d.code, d.severity) for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code[:2] in ("SL", "PK", "KL"))


def test_bonus_subtask_counts_separately_and_task_points_match_regular_sum():
    """Aufgabe 1: 2 P regulär + 2 Bonuspunkte; `points=` an der Aufgabe meint die reguläre Summe."""
    unit = build_points_model(parse_blocks(WITH_BONUS_SUBTASK))[0]
    assert (unit.effective, unit.regular_points, unit.bonus_points) == (Decimal(2), Decimal(2), Decimal(2))
    assert _codes(WITH_BONUS_SUBTASK) == []
    assert _codes(WITH_BONUS_SUBTASK.replace(":::task afb=1", ":::task points=2 afb=1", 1)) == []
    assert ("PK001", "error") in _codes(WITH_BONUS_SUBTASK.replace(":::task afb=1", ":::task points=4 afb=1", 1))


def test_bonus_task_counts_only_as_bonus():
    """Eine Bonus-Aufgabe: regulär 0, Bonus = ihre Punkte; ihre Lösung wird gegen ihre Punkte geprüft."""
    units = build_points_model(parse_blocks(BONUS_TASK))
    assert (units[1].regular_points, units[1].bonus_points) == (Decimal(0), Decimal(2))
    assert _codes(BONUS_TASK) == []
    assert ("PK002", "error") in _codes(BONUS_TASK.replace("(2P)", "(1P)"))


def test_analysis_excludes_bonus_from_points_and_afb():
    """Teil A: 2 P (+2 Bonus), AFB nur aus regulären Punkten; Editor-Übersicht nennt den Bonus."""
    analysis = analyze_exam(parse_blocks(WITH_BONUS_SUBTASK), "exam")
    part_a, part_b = analysis.parts
    assert (part_a.points, part_a.bonus_points, part_b.points, analysis.total.points) == (Decimal(2), Decimal(2), Decimal(3), Decimal(5))
    assert analysis.total.afb_points[2] == Decimal(3)
    assert "Teil A: 2 P + 2 Bonuspunkte" in format_analysis_lines(analysis)


def test_evaluation_table_leaves_bonus_out():
    """Bewertungstabelle: Bonus erscheint nicht -- weder als Aufgabe noch als Teilaufgabe."""
    blocks = parse_blocks(WITH_BONUS_SUBTASK)
    by_task = build_evaluation_table(blocks, {}, "exam")
    assert [(c.label, c.points) for c in by_task.groups[0].cells] == [("1", Decimal(2)), ("2", Decimal(3))]
    by_subtask = build_evaluation_table(blocks, {"level": "subtask"}, "exam")
    assert [c.label for c in by_subtask.groups[0].cells] == ["1a", "2"]
    assert [c.label for c in build_evaluation_table(parse_blocks(BONUS_TASK), {}, "exam").groups[0].cells] == ["1"]


def test_heads_show_bonus_points():
    """Kopf: „+2 Bonuspunkte“ statt „2 P“, an Teilaufgabe und Aufgabe."""
    assert points_badge({"points": "2", "bonus": "true"}) == "+2 Bonuspunkte"
    assert points_badge({"points": "2"}) == "2 P"
    html = render_html({"Titel": "T"}, parse_blocks(WITH_BONUS_SUBTASK + BONUS_TASK), document_type="exam")
    assert "subtask-points'>+2 Bonuspunkte" in html and "task-points'>+2 Bonuspunkte" in html


def test_horizon_shows_bonus_separately():
    """Horizont: Aufgabe „2 P + 2 Bonuspunkte“, Teilaufgabe „+2 Bonuspunkte“, Teilsumme mit Bonus-Zusatz."""
    html, diagnostics = build_expectation_horizon_html(HEAD + WITH_BONUS_SUBTASK)
    assert "<h3>Aufgabe 1 (2 P + 2 Bonuspunkte)</h3>" in html and "Aufgabe 1b (+2 Bonuspunkte)" in html
    assert "Summe Teil A: 2 P + 2 Bonuspunkte" in html and "Summe Teil B: 3 P</p>" in html
    bonus_html, _ = build_expectation_horizon_html(HEAD + BONUS_TASK)
    assert re.search(r"<h3>Aufgabe 2 \(\+2 Bonuspunkte\)</h3>", bonus_html)
    assert diagnostics == []
