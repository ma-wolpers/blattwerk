"""Erwartungsblöcke: Zerlegung nach Punktklammern, optionale Nummern, Sichtbarkeit.

`expectation_structure.classify_expectations` ist die einzige Zerlegung; die
Tests prüfen sie über `parse_expectation_items` (Text, Punkte, Nummer) für
Grenzfälle der Grammatik. Außerdem: `:::expectation` erscheint in keiner
Ausgabe, `:::solution` ist gewöhnliches Markdown ohne Punktauswertung.
"""

from __future__ import annotations

import pytest

from app.core.blatt_kern_task_render import render_block
from app.core.expectation_items import parse_expectation_items, solution_has_points


def _summary(content):
    """`(label, text, points)` je Erwartung, Punkte als Text (``None`` ohne gültiges Suffix)."""
    return [
        (item.label, item.text, None if item.points is None else str(item.points))
        for item in parse_expectation_items(content)
    ]


CASES = {
    "ohne_nummern": ("Ansatz (1P)\nErgebnis (1P)", [(None, "Ansatz", "1"), (None, "Ergebnis", "1")]),
    "mit_nummern": ("1. Ansatz (1P)\n2. Ergebnis (1P)", [("1", "Ansatz", "1"), ("2", "Ergebnis", "1")]),
    "gemischt": ("1. Schritt (1P)\nweiter (1P)", [("1", "Schritt", "1"), (None, "weiter", "1")]),
    "mehrzeilig": ("Ansatz mit\nzwei Zeilen (2P)\nEnde (1P)", [(None, "Ansatz mit zwei Zeilen", "2"), (None, "Ende", "1")]),
    "leerzeilen": ("A (1P)\n\n\nB (1P)\n", [(None, "A", "1"), (None, "B", "1")]),
    "rest_ohne_punkte": ("A (1P)\nRest", [(None, "A", "1"), (None, "Rest", None)]),
    "nummer_beendet_offene": ("1. offen\n2. B (1P)", [("1", "offen", None), ("2", "B", "1")]),
    "kommentar_zeilenende": ("A (1P) %%Notiz%%\nB (1P)", [(None, "A", "1"), (None, "B", "1")]),
    "kommentar_mehrzeilig": ("A (1P)\n%% weg (5P)\nauch weg (5P) %%\nB (1P)", [(None, "A", "1"), (None, "B", "1")]),
    "mathe_in_klammer": ("$f(x)=(2P)$ bleibt Text\nEnde (1P)", [(None, "$f(x)=(2P)$ bleibt Text Ende", "1")]),
    "mathe_mehrzeilig": ("$$\nx (2P)\n$$\ny (1P)", [(None, "$$ x (2P) $$ y", "1")]),
    "codezaun": ("```\nCode (2P)\n```\necht (1P)", [(None, "``` Code (2P) ``` echt", "1")]),
    "klammer_marker_ist_text": ("1) Punkt (1P)", [(None, "1) Punkt", "1")]),
    "zweistellig": ("10. A (1P)\n11. B (1P)", [("10", "A", "1"), ("11", "B", "1")]),
    "abzug": ("Je Fehler (−0,5P)", [(None, "Je Fehler", "-0.5")]),
    "unlesbar_bleibt_text": ("A (0,5abP)", [(None, "A (0,5abP)", None)]),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_expectations_are_split_by_points_suffix(name):
    """Jede Punktklammer am Zeilenende beendet eine Erwartung; Nummern sind optional."""
    content, expected = CASES[name]
    assert _summary(content) == expected


def test_suffix_inside_math_never_ends_an_expectation():
    """Eine Klammer, deren Ende in einer Formel liegt, zählt nie (geschützter Bereich)."""
    assert _summary("Wert $=(1P)$\nfertig (1P)")[0][2] == "1"
    assert len(parse_expectation_items("Wert $=(1P)$\nfertig (1P)")) == 1


def test_expectation_block_is_never_rendered():
    """`:::expectation` erscheint weder im Aufgabenblatt noch in der Lösung."""
    for include_solutions in (False, True):
        assert render_block("expectation", {}, "A (1P)", include_solutions=include_solutions, document_type="exam") == ""


def test_solution_is_plain_markdown():
    """`:::solution` rendert wie jeder Textblock: Listen bleiben Listen, Kommentare verschwinden."""
    html = render_block("solution", {}, "1. Schritt\n2. Ergebnis %%Notiz%%", include_solutions=True, document_type="exam")
    assert "<ol>" in html and "<li>Schritt</li>" in html and "<li>Ergebnis" in html and "Notiz" not in html


@pytest.mark.parametrize(
    ("content", "expected"),
    [("Rechnung $=5$ (1P)", True), ("1. Ansatz (0,5abP)", True), ("Ergebnis: $x=2$", False), ("(3 Punkte)", False)],
)
def test_solution_has_points_uses_the_expectation_grammar(content, expected):
    """SL024-Grundlage: gültige und unlesbare Klammern zählen, gewöhnliche Klammern nicht."""
    assert solution_has_points(content) is expected
