"""Redaktionelle Gruppierung der Blocktypen für das Editor-Menü "Einfügen".

**Wichtig:** Diese Gruppierung ist eine veränderbare redaktionelle
Präsentations-/Navigationsstruktur des Einfügemenüs -- keine kanonische Taxonomie
der Blocktypen und keine technische Invariante. Sie darf jederzeit umsortiert,
umbenannt oder anders geschnitten werden, ohne dass dafür Tests angepasst werden
müssen (siehe `tests/test_block_insert_menu.py`: dort wird nur geprüft, dass jeder
in `BLOCK_INSERT_SNIPPETS` vorgesehene Blocktyp genau einmal vorkommt -- nicht eine
bestimmte Anzahl oder Namen von Familien). Sie darf insbesondere nicht als Grundlage
für Validierungs- oder sonstige Domänenlogik verwendet werden -- dafür ist
`KNOWN_BLOCK_TYPES`/`BLOCK_OPTION_SPECS` in `blatt_validator_constants.py` die
normative Quelle.

`BLOCK_INSERT_FAMILIES` gruppiert echte `:::`-Blocktypen in benannte Untermenüs;
`BLOCK_INSERT_STANDALONE` listet Blocktypen, die strukturell zu einzigartig für eine
Familie sind (aktuell nur `columns`: ein Spalten-Layout-Container ohne inhaltliche
Verwandtschaft zu anderen Blöcken) und daher direkt auf oberster Ebene des Menüs
liegen, neben den Familien-Untermenüs.

Beide Strukturen referenzieren nur Blocktyp-Schlüssel -- die eigentlichen
Einfüge-Vorlagen bleiben einzig in `BLOCK_INSERT_SNIPPETS`
(`block_insert_snippets.py`) definiert, damit es nur eine Quelle für den
tatsächlichen Snippet-Text gibt.

`Bild` (reines Markdown-Bildsyntax, kein `:::`-Block) taucht hier bewusst in keiner
der beiden Strukturen auf: es ist keine `:::`-Blockeinfügung, sondern eine
eigenständige UI-Aktion des Einfügemenüs, und wird deshalb direkt im UI-Mixin
(`app/ui/blatt_ui_block_insert_menu.py`) als eigene Konstante gepflegt statt hier
gegen `BLOCK_INSERT_SNIPPETS` geprüft zu werden.
"""

from __future__ import annotations

BLOCK_INSERT_FAMILIES: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Boxen/Hinweise",
        [
            ("Material", "material"),
            ("Infobox / Hinweis (info)", "info"),
            ("Musterlösung (solution)", "solution"),
            ("Hilfe-Karte (help)", "help"),
        ],
    ),
    (
        "Aufgaben",
        [
            ("Aufgabe (task)", "task"),
            ("Teilaufgabe (subtask)", "subtask"),
        ],
    ),
    (
        "Freies Antwortfeld",
        [
            ("Linienfeld (lines)", "lines"),
            ("Gitterpapier (grid)", "grid"),
            ("Punktpapier (dots)", "dots"),
            ("Freier Platz (space)", "space"),
        ],
    ),
    (
        "Textbasierte Übungen",
        [
            ("Auswahlaufgabe (mc)", "mc"),
            ("Lückentext (cloze)", "cloze"),
            ("Reihenfolge (ordering)", "ordering"),
            ("Wortsuchrätsel (wordsearch)", "wordsearch"),
        ],
    ),
    (
        "Grafische/räumliche Übungen",
        [
            ("Tabelle (table)", "table"),
            ("Koordinatensystem (geometry)", "geometry"),
            ("Zahlengerade (numberline)", "numberline"),
            ("Ankreuztabelle (checkgrid)", "checkgrid"),
            ("Kreuzworträtsel (crossword)", "crossword"),
            ("Zuordnung (matching)", "matching"),
        ],
    ),
    (
        "Offen/Reflexion",
        [
            ("Mindmap", "mindmap"),
            ("Selbsteinschätzung (selfcheck)", "selfcheck"),
            ("Schreibrahmen (writebox)", "writebox"),
        ],
    ),
]

BLOCK_INSERT_STANDALONE: list[tuple[str, str]] = [
    ("Spalten-Layout (columns)", "columns"),
    ("QR-Code", "qrcode"),
]
