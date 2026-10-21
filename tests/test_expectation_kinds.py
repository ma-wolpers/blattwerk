"""Erwartungstypen `(0,5P An)` / `(0,5P Ansatz)`: Katalog, Auflösung, Diagnose, Darstellung.

Der Typ ist optional, ein unbekannter Typ nur eine Warnung (SL017) -- Wert
und Weg zählen trotzdem. Die Lösung blendet das Token aus; der
Erwartungshorizont zeigt das Symbol vor dem Text und eine Legende der
tatsächlich verwendeten Typen. Typisierte Abzüge sind ausdrücklich erlaubt.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.core.blatt_kern_task_render import render_block
from app.core.blatt_validator import inspect_markdown_text
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.expectation_kinds import EXPECTATION_KINDS, resolve_expectation_kind
from app.core.solution_items import parse_solution_items, solution_points_total

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"


def _codes(body):
    """(Code, Schwere) der Punkt-/Lösungsdiagnosen einer Klausur."""
    return sorted((d.code, d.severity) for d in inspect_markdown_text(HEAD + body, document_type="exam").diagnostics if d.code[:2] in ("SL", "PK"))


def _task(points, *lines):
    """Aufgabe mit `points=` und einer Lösung aus den gegebenen Punktzeilen."""
    return f":::task points={points} afb=1\nA\n:::\n:::solution\n" + "".join(f"{n}. Schritt {n} {s}\n" for n, s in enumerate(lines, 1)) + ":::\n"


def test_tokens_are_unique_across_the_catalog():
    """Kein Kürzel, Name oder Alias darf zwei Typen meinen (ohne Groß-/Kleinschreibung)."""
    tokens = [token for kind in EXPECTATION_KINDS for token in kind.tokens()]
    assert len(tokens) == len(set(tokens))
    assert len(EXPECTATION_KINDS) == 11


@pytest.mark.parametrize(
    ("token", "key"),
    [("An", "ansatz"), ("ansatz", "ansatz"), ("AW", "anwendung"), ("Sa", "antwortsatz"), ("Fs", "fachsprache"),
     ("En", "entscheidung"), ("Er", "ergebnis"), ("Be", "beobachtung"), ("Bg", "begruendung"), ("Begründung", "begruendung"),
     ("Begruendung", "begruendung"), ("Ei", "einheit"), ("Größe", "einheit"), ("Groesse", "einheit"),
     ("Einheit/Größe", "einheit"), ("Da", "darstellung"), ("Fo", "formales"), ("formal", "formales"), ("Rechnung", None), ("Xy", None)],
)
def test_resolution_by_name_abbreviation_alias_case_insensitive(token, key):
    """Name, Kürzel, Alias; „Rechnung“ ist bewusst kein Typ."""
    kind = resolve_expectation_kind(token)
    assert (kind.key if kind else None) == key


def test_kind_combines_with_path_and_counts_normally():
    """`(0,5aP An)`: Wert und Weg wie ohne Typ; Typ zusätzlich."""
    items, _misplaced = parse_solution_items("1. a (0,5aP An)\n2. b (0,5bP Aw)\n3. c (0,5P Er)\n")
    assert [(i.points, i.path, i.kind) for i in items] == [
        (Decimal("0.5"), "a", "ansatz"), (Decimal("0.5"), "b", "anwendung"), (Decimal("0.5"), None, "ergebnis"),
    ]
    assert _codes(_task(1, "(0,5aP An)", "(0,5bP Aw)", "(0,5P Er)")) == []


def test_missing_kind_is_fine_and_unknown_kind_is_sl017_but_still_counts():
    """Kein Typ: keine Diagnose. Unbekannter Typ: SL017 mit Liste, Punkt zählt im Weg weiter."""
    assert _codes(_task(1, "(1P)")) == []
    diagnostics = inspect_markdown_text(HEAD + _task(2, "(1aP Xy)", "(1bP)", "(1P)"), document_type="exam").diagnostics
    codes = [(d.code, d.severity) for d in diagnostics if d.code[:2] in ("SL", "PK")]
    assert codes == [("SL017", "warning")]
    assert "Ansatz (An)" in next(d.message for d in diagnostics if d.code == "SL017")
    items, _misplaced = parse_solution_items("1. x (1aP Xy)\n2. y (1bP)\n")
    assert solution_points_total(items).total == Decimal(1) and items[0].kind is None and items[0].kind_token == "Xy"


@pytest.mark.parametrize(("suffix", "codes"), [("(−1P Bg)", []), ("(−1aP Bg)", [("SL016", "warning")]), ("(−1P Xy)", [("SL017", "warning")])])
def test_typed_deductions(suffix, codes):
    """Typisierte Abzüge: gültig, mit/ohne Buchstabe (SL016), unbekannter Typ (SL017); Abzug bleibt Abzug."""
    assert _codes(_task(2, "(2P Bg)", suffix)) == codes
    items, _misplaced = parse_solution_items(f"1. Je falsche Begründung {suffix}\n")
    assert items[0].is_deduction and items[0].points == Decimal(-1)


def test_solution_hides_the_kind_token_and_shows_no_symbol():
    """Lösungsversion: kein Typ-Token, kein Symbol."""
    html = render_block("solution", {}, "1. Ansatz (0,5aP An)\n2. Je Fehler (-1P Bg)", include_solutions=True)
    assert "Ansatz (0,5P, Weg A)" in html and "Je Fehler (−1P)" in html
    assert "An)" not in html and "Bg" not in html and "💡" not in html and "🧩" not in html


def test_horizon_shows_symbols_and_one_legend_of_used_kinds_including_deductions():
    """Horizont: Symbol vor dem Text (auch in der Abzugszeile), eine Legende in Katalogreihenfolge vor der AFB-Tabelle."""
    body = (
        _task(2, "(1P Er)", "(1P An)", "(-1P Bg)")
        + ":::task points=1 afb=2\nB\n:::\n:::solution\n1. Satz (1P Sa)\n:::\n"
    )
    html, diagnostics = build_expectation_horizon_html(HEAD + body)
    assert "<span class='kind' title='Ergebnis'>✅</span> Schritt 1" in html
    assert re.search(r"<tr class='deduction'>.*?<span class='kind' title='Begründung'>🧩</span>", html)
    legend = re.search(r"<h2>Erwartungstypen</h2>.*?</table>", html, re.S).group(0)
    assert re.findall(r"<td>([^<]+)</td></tr>", legend) == ["Ansatz", "Antwortsatz", "Ergebnis", "Begründung"]
    assert html.count("<h2>Erwartungstypen</h2>") == 1 and html.index("Erwartungstypen") < html.index("Anforderungsbereiche")
    assert diagnostics == []


def test_horizon_without_kinds_has_no_legend():
    """Ohne Typen keine Legende."""
    html, _diagnostics = build_expectation_horizon_html(HEAD + _task(1, "(1P)"))
    assert "Erwartungstypen" not in html and "class='kind'" not in html
