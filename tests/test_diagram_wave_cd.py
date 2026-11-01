"""Tests für Bäume und datenbasierte Diagrammblöcke (Wellen C und D) und `diagram_numbers`."""

from __future__ import annotations

from fractions import Fraction

import pytest

from app.core.blatt_validator import inspect_markdown_text
from app.core.diagram_block_dispatch import render_diagram_block
from app.core.diagram_arrow import parse as parse_arrow
from app.core.diagram_memory import parse as parse_memory
from app.core.diagram_numbers import five_numbers, format_number, nice_ticks, parse_number, split_numbers
from app.core.diagram_probability import parse as parse_probability
from app.core.diagram_term import evaluate, parse as parse_term
from app.core.diagram_timeline import parse as parse_timeline
from app.core.diagram_timeline import time_value
from app.core.diagram_venn import set_names
from app.core.diagram_venn import parse as parse_venn

HEAD = "---\nTitel: T\nFach: M\nThema: X\n---\n"


def _codes(block: str, content: str, options: str = "") -> list[str]:
    """Validator-Codes eines Dokuments mit genau diesem Block."""
    text = f"{HEAD}:::{block} {options}\n{content}\n:::\n"
    return [d.code for d in inspect_markdown_text(text, document_type="worksheet").diagnostics]


def _gap_differs(block: str, content: str, options=None) -> None:
    """Arbeitsblatt und Lösung unterscheiden sich, die Lösung zeigt keine versteckten Teile."""
    worksheet = render_diagram_block(block, options or {}, content, include_solutions=False)
    solution = render_diagram_block(block, options or {}, content, include_solutions=True)
    assert worksheet and solution and worksheet != solution
    assert "diagram-hidden" not in solution


@pytest.mark.parametrize(
    ("text", "expected"),
    [("3", 3), ("3,5", Fraction(7, 2)), ("3.5", Fraction(7, 2)), ("1/3", Fraction(1, 3)), ("50%", Fraction(1, 2)), ("-2", -2), ("1/0", None), ("x", None), ("", None)],
)
def test_parse_number_reads_all_notations(text, expected):
    """Alle Schreibweisen; Unsinn ergibt `None`."""
    assert parse_number(text) == expected


def test_numbers_format_split_ticks_and_quartiles():
    """Anzeige mit Komma, Bruch bleibt Bruch; Listen, Achsen und Schulquartile."""
    assert format_number(Fraction(7, 2)) == "3,5"
    assert format_number(Fraction(1, 3)) == "1/3"
    assert format_number(Fraction(4)) == "4"
    assert split_numbers("1,5, 2; 3") == ["1,5", "2", "3"]
    ticks = nice_ticks(0.0, 12.0)
    assert ticks[0] == 0 and ticks[-1] >= 12
    assert nice_ticks(5.0, 5.0)
    assert five_numbers([Fraction(n) for n in (1, 2, 3, 4, 5, 6, 7)]) == (1, 2, 4, 6, 7)
    assert five_numbers([Fraction(n) for n in (1, 2, 3, 4)]) == (1, Fraction(3, 2), Fraction(5, 2), Fraction(7, 2), 4)
    assert five_numbers([Fraction(5)]) == (5, 5, 5, 5, 5)


def test_probability_tree_parses_nesting_and_checks_sums():
    """Einrückung ergibt Äste; die Summe wird auch bei Lücken nachgerechnet."""
    roots, issues = parse_probability("Rot: 1/3\n    Rot: 1/4\n    Blau: 3/4\nBlau: %{2/3}")
    assert not issues
    assert len(roots[0].children) == 2
    assert "PB001" in _codes("probabilitytree", "")
    assert "PB002" in _codes("probabilitytree", "Rot")
    assert "PB003" in _codes("probabilitytree", "    Rot: 1")
    assert "PB004" in _codes("probabilitytree", "Rot: 2\nBlau: x")
    assert "PB005" in _codes("probabilitytree", "Rot: 1/3\nBlau: 1/3")
    assert not [c for c in _codes("probabilitytree", "Rot: 1/3\n    A: 50%\n    B: 0,5\nBlau: %{2/3}") if c.startswith("PB")]
    _gap_differs("probabilitytree", "Rot: %{1/3}\nBlau: 2/3")


def test_term_tree_computes_exactly_and_hides_by_option():
    """Ergebnis exakt, Rechenreihenfolge richtig, Lücken nach `gaps`."""
    terms, issues = parse_term("(3+4)*2\n1/3+2/3\n2^3^2\n3,5 · 2\n-3+1")
    assert not issues
    assert [evaluate(term.expression) for term in terms] == [14, 1, 512, 7, -2]
    html = render_diagram_block("termtree", {}, "(3+4)*2")
    assert ">14<" in html.replace("<span>", "").replace("</span>", "")
    assert ">7<" in html.replace("<span>", "").replace("</span>", "")
    for gaps in ("results", "leaves", "all"):
        _gap_differs("termtree", "(3+4)*2", {"gaps": gaps})
    worksheet = render_diagram_block("termtree", {"gaps": "results"}, "(3+4)*2")
    assert worksheet.count("diagram-hidden") == 2


def test_term_tree_validator_codes():
    """Syntaxfehler, Division durch 0, Variablen."""
    assert "TT001" in _codes("termtree", "")
    assert "TT002" in _codes("termtree", "(3+")
    assert "TT003" in _codes("termtree", "1/(2-2)")
    assert "TT004" in _codes("termtree", "a+1")
    assert render_diagram_block("termtree", {}, "a+1")
    assert render_diagram_block("termtree", {}, "1/(2-2)")


def test_timeline_reads_times_and_warns_about_order():
    """Jahr, v. Chr., Datum; unsortierte Zeilen fallen auf; beide Maßstäbe rendern."""
    assert time_value("44 v. Chr.") == -44
    assert time_value("-44") == -44
    assert 1789 < time_value("14.07.1789") < 1790
    events, issues = parse_timeline("44 v. Chr.: Caesar\n1789: Revolution\n14.07.1789: Bastille")
    assert not issues and len(events) == 3
    assert "TL001" in _codes("timeline", "")
    assert "TL002" in _codes("timeline", "kein Datum")
    assert "TL003" in _codes("timeline", "1800: a\n1700: b")
    for scale in ("even", "proportional"):
        assert render_diagram_block("timeline", {"scale": scale}, "1000: a\n1001: b\n2000: c")
    _gap_differs("timeline", "1789: a\n% 1848: b")


@pytest.mark.parametrize(
    ("kind", "content"),
    [
        ("bar", "Äpfel: 12\nBirnen: 7\n% Kirschen: 3"),
        ("pie", "Äpfel: 1\nBirnen: 1\n% Kirschen: 2"),
        ("box", "8a: 3, 5, 7, 9, 12\n% 8b: 1, 2, 3, 4, 5"),
        ("histogram", "0-10: 4\n10-20: 9\n% 20-30: 2"),
        ("scatter", "1,5; 3\n2; 4\n% 3; 1"),
    ],
)
def test_chart_renders_all_types_and_line_gaps(kind, content):
    """Alle Darstellungen rendern; `%` macht aus einem Wert eine Lücke."""
    _gap_differs("chart", content, {"type": kind})
    assert not [c for c in _codes("chart", content, f"type={kind}") if c.startswith("CH")]


def test_chart_gap_values_hides_only_numbers():
    """`gaps=values` lässt die Balken stehen und blendet die Zahlen aus."""
    worksheet = render_diagram_block("chart", {"type": "bar", "gaps": "values"}, "A: 3\nB: 4")
    assert worksheet.count("diagram-bar") == 2
    assert worksheet.count("diagram-hidden") == 2


def test_chart_validator_checks_rows_against_type():
    """Zeilen werden gegen `type` geprüft; falsche Zeilen stürzen die Vorschau nicht ab."""
    assert "CH001" in _codes("chart", "")
    assert "CH002" in _codes("chart", "A: viel")
    assert "CH003" in _codes("chart", "A: 1, 2", "type=bar")
    assert "CH003" in _codes("chart", "1; 2; 3", "type=scatter")
    assert "CH004" in _codes("chart", "A: -1", "type=bar")
    assert "CH004" in _codes("chart", "A: 0", "type=pie")
    assert "CH005" in _codes("chart", "A: 1", "type=histogram")
    assert "CH006" in _codes("chart", "0-10: 1\n20-30: 2", "type=histogram")
    for kind in ("bar", "pie", "box", "histogram", "scatter"):
        assert isinstance(render_diagram_block("chart", {"type": kind}, "A: -1\n1; 2; 3"), str)


def test_venn_regions_and_compare_variant():
    """Mengen aus den Zeilen, `rest` ist keine Menge, beide Varianten rendern mit Lücken."""
    regions, issues = parse_venn("A: 2, 4\nA B: 6\nB: 3\nrest: 9")
    assert not issues
    assert set_names(regions) == ["A", "B"]
    _gap_differs("venn", "A: 2\nA B: %{6}\nB: 3")
    _gap_differs("venn", "A: 2\nB: 3\nC: 4\nA B C: %{6}\nA B: 7\nA C: 8\nB C: 9\nrest: 1")
    _gap_differs("venn", "Hund: bellt\n% Hund Katze: Haustier\nKatze: miaut", {"variant": "compare"})


def test_venn_validator_codes():
    """Struktur und Konsistenz der Bereiche; im Vergleich dürfen Texte sich wiederholen."""
    assert "VN001" in _codes("venn", "")
    assert "VN002" in _codes("venn", "keine Menge")
    assert "VN003" in _codes("venn", "A: 1")
    assert "VN003" in _codes("venn", "A: 1\nB: 2\nC: 3\nD: 4")
    assert "VN004" in _codes("venn", "A: 1\nB A: 2\nA B: 3")
    assert "VN005" in _codes("venn", "A: 1\nB: 1")
    assert "VN005" not in _codes("venn", "A: gut\nB: gut", "variant=compare")


def test_arrow_diagram_parses_lone_elements_and_checks_functions():
    """`_` zeigt Elemente ohne Pfeil; `kind=function` prüft die Eindeutigkeit."""
    model, issues = parse_arrow("1 -> a\n2 -> a\n3 -> _\n_ -> b")
    assert not issues
    assert model.left == ["1", "2", "3"] and model.right == ["a", "b"]
    assert len(model.links) == 2
    assert "AR001" in _codes("arrowdiagram", "")
    assert "AR002" in _codes("arrowdiagram", "1 2")
    assert "AR003" in _codes("arrowdiagram", "1 -> a\n1 -> a")
    assert "AR004" in _codes("arrowdiagram", "1 -> a\n1 -> b", "kind=function")
    assert "AR004" in _codes("arrowdiagram", "1 -> _", "kind=function")
    assert "AR004" not in _codes("arrowdiagram", "1 -> a\n2 -> a", "kind=function")
    _gap_differs("arrowdiagram", "1 -> a\n% 2 -> a")


def test_fractions_shapes_wholes_and_gaps():
    """Kreis und Balken, unechter Bruch, leer zum Ausmalen, Lücke."""
    assert render_diagram_block("fractions", {}, "3/4").count("diagram-fill") == 3
    assert render_diagram_block("fractions", {"shape": "bar"}, "3/4").count("diagram-fill") == 3
    assert render_diagram_block("fractions", {}, "5/4").count("diagram-fill") == 5
    assert render_diagram_block("fractions", {}, "1/1").count("diagram-fill") == 1
    assert render_diagram_block("fractions", {"filled": "false"}, "3/4").count("diagram-fill") == 0
    assert render_diagram_block("fractions", {}, "0/4").count("diagram-fill") == 0
    _gap_differs("fractions", "% 3/4")
    assert "FR001" in _codes("fractions", "")
    assert "FR002" in _codes("fractions", "drei Viertel")
    assert "FR003" in _codes("fractions", "1/0")
    assert "FR003" in _codes("fractions", "1/100")


def test_memory_diagram_parses_and_checks_references():
    """Alle Objektarten; Referenzziele und Namen werden geprüft."""
    content = "reihung r: 3, 5, 7\nvariable x: 5\nreferenz p -> r\nreferenz q -> null\nstapel s: 1, 2\nschlange w: 1, 2"
    model, issues = parse_memory(content)
    assert not issues and len(model.order) == 6
    assert not [c for c in _codes("memorydiagram", content) if c.startswith("MM")]
    assert render_diagram_block("memorydiagram", {}, content)
    _gap_differs("memorydiagram", "reihung r: 3, %{5}\n% variable x: 5")
    assert "MM001" in _codes("memorydiagram", "")
    assert "MM002" in _codes("memorydiagram", "kiste k: 1")
    assert "MM003" in _codes("memorydiagram", "referenz p -> fehlt")
    assert "MM004" in _codes("memorydiagram", "variable x: 1\nvariable x: 2")
    assert "MM005" in _codes("memorydiagram", "variable x: 1, 2")


def test_venn_regions_stay_inside_their_circles():
    """Die Bereichsmitten liegen in genau den Kreisen, zu denen sie gehören."""
    from math import hypot

    from app.core.diagram_venn import _centers, _region_spot

    radius, distance = 86.0, 56.0
    names = ["A", "B", "C"]
    centers = _centers(3, distance, radius)
    for sets in (("A",), ("B",), ("C",), ("A", "B"), ("A", "C"), ("B", "C"), ("A", "B", "C")):
        x, y = _region_spot(sets, names, centers)
        for name, center in zip(names, centers):
            assert (hypot(x - center[0], y - center[1]) < radius) == (name in sets), (sets, name)
