"""`:::table`: Breiten mit Kopfspalte, AN020 und woertliche Zellanfaenge.

Frueher bekam die `row_headers`-Spalte bei gesetztem `widths=` keine Breite und wurde
auf Wortbreite zusammengedrueckt; ueberzaehlige Werte fielen still weg; und "2. Frage"
in einer Zelle wurde zu einer ab 1 nummerierten Liste ("1. Frage").
"""

from __future__ import annotations

import pytest

from app.core.answer_table_layout import resolve_table_column_widths, widths_count_mismatch
from app.core.blatt_kern_answer_table import _render_table_answer
from app.core.blatt_validator import inspect_markdown_text

CELLS = 'cells:\n  - ["2. Wie entsteht es?", ""]\n  - ["2025. Jahr", ""]\n'


def test_row_header_gets_mean_weight_with_data_widths():
    """`cols` Gewichte + Kopfspalte: Kopfspalte erhaelt das mittlere Gewicht."""
    header, data = resolve_table_column_widths("1 3", 2, True)
    assert header == "33.3333%"
    assert data == ["16.6667%", "50.0000%"]


def test_extra_width_value_is_used_for_row_header():
    """`cols + 1` Werte mit Kopfspalte: der erste gilt fuer die Kopfspalte."""
    header, data = resolve_table_column_widths("2 6 2", 2, True)
    assert header == "20.0000%"
    assert data == ["60.0000%", "20.0000%"]


def test_without_row_header_widths_are_unchanged():
    """Ohne Kopfspalte bleibt das bisherige Verhalten."""
    assert resolve_table_column_widths("1 3", 2, False) == (None, ["25.0000%", "75.0000%"])


def test_explicit_lengths_leave_row_header_automatic():
    """Feste CSS-Laengen: kein erfundenes Gewicht fuer die Kopfspalte."""
    assert resolve_table_column_widths("3cm 5cm", 2, True) == (None, ["3cm", "5cm"])


@pytest.mark.parametrize(
    "widths, has_header, expected",
    [("1 2", False, None), ("1 2 3", False, (3, (2,))), ("1 2 3", True, None), ("1", True, (1, (2, 3)))],
)
def test_widths_count_mismatch(widths, has_header, expected):
    """Erlaubt: `cols`, mit Kopfspalte auch `cols + 1`."""
    assert widths_count_mismatch(widths, 2, has_header) == expected


def test_rendered_header_column_has_width_and_cells_stay_literal():
    """Kopfspalte bekommt `<col style=width>`, Zellen behalten "2." bzw. "2025."."""
    html = _render_table_answer({"cols": "2", "row_headers": "A|B", "widths": "1 3"}, CELLS, False)
    assert "<col style='width:33.3333%'>" in html
    assert "2. Wie entsteht es?" in html and "2025. Jahr" in html
    assert "<ol>" not in html


def test_validator_reports_an020_for_wrong_widths_count():
    """AN020 bei falscher Anzahl, nicht bei `cols + 1` mit Kopfspalte."""
    wrong = ':::table cols=2 widths="1 2 3"\n' + CELLS + ":::\n"
    right = ':::table cols=2 row_headers="A|B" widths="1 2 3"\n' + CELLS + ":::\n"
    assert "AN020" in [d.code for d in inspect_markdown_text(wrong).diagnostics]
    assert "AN020" not in [d.code for d in inspect_markdown_text(right).diagnostics]
