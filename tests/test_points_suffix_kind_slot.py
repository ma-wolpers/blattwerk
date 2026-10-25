"""`find_kind_slot`: Typ-Stelle eines Punkt-Suffixes für die Editor-Completion.

Die Funktion nutzt denselben Grammatik-Kopf wie `parse_points_suffix`
(`_POINTS_HEAD`), daher treffen genau die Klammern, die nach dem `P` als
gültiges Suffix weitergehen könnten.
"""

from __future__ import annotations

import pytest

from app.core.points_suffix import find_kind_slot


@pytest.mark.parametrize(
    ("left_text", "expected_prefix"),
    [
        ("1. Ansatz notiert (0,5P ", ""),
        ("1. Ansatz notiert (0,5P  ", ""),
        ("1. Rechnung (1aP An", "An"),
        ("1. Rechnung (1 b P Anw", "Anw"),
        ("2. Begründung (1/2P ", ""),
        ("3. Je Fehler (−1P Bg", "Bg"),
        ("3. Je Fehler (-0.5P fo", "fo"),
        ("4. Einheit (1P Einheit/Grö", "Einheit/Grö"),
    ],
)
def test_finds_slot_and_typed_prefix(left_text, expected_prefix):
    slot = find_kind_slot(left_text)

    assert slot is not None
    start, prefix = slot
    assert prefix == expected_prefix
    assert left_text[start:] == expected_prefix


@pytest.mark.parametrize(
    "left_text",
    [
        "1. Ansatz (0,5P",  # noch kein Leerzeichen nach dem P
        "1. Ansatz (3 Punkte ",  # kein Punkt-Kandidat
        "1. Ansatz (0,5abP ",  # ungültige Grammatik (SL018)
        "1. Abzug (−1/2P ",  # Abzug mit Höchstwert ist ungültig
        "1. Ansatz (0,5P An ",  # Typ schon fertig getippt
        "1. Ansatz (0,5P An) ",  # Klammer schon geschlossen
        "1. Ansatz 0,5P ",  # keine Klammer
        "",
    ],
)
def test_no_slot(left_text):
    assert find_kind_slot(left_text) is None
