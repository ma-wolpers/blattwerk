"""Punkt-Suffix-Vertrag (`points_suffix`) und alternative Wege `(0,5aP)`.

Abgedeckt: jeder Status des Vertrags (none/valid/invalid), dass unlesbare
Suffixe keinen Zahlenwert tragen und genau eine Diagnose auslösen, der
Geltungsbereich der Weg-Buchstaben (ein Ziel), die exakte Decimal-Summe
sowie der echte Validierungs- und Exportpfad. Summative Optionen `(x/kP)`:
tests/test_solution_options.py.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_kern_task_render import render_block
from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_text
from app.core.exam_expectation_horizon import build_expectation_horizon, build_expectation_horizon_html
from app.core.points_suffix import (
    SUFFIX_INVALID,
    SUFFIX_NONE,
    SUFFIX_VALID,
    parse_points_suffix,
)
from app.core.solution_items import collect_solution_targets, parse_solution_items

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
SNAIL_6C = (
    ":::task afb=2\nSchnecke\n:::\n:::subtask points=2\nc\n:::\n:::solution\n"
    "1. Entweder: Der Graph verläuft flacher (0,5aP)\n"
    "2. und: Die Änderungsrate ist kleiner (0,5aP)\n"
    "3. Oder: Steigung berechnen (1bP)\n"
    "4. In beiden Fällen: langsamer (0,5P)\n"
    "5. Sinngemäß: Antwortsatz (0,5P)\n:::\n"
)


def _codes(body):
    """(Code, Schwere) der Punkt-/Lösungsdiagnosen einer Klausur."""
    return sorted((d.code, d.severity) for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code[:2] in ("SL", "PK"))


def _task(points, *lines):
    """Aufgabe mit `points=` und einer Lösung aus den gegebenen Punktzeilen."""
    return f":::task points={points} afb=1\nA\n:::\n:::solution\n" + "".join(f"{n}. Schritt {n} {s}\n" for n, s in enumerate(lines, 1)) + ":::\n"


@pytest.mark.parametrize(
    ("head", "status", "value", "path"),
    [
        ("Ansatz (2P)", SUFFIX_VALID, Decimal(2), None),
        ("Ansatz (0,5P)", SUFFIX_VALID, Decimal("0.5"), None),
        ("Ansatz (0.5 P)", SUFFIX_VALID, Decimal("0.5"), None),
        ("Ansatz (0,5aP)", SUFFIX_VALID, Decimal("0.5"), "a"),
        ("Ansatz ( 1 b P )  ", SUFFIX_VALID, Decimal(1), "b"),
        ("Ansatz (3 Punkte)", SUFFIX_NONE, None, None),
        ("Ansatz (2 Pkt)", SUFFIX_NONE, None, None),
        ("f(2) = 3", SUFFIX_NONE, None, None),
        ("Ansatz (2P) im Text", SUFFIX_NONE, None, None),
        ("Option (1/3P)", SUFFIX_VALID, Decimal(1), None),
        ("Option (1,5 / 3 P)", SUFFIX_VALID, Decimal("1.5"), None),
        ("Option (1/2P An)", SUFFIX_VALID, Decimal(1), None),
        ("Option (1a/2P)", SUFFIX_INVALID, None, None),
        ("Option (-1/2P)", SUFFIX_INVALID, None, None),
        ("Ansatz (0,5abP)", SUFFIX_INVALID, None, None),
        ("Ansatz (-1P)", SUFFIX_VALID, Decimal(-1), None),
        ("Ansatz (−0,5P)", SUFFIX_VALID, Decimal("-0.5"), None),
        ("Ansatz (– 1 a P)", SUFFIX_VALID, Decimal(-1), "a"),
        ("Ansatz (-1P An)", SUFFIX_VALID, Decimal(-1), None),
        ("Ansatz (1P An)", SUFFIX_VALID, Decimal(1), None),
        ("Ansatz (1P An Er)", SUFFIX_INVALID, None, None),
        ("Ansatz (1AP)", SUFFIX_INVALID, None, None),
    ],
)
def test_suffix_contract_status_and_value(head, status, value, path):
    """Jeder Status; nur `valid` trägt Zahlenwert und Weg."""
    suffix = parse_points_suffix(head)
    assert (suffix.status, suffix.value, suffix.path) == (status, value, path)


def test_invalid_items_carry_no_points_and_keep_their_text():
    """Kein Zahlenwert für unlesbare Suffixe; das Suffix bleibt im Erwartungstext sichtbar."""
    items, _misplaced = parse_solution_items("1. b (0,5abP)\n2. c (1aP)\n")
    assert [(i.text, i.points, i.path, i.suffix_status) for i in items] == [
        ("b (0,5abP)", None, None, SUFFIX_INVALID),
        ("c", Decimal(1), "a", SUFFIX_VALID),
    ]


def test_invalid_suffix_reports_only_sl018_and_no_sum_check():
    """Unlesbar: SL018 (Fehler) je Punkt; die übrigen Werte werden nicht summiert."""
    assert _codes(_task(2, "(0,5abP)", "(1P)")) == [("SL018", "error")]
    assert _codes(_task(2, "(1 a b P)", "(5P)")) == [("SL018", "error")]


def test_snail_6c_paths_sum_to_points():
    """Weg a (0,5+0,5) oder Weg b (1), gemeinsam 0,5+0,5: exakt 2 Punkte, keine Meldung."""
    assert _codes(SNAIL_6C) == []


def test_wrong_path_sum_is_pk002_naming_shared_and_best_path():
    """Bester Weg zu groß → PK002 mit gemeinsam + bester Weg."""
    diagnostics = inspect_markdown_text(HEAD + SNAIL_6C.replace("(1bP)", "(2bP)"), document_type="exam").diagnostics
    pk002 = [d for d in diagnostics if d.code == "PK002"]
    assert len(pk002) == 1 and pk002[0].severity == "error"
    assert "gemeinsam 1 + bester Weg B 2 = 3" in pk002[0].message


def test_paths_of_different_length_take_the_best_path():
    """Wege verschiedener Länge: max über die Wegsummen, nicht über Einzelpunkte."""
    assert _codes(_task(3, "(1aP)", "(1aP)", "(1aP)", "(2bP)", "(1P)")) == [("PK002", "error")]
    assert _codes(_task(4, "(1aP)", "(1aP)", "(1aP)", "(2bP)", "(1P)")) == []


def test_single_path_letter_is_sl015_warning():
    """Nur ein Buchstabe: keine echte Alternative (Warnung), im Text als „Weg A“."""
    assert _codes(_task(2, "(1aP)", "(1P)")) == [("SL015", "warning")]
    messages = [d.message for d in inspect_markdown_text(HEAD + _task(2, "(1aP)", "(1P)"), document_type="exam").diagnostics]
    assert any("Nur Weg A (`a`)" in m for m in messages)


def test_path_scope_is_one_target_subtasks_are_independent():
    """Teilaufgabe a mit a/b, Teilaufgabe b nur mit a: SL015 nur bei b; Summen getrennt."""
    body = (
        ":::task afb=1\nA\n:::\n:::subtask points=1\na\n:::\n:::subtask points=2\nb\n:::\n"
        ":::solution target=a\n1. x (1aP)\n2. y (1bP)\n:::\n"
        ":::solution target=b\n1. z (1aP)\n2. w (1P)\n:::\n"
    )
    diagnostics = [d for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code[:2] in ("SL", "PK")]
    assert [(d.code, "1b" in d.message) for d in diagnostics] == [("SL015", True)]


def test_two_solution_blocks_of_one_target_share_their_letters():
    """Zwei Lösungsblöcke derselben Teilaufgabe bilden ein Ziel: a und b sind eine Wahl."""
    body = ":::task points=1 afb=1\nA\n:::\n:::solution\n1. x (1aP)\n:::\n:::solution\n1. y (1bP)\n:::\n"
    assert _codes(body) == []
    targets, _issues = collect_solution_targets(parse_blocks(body))
    assert [(item.path, item.points) for item in targets[0].items] == [("a", Decimal(1)), ("b", Decimal(1))]


def test_aid_split_separates_path_groups():
    """Vor und nach `--hm` sind getrennte Aufgaben: kein gemeinsamer Weg, je SL015."""
    body = ":::task points=1 afb=1\nA\n:::\n:::solution\n1. x (1aP)\n:::\n--hm\n:::task points=1 afb=1\nB\n:::\n:::solution\n1. y (1bP)\n:::\n"
    assert _codes(body) == [("SL015", "warning"), ("SL015", "warning")]


def test_task_level_and_subtask_targets_are_separate():
    """Aufgabenebene und Teilaufgabe teilen keine Buchstaben."""
    body = (
        ":::task points=2 afb=1\nA\n:::\n:::subtask\na\n:::\n:::subtask\nb\n:::\n"
        ":::solution target=task\n1. x (1aP)\n2. y (1P)\n:::\n:::solution target=a\n1. z (1bP)\n:::\n"
    )
    sl015 = [d.message for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code == "SL015"]
    assert len(sl015) == 2 and any("Aufgabe 1:" in m for m in sl015) and any("Aufgabe 1a:" in m for m in sl015)


@pytest.mark.parametrize(
    ("points", "lines", "expected"),
    [
        ("0.3", ("(0,1P)", "(0,2P)"), []),
        ("0,3", ("(0,1aP)", "(0,2aP)", "(0,3bP)"), []),
        ("0,30", ("(0.1P)", "(0.2P)"), []),
        ("0,3", ("(0,1P)", "(0,1P)"), [("PK002", "error")]),
    ],
)
def test_sums_are_exact_decimals_without_float_effects(points, lines, expected):
    """0,1 + 0,2 ist in float 0.30000000000000004 -- hier exakt 0,3 (Decimal aus Strings)."""
    assert _codes(_task(points, *lines)) == expected


def test_subtask_points_with_tenths_compare_exactly():
    """Zielwerte aus Teilaufgaben (`subtask_effective`) sind ebenfalls exakte Decimals."""
    body = (
        ":::task afb=1\nA\n:::\n:::subtask points=0,1\na\n:::\n:::subtask points=0.2\nb\n:::\n"
        ":::solution target=a\n1. x (0.1P)\n:::\n:::solution target=b\n1. y (0,1P)\n2. z (0,1P)\n:::\n"
    )
    assert _codes(body) == []


def test_solution_display_normalizes_valid_suffix_and_keeps_others_raw():
    """Lösung: `(0,5P, Weg A)`, `(1P)`; unlesbare Suffixe bleiben sichtbar unverändert."""
    html = render_block("solution", {}, "1. a (0.5aP)\n2. b (1 P)\n3. d (0,5abP)", include_solutions=True)
    assert "a (0,5P, Weg A)" in html and "b (1P)" in html and "d (0,5abP)" in html


def test_expectation_horizon_marks_paths_and_shows_plain_points():
    """Horizont: `Weg A:` vor dem Text (großgeschrieben), Punktspalte ohne Bruch."""
    html, diagnostics = build_expectation_horizon_html(HEAD + SNAIL_6C)
    assert "<span class='path'>Weg A:</span> Entweder" in html and "<span class='path'>Weg B:</span> Oder" in html
    points_cells = re.findall(r"<td class='pts'>([^<]*)</td>", html)
    assert "0,5" in points_cells and "1" in points_cells and not any("/" in cell for cell in points_cells)
    assert diagnostics == []


@pytest.mark.parametrize("suffix", ["(1a/2P)", "(0,5abP)"])
def test_unreadable_suffix_blocks_validation_and_every_export_path(tmp_path, suffix):
    """Integration: Fehler im Validator, Horizont-Export wirft ohne Datei, Klausur-Export blockiert, Vorschau läuft."""
    from app.core.blatt_kern_io_build import build_worksheet

    body = f":::task points=2 afb=1\nA\n:::\n:::solution\n1. a {suffix}\n2. b (1P)\n:::\n"
    diagnostics = inspect_markdown_text(HEAD + body, document_type="exam").diagnostics
    assert has_blocking_diagnostics(diagnostics)
    source = tmp_path / "klausur.kbw"
    source.write_text(HEAD + body, encoding="utf-8")
    horizon = tmp_path / "horizont.pdf"
    with pytest.raises(ValueError):
        build_expectation_horizon(source, horizon)
    assert not horizon.exists()
    exported = tmp_path / "klausur.pdf"
    with pytest.raises(Exception):
        build_worksheet(source, exported, document_type="exam", include_solutions=True, block_on_critical=True)
    assert not exported.exists()
    preview = render_block("solution", {}, f"1. a {suffix}\n2. b (1P)", include_solutions=True)
    assert suffix in preview
