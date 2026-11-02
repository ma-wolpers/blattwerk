"""Redaktionelle Gruppierung und Kennbuchstaben der Blocktypen für das Editor-Menü "Einfügen".

**Wichtig:** Diese Gruppierung ist eine veränderbare redaktionelle
Präsentations-/Navigationsstruktur des Einfügemenüs -- keine kanonische Taxonomie
der Blocktypen und keine technische Invariante. Sie darf jederzeit umsortiert,
umbenannt oder anders geschnitten werden, ohne dass dafür Tests angepasst werden
müssen (siehe `tests/test_block_insert_menu.py`: dort wird nur geprüft, dass jeder
in `BLOCK_INSERT_SNIPPETS` vorgesehene Blocktyp genau einmal vorkommt und die
Kennbuchstaben eindeutig sind). Sie darf insbesondere nicht als Grundlage für
Validierungs- oder sonstige Domänenlogik verwendet werden -- dafür ist
`KNOWN_BLOCK_TYPES`/`BLOCK_OPTION_SPECS` in `blatt_validator_constants.py` die
normative Quelle.

Jeder Eintrag ist `(Titel, Blocktyp, Kennbuchstabe)`. Die Menübeschriftung
`"Titel (blocktyp)"` baut `insert_menu_label` an einer Stelle. Der
Kennbuchstabe (oder `None`) löst den Eintrag im offenen Menü aus (Alt+I, dann
Buchstabe; `MenuItem.mnemonic` in bw-gui). Die Buchstaben folgen der Tabelle
des früheren Strg+B-Popups (42c7368).
GRENZE: `evaluation`, `operators` und die Diagramme haben keinen Buchstaben, J ist frei.

`BLOCK_INSERT_FAMILIES` gruppiert echte `:::`-Blocktypen in benannte Untermenüs;
`BLOCK_INSERT_STANDALONE` listet Blocktypen, die strukturell zu einzigartig für eine
Familie sind, und liegt direkt auf oberster Ebene neben den Familien-Untermenüs.
`IMAGE_INSERT_ENTRY` ist kein `:::`-Block, sondern Markdown-Bildsyntax
(`IMAGE_INSERT_SNIPPET`); er steht hier nur, damit Beschriftung und Buchstabe
dieselbe Quelle haben.

Alle Strukturen referenzieren nur Blocktyp-Schlüssel -- die eigentlichen
Einfüge-Vorlagen bleiben einzig in `block_insert_snippets.py`.
"""

from __future__ import annotations

from .diagram_block_catalog import DIAGRAM_BLOCKS

INSERT_MENU_LABEL = "Einfügen"
"""Titel des Menüs in der Menüleiste (auch in der generierten Anleitung genannt)."""

INSERT_MENU_ALT = "i"
"""Alt-Buchstabe, der das Menü öffnet (`MenuDefinition.alt`)."""

InsertEntry = tuple[str, str, "str | None"]
"""`(Titel, Blocktyp, Kennbuchstabe)`."""

BLOCK_INSERT_FAMILIES: list[tuple[str, list[InsertEntry]]] = [
    (
        "Boxen/Hinweise",
        [
            ("Material", "material", "M"),
            ("Infobox / Hinweis", "info", "F"),
            ("Musterlösung", "solution", "R"),
            ("Hilfe-Karte", "help", "H"),
        ],
    ),
    (
        "Aufgaben",
        [
            ("Aufgabe", "task", "T"),
            ("Teilaufgabe", "subtask", "S"),
            ("Bewertungstabelle", "evaluation", None),
            ("Operatorentabelle", "operators", None),
        ],
    ),
    (
        "Freies Antwortfeld",
        [
            ("Linienfeld", "lines", "L"),
            ("Gitterpapier", "grid", "G"),
            ("Punktpapier", "dots", "D"),
            ("Freier Platz", "space", "P"),
        ],
    ),
    (
        "Textbasierte Übungen",
        [
            ("Auswahlaufgabe", "mc", "A"),
            ("Lückentext", "cloze", "K"),
            ("Reihenfolge", "ordering", "O"),
            ("Wortsuchrätsel", "wordsearch", "W"),
        ],
    ),
    (
        "Grafische/räumliche Übungen",
        [
            ("Tabelle", "table", "B"),
            ("Koordinatensystem", "geometry", "E"),
            ("Zahlengerade", "numberline", "N"),
            ("Ankreuztabelle", "checkgrid", "V"),
            ("Kreuzworträtsel", "crossword", "X"),
            ("Zuordnung", "matching", "Z"),
        ],
    ),
    ("Diagramme", [(spec.title, spec.name, None) for spec in DIAGRAM_BLOCKS]),
    (
        "Offen/Reflexion",
        [
            ("Mindmap", "mindmap", "U"),
            ("Selbsteinschätzung", "selfcheck", "Ü"),
            ("Schreibrahmen", "writebox", "Y"),
        ],
    ),
]

BLOCK_INSERT_STANDALONE: list[InsertEntry] = [
    ("Spalten-Layout", "columns", "C"),
    ("QR-Code", "qrcode", "Q"),
]

IMAGE_INSERT_ENTRY: InsertEntry = ("Bild", "image", "I")


def insert_menu_label(title: str, key: str) -> str:
    """Menübeschriftung eines Eintrags: `"Titel (blocktyp)"`, z. B. `"Aufgabe (task)"`."""
    return f"{title} ({key})"


def iter_insert_entries():
    """Alle Einträge des Menüs in Menüreihenfolge (Familien, Einzelgänger, Bild)."""
    for _family, entries in BLOCK_INSERT_FAMILIES:
        yield from entries
    yield from BLOCK_INSERT_STANDALONE
    yield IMAGE_INSERT_ENTRY


def mnemonic_for(key: str) -> str | None:
    """Kennbuchstabe eines Blocktyps (oder `"image"`) im Menü, `None` ohne Buchstabe."""
    return next((letter for _title, entry_key, letter in iter_insert_entries() if entry_key == key), None)
