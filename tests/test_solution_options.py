"""Summative Optionen `(x/kP)`: „von diesen Möglichkeiten zählen zusammen höchstens k Punkte“.

Anders als Wege (`(1aP)`, nur der beste zählt) werden Optionen addiert und
bei k gekappt. Erreichbar: gemeinsam + bester Weg + min(Σ Optionen, k).
Prüfungen: SL019 (verschiedene k), SL020 (Option > k), SL021 (Σ < k),
SL022 (Σ = k, Schreibweise unnötig).
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.core.blatt_kern_task_render import render_block
from app.core.blatt_validator import inspect_markdown_text
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.solution_items import parse_solution_items, solution_points_total

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
TWO_OF_FOUR = (
    ":::task points=2 afb=2\nBegründe zwei Aussagen.\n:::\n:::solution\n"
    "1. Aussage 1 (falsch): … (1/2P Bg)\n2. Aussage 2 (wahr): … (1/2P Bg)\n"
    "3. Aussage 3 (falsch): … (1/2P Bg)\n4. Aussage 4 (falsch): … (1/2P Bg)\n"
    "5. Je falsche Begründung (−0,5P Bg)\n:::\n"
)


def _codes(body):
    """(Code, Schwere) der Punkt-/Lösungsdiagnosen einer Klausur."""
    return sorted((d.code, d.severity) for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code[:2] in ("SL", "PK"))


def _task(points, *lines):
    """Aufgabe mit `points=` und einer Lösung aus den gegebenen Punktzeilen."""
    return f":::task points={points} afb=1\nA\n:::\n:::solution\n" + "".join(f"{n}. Schritt {n} {s}\n" for n, s in enumerate(lines, 1)) + ":::\n"


def test_two_of_four_options_sum_to_the_cap():
    """3b-Fall: vier Begründungen à 1 P, höchstens 2 zählen -- plus ein typisierter Abzug."""
    assert _codes(TWO_OF_FOUR) == []
    items, _misplaced = parse_solution_items("1. a (1/2P)\n2. b (1/2P)\n3. c (1/2P)\n")
    total = solution_points_total(items)
    assert (total.options, total.option_caps, total.total) == (Decimal(3), frozenset({Decimal(2)}), Decimal(2))


def test_options_combine_with_shared_points_and_paths():
    """gemeinsam 1 + bester Weg 1 + Optionen min(3, 2) = 4."""
    assert _codes(_task(4, "(1P)", "(1aP)", "(1bP)", "(1/2P)", "(1/2P)", "(1/2P)")) == []
    diagnostics = inspect_markdown_text(HEAD + _task(5, "(1P)", "(1aP)", "(1bP)", "(1/2P)", "(1/2P)", "(1/2P)"), document_type="exam").diagnostics
    pk002 = next(d.message for d in diagnostics if d.code == "PK002")
    assert "gemeinsam 1 + bester Weg A 1 + Optionen 2 (hoechstens 2) = 4" in pk002


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (("(1/2P)", "(1/3P)", "(1/3P)"), [("SL019", "error")]),
        (("(3/2P)", "(1/2P)"), [("SL020", "error")]),
        (("(1/2P)",), [("SL021", "error")]),
        (("(1/2P)", "(1/2P)"), [("SL022", "warning")]),
    ],
)
def test_option_checks(lines, expected):
    """Verschiedene k, Option über k, Höchstwert nicht erreichbar (Fehler); genau erreichbar (Warnung)."""
    assert _codes(_task(2, *lines)) == expected


def test_options_are_no_paths_and_deductions_cannot_be_options():
    """Optionen lösen kein SL015 aus; `(−1/2P)` und `(1a/2P)` sind unlesbar (SL018)."""
    assert _codes(_task(2, "(1/2P)", "(1/2P)", "(1/2P)")) == []
    assert _codes(_task(2, "(-1/2P)", "(2P)")) == [("SL018", "error")]
    assert _codes(_task(2, "(1a/2P)", "(2P)")) == [("SL018", "error")]


def test_solution_shows_option_with_cap_and_hides_the_kind():
    """Lösung: `(1P, Option, max. 2P)`, kein Typ-Token, kein „Weg“."""
    html = render_block("solution", {}, "1. Aussage 1 (1/2P Bg)", include_solutions=True)
    assert "Aussage 1 (1P, Option, max. 2P)" in html and "Weg" not in html and "Bg" not in html


def test_horizon_marks_options_and_states_the_cap_once():
    """Horizont: `Option:` vor dem Text, eine Zeile „Optionen zählen zusammen höchstens 2 P“, Abzug am Ende."""
    html, diagnostics = build_expectation_horizon_html(HEAD + TWO_OF_FOUR)
    assert html.count("<span class='path'>Option:</span>") == 4 and "Weg" not in html
    rows = re.findall(r"<tr(?: class='([\w-]+)')?>", html.split("Aufgabe 1 (2 P)")[1].split("</table>")[0])
    assert rows[-2:] == ["option-cap", "deduction"]
    assert "Optionen zählen zusammen höchstens 2 P" in html and diagnostics == []
