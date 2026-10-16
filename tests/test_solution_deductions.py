"""Minuspunkte in Lösungen: `(−0,5P)` ist ein Abzug je Fehler.

Abzüge zählen in keine Summe (die Pluspunkte ergeben die Punktzahl), gehören
zu keinem Weg (ein Buchstabe daran ist wirkungslos, SL016) und stehen im
Erwartungshorizont getrennt am Tabellenende.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.core.blatt_kern_task_render import render_block
from app.core.blatt_validator import inspect_markdown_text
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.points_model import format_signed_points
from app.core.solution_items import parse_solution_items, solution_points_total

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
CHECKBOXES = (
    ":::task points=2 afb=1\nKreuze an.\n:::\n:::solution\n"
    "1. Aussage 1 richtig angekreuzt (0,5P)\n2. Aussage 2 (0,5P)\n3. Aussage 3 (0,5P)\n4. Aussage 4 (0,5P)\n"
    "5. Je falsch gesetztes Kreuz (−0,5P)\n:::\n"
)
REASONS = ":::task points=3 afb=2\nBegründe.\n:::\n:::solution\n1. Begründung vollständig (3P)\n2. Je falsche Begründung (-1P)\n:::\n"


def _codes(body):
    """(Code, Schwere) der Punkt-/Lösungsdiagnosen einer Klausur."""
    return sorted((d.code, d.severity) for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code[:2] in ("SL", "PK"))


@pytest.mark.parametrize("minus", ["-", "−", "–"])
def test_all_three_minus_signs_give_a_deduction(minus):
    """Bindestrich, typografisches Minus und Gedankenstrich (Word-Autokorrektur) gelten gleich."""
    items, _misplaced = parse_solution_items(f"1. Je Fehler ({minus}0,5P)\n")
    assert items[0].points == Decimal("-0.5") and items[0].is_deduction


def test_deductions_do_not_count_towards_the_sum():
    """Ankreuzaufgabe und Begründung: nur die Pluspunkte müssen die Punktzahl ergeben."""
    assert _codes(CHECKBOXES) == []
    assert _codes(REASONS) == []
    items, _misplaced = parse_solution_items("1. a (1P)\n2. b (1aP)\n3. c (2bP)\n4. Abzug (-5P)\n5. Abzug (-1aP)\n")
    assert solution_points_total(items).total == Decimal(3)


def test_only_deductions_is_a_sum_error():
    """Ohne Pluspunkte ist die erreichbare Summe 0 -- PK002."""
    assert _codes(":::task points=2 afb=1\nA\n:::\n:::solution\n1. Je Fehler (–1P)\n:::\n") == [("PK002", "error")]


def test_deduction_with_path_letter_is_sl016_and_no_path():
    """Buchstabe an einem Abzug: SL016, und er zählt nicht als Weg (kein SL015)."""
    body = CHECKBOXES.replace("(−0,5P)", "(−0,5aP)")
    assert _codes(body) == [("SL016", "warning")]


def test_solution_shows_typographic_minus_and_never_a_path():
    """Lösung: `(−0,5P)` mit U+2212, auch wenn ein Buchstabe dabeisteht."""
    html = render_block("solution", {}, "1. a (1P)\n2. Je falsch (-0,5aP)", include_solutions=True)
    assert "Je falsch (−0,5P)" in html and "Weg" not in html


def test_expectation_horizon_lists_deductions_last_and_separately():
    """Horizont: Abzüge am Tabellenende, eigene Klasse, „Abzug je Fehler“, Punktspalte −0,5, keine Nummer."""
    html, diagnostics = build_expectation_horizon_html(HEAD + CHECKBOXES)
    rows = re.findall(r"<tr(?: class='(\w+)')?><td class='num'>(\d*)</td><td>(.*?)</td><td class='pts'>([^<]*)</td>", html)
    assert rows[-1][0] == "deduction" and rows[-1][1] == "" and "Abzug je Fehler:" in rows[-1][2] and rows[-1][3] == "−0,5"
    assert [row[1] for row in rows[:-1]] == ["1", "2", "3", "4"]
    assert diagnostics == []


def test_format_signed_points():
    """Negative Werte mit typografischem Minus, positive unverändert."""
    assert (format_signed_points(Decimal("-0.5")), format_signed_points(Decimal(2))) == ("−0,5", "2")
