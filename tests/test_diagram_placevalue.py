"""Tests für die Stellenwerttafel `:::placevalue` (`diagram_placevalue`, `diagram_placevalue_model`)."""

from __future__ import annotations

import re
from fractions import Fraction

import pytest

from app.core.diagram_block_dispatch import render_diagram_block, validate_diagram_blocks
from app.core.diagram_placevalue_model import fraction_tex, parse, resolve_columns, row_value
from app.core.document_language import LANGUAGE_OPTION_KEY


def _codes(options, content) -> list[str]:
    """Diagnosecodes eines einzelnen Blocks."""
    return [diag.code for diag in validate_diagram_blocks([("placevalue", options, content)])]


def _rows(html: str) -> list[list[str]]:
    """Zelltexte je Körperzeile (Tags entfernt, versteckte Lösungen als `?`)."""
    body = html.split("<tbody>")[1]
    rows = []
    for row in re.findall(r"<tr>(.*?)</tr>", body):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row)
        rows.append([re.sub(r"<[^>]+>", "", re.sub(r"<span class='diagram-hidden'>.*?</span>", "?", cell)) for cell in cells])
    return rows


def test_number_digits_land_in_their_places():
    """`52,34` verteilt sich auf Z, E, z, h."""
    table, issues = parse("52,34\n2.8")
    assert not issues
    assert [(d.exponent, d.numeral) for d in table.rows[0].digits] == [(1, "5"), (0, "2"), (-1, "3"), (-2, "4")]
    assert [(d.exponent, d.numeral) for d in table.rows[1].digits] == [(0, "2"), (-1, "8")]


def test_columns_auto_range_covers_all_numbers_and_at_least_ones():
    """Ohne `from`/`to`: kleinster Bereich mit allen Ziffern, mindestens E."""
    table, _ = parse("52,34\n0,001")
    assert resolve_columns({}, table).exponents == (1, 0, -1, -2, -3)
    assert resolve_columns({}, parse("")[0]).exponents == (0,)


def test_from_to_fix_the_range_and_report_problems():
    """Feste Grenzen gelten; unbekannte Kürzel, falsche Reihenfolge und abgeschnittene Ziffern melden sich."""
    table, _ = parse("152,3")
    columns = resolve_columns({"from": "Z", "to": "t"}, table)
    assert columns.exponents == (1, 0, -1, -2, -3)
    assert [code for code, _ in columns.problems] == ["PV005"]
    assert [code for code, _ in resolve_columns({"from": "X"}, table).problems][0] == "PV004"
    assert "PV004" in [code for code, _ in resolve_columns({"from": "h", "to": "Z"}, table).problems]


def test_case_matters_for_column_names():
    """`Z` (Zehner) und `z` (Zehntel) sind verschiedene Spalten."""
    columns = resolve_columns({"from": "Z", "to": "z"}, parse("")[0])
    assert columns.exponents == (1, 0, -1)


def test_invalid_line_is_reported():
    """Eine Zeile, die keine Zahl ist, ergibt `PV002`."""
    assert "PV002" in _codes({}, "zwei Komma acht")


def test_cell_rows_need_bounds_and_matching_count():
    """Zellenzeilen brauchen `from`/`to` (`PV006`) und je Spalte eine Zelle (`PV003`)."""
    assert "PV006" in _codes({}, "| 1 | 8 |")
    assert "PV003" in _codes({"from": "Z", "to": "h"}, "| 1 | 8 | 13 |")
    assert not _codes({"from": "Z", "to": "h"}, "| 1 | 8 | 13 | |")


def test_empty_template_is_not_empty_but_bare_block_is():
    """`rows=` ohne Inhalt ist eine gültige Vorlage, ein ganz leerer Block meldet `PV001`."""
    assert _codes({}, "") == ["PV001"]
    assert _codes({"from": "H", "to": "t", "rows": "3"}, "") == []
    html = render_diagram_block("placevalue", {"from": "H", "to": "t", "rows": "3"}, "")
    assert len(_rows(html)) == 3
    assert render_diagram_block("placevalue", {}, "") == ""


def test_invalid_rows_option_warns():
    """`rows` muss eine ganze Zahl sein (`PV007`)."""
    assert "PV007" in _codes({"rows": "drei"}, "2,8")


def test_row_values_and_fraction_tex():
    """Werte aus Zahl- und Zellenzeilen; Bruch gemischt oder unecht mit Zehnerpotenz-Nenner."""
    table, _ = parse("2,02\n0,234\n| 1 | 8 | 13 | |\n2,20")
    exponents = (1, 0, -1, -2)
    assert row_value(table.rows[0], exponents) == (Fraction(202, 100), 2)
    assert row_value(table.rows[2], exponents) == (Fraction(193, 10), 1)
    assert fraction_tex(Fraction(202, 100), 2, False) == "2\\frac{2}{100}"
    assert fraction_tex(Fraction(234, 1000), 3, False) == "\\frac{234}{1000}"
    assert fraction_tex(Fraction(202, 100), 2, True) == "\\frac{202}{100}"
    assert fraction_tex(Fraction(220, 100), 2, False) == "2\\frac{20}{100}"
    assert fraction_tex(Fraction(3), 0, False) == "3"


def test_gaps_are_hidden_in_worksheet_and_shown_in_solution():
    """`%{…}` und `%`-Zeilen sind im Arbeitsblatt offen, der Bruch einer Lückenzeile auch."""
    options = {"from": "Z", "to": "h", "fraction": "mixed"}
    content = "5%{2},3%{4}\n% 8,25\n2,02"
    worksheet = _rows(render_diagram_block("placevalue", options, content))
    assert worksheet[0] == ["5", "?,", "3", "?", "?"]
    assert worksheet[1] == ["", "?,", "?", "?", "?"]
    assert worksheet[2][:4] == ["", "2,", "0", "2"] and "frac{2}{100}" in worksheet[2][4]
    solution = render_diagram_block("placevalue", options, content, include_solutions=True)
    assert "diagram-hidden" not in solution
    assert "52\\frac{34}{100}" in solution


def test_comma_is_preprinted_unless_switched_off():
    """Komma in leeren Einerzellen standardmäßig, mit `comma=false` nur hinter sichtbaren Ziffern."""
    assert _rows(render_diagram_block("placevalue", {"from": "Z", "to": "h", "rows": "1"}, ""))[0][1] == ","
    assert _rows(render_diagram_block("placevalue", {"from": "Z", "to": "h", "rows": "1", "comma": "false"}, ""))[0][1] == ""
    assert _rows(render_diagram_block("placevalue", {"comma": "false"}, "2,8"))[0][0] == "2,"


def test_fraction_gap_hides_whole_fraction_column():
    """`fraction_gap=true` lässt den Bruch auch bei sichtbaren Ziffern offen."""
    rows = _rows(render_diagram_block("placevalue", {"fraction": "improper", "fraction_gap": "true"}, "0,234"))
    assert rows[0][-1] == "?"


def test_values_row_is_automatic_and_labels_are_optional():
    """Stellenwertzeile nur mit Nachkommastellen; Zeilenbeschriftung als Daten-Attribut."""
    assert "\\frac{1}{10}" in render_diagram_block("placevalue", {}, "2,8")
    assert "pv-value" not in render_diagram_block("placevalue", {}, "352")
    assert "pv-value" in render_diagram_block("placevalue", {"values": "true"}, "352")
    assert "data-label='a)'" in render_diagram_block("placevalue", {"labels": "letters"}, "2,8")
    assert "data-label='1)'" in render_diagram_block("placevalue", {"labels": "numbers"}, "2,8")
    assert "data-label" not in render_diagram_block("placevalue", {}, "2,8")


@pytest.mark.parametrize(("colors", "expected"), [("decimals", 1), ("all", 2), ("none", 0)])
def test_color_modes(colors, expected):
    """`decimals` tönt nur Nachkommaspalten, `all` auch Ganze, `none` nichts."""
    html = render_diagram_block("placevalue", {"colors": colors}, "2,8")
    toned = {cls for cls in re.findall(r"pv-col( pv-tone-\d)?", html) if cls}
    assert len(toned) == expected


def test_ones_column_has_thick_line_and_comma_in_header():
    """Einerspalte: Klasse `pv-ones` und Kopf `E,`."""
    html = render_diagram_block("placevalue", {}, "2,8")
    assert "pv-ones'>E,</th>" in html


def test_fraction_header_follows_document_language():
    """Nur der Kopf der Bruchspalte ist übersetzt."""
    html = render_diagram_block("placevalue", {"fraction": "mixed", LANGUAGE_OPTION_KEY: "pt-br"}, "2,8")
    assert "Fração" in html
    assert "Bruch" in render_diagram_block("placevalue", {"fraction": "mixed"}, "2,8")
