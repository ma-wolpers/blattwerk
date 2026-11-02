"""Einzige Quelle für die Block-Einfüge-Vorlagen des Editor-Menüs "Einfügen".

`BLOCK_INSERT_SNIPPETS` enthält für jeden Blocktyp mit einem Eintrag im Menü
"Einfügen" (Alt+I; Menüstruktur in
`app/core/block_insert_menu_families.py`, Anbindung in
`app/ui/blatt_ui_block_insert_menu.py`) exakt den Text, der beim Einfügen per
Klick in den Editor geschrieben wird -- inklusive Cursor-Platzhalter `[[CURSOR]]` (`insert_placeholders.py`)
(derselbe Vertrag wie bisher im Editor).

**Wichtig:** Ein Snippet ist ein *minimales, bequemes Beispiel* für die
Verwendung eines Blocktyps -- nicht die vollständige Grammatikspezifikation
(die liefern `BLOCK_OPTION_SPECS`/die Options-Tabelle in der generierten
Anleitung). Konsumenten: der Editor (Menü "Einfügen") und der
Doku-Generator (`tools/docs/generate_authoring_guides.py`, als belegtes
"Beispiel" pro Block). Reine Datendatei, keine Logik -- bewusst in
`app/core`, damit die Doku-Pipeline sie ohne GUI-Abhängigkeit (`bw_gui`)
importieren kann.

Nicht jeder Blocktyp aus `KNOWN_BLOCK_TYPES` hat hier einen Eintrag (z. B.
`nextcol`/`endcolumns`/die Control-Marker-Pseudoblöcke) -- fehlende
Einträge sind kein Fehler, `markdown_conventions.py` re-verpackt sie als
`None`.
"""

from __future__ import annotations

from .diagram_block_catalog import DIAGRAM_BLOCKS

BLOCK_INSERT_SNIPPETS: dict[str, str] = {
    "mc": (
        ":::mc inline=true\n"
        "[[CURSOR]]Frage oder Einleitung…\n"
        "- [x] Richtige Antwort\n"
        "- [ ] Falsche Antwort A\n"
        "- [ ] Falsche Antwort B\n"
        ":::\n"
    ),
    "table": (
        ':::table rows=3 cols=3 column_headers="A|B|C"\n'
        "cells:\n"
        '[[CURSOR]]  - ["", "", ""]\n'
        '  - ["", "", ""]\n'
        '  - ["", "", ""]\n'
        ":::\n"
    ),
    "columns": (
        ':::columns cols=2 widths="1 1" :::\n'
        "[[CURSOR]]\n"
        ":::nextcol :::\n"
        "\n"
        ":::endcolumns :::\n"
    ),
    "dots": (
        ":::dots height=4cm\n"
        "[[CURSOR]]\n"
        ":::\n"
    ),
    "geometry": (
        ':::geometry scale=0.5cm width=20 height=10 axis=true origin="10,5"\n'
        "points:\n"
        '[[CURSOR]]  - {x: 0, y: 0, label: "A", show: "&"}\n'
        ":::\n"
    ),
    "info": (
        ":::info type=note\n"
        "[[CURSOR]]Hinweis hier…\n"
        ":::\n"
    ),
    "grid": (
        ":::grid scale=0.5cm\n"
        "[[CURSOR]]\n"
        ":::\n"
    ),
    "help": (
        ':::help title="Hilfe" level=1\n'
        "[[CURSOR]]Hilfetext hier…\n"
        ":::\n"
    ),
    "cloze": (
        ":::cloze gap=fixed words=below\n"
        "[[CURSOR]]Text mit {{Lücke}} hier.\n"
        ":::\n"
    ),
    "lines": (
        ":::lines rows=3\n"
        "[[CURSOR]]\n"
        ":::\n"
    ),
    "material": (
        ':::material title="Titel"\n'
        "[[CURSOR]]Inhalt hier…\n"
        ":::\n"
    ),
    "numberline": (
        ":::numberline min=0 max=10 tick_step=1 major_every=5 height=2cm\n"
        "labels:\n"
        '[[CURSOR]]  - {value: 0, show: "&"}\n'
        '  - {value: 10, show: "&"}\n'
        "answers:\n"
        "  - {value: 5}\n"
        ":::\n"
    ),
    "space": (
        ":::space height=3cm\n"
        "[[CURSOR]]\n"
        ":::\n"
    ),
    "qrcode": (
        ":::qrcode url=https://example.org w=3cm h=3cm maxw=45% :::\n"
        "[[CURSOR]]"
    ),
    "evaluation": (
        ":::evaluation level=task:::\n"
        "[[CURSOR]]"
    ),
    "operators": (
        ":::operators:::\n"
        "[[CURSOR]]"
    ),
    "solution": (
        ":::solution\n"
        "[[CURSOR]]Musterlösung hier…\n"
        ":::\n"
    ),
    "subtask": (
        ":::subtask work=single\n"
        "[[CURSOR]]Teilaufgabe hier…\n"
        ":::\n"
    ),
    "task": (
        ":::task work=single action=write\n"
        "[[CURSOR]]Aufgabentext hier…\n"
        ":::\n"
    ),
    "wordsearch": (
        ":::wordsearch min_size=10x12 diagonal=false\n"
        "[[CURSOR]]- Wort1\n"
        "- Wort2\n"
        "- Wort3\n"
        ":::\n"
    ),
    "ordering": (
        ":::ordering numbering=numeric\n"
        "[[CURSOR]]- Zuerst das Ei kaufen\n"
        "- Dann den Teig anrühren\n"
        "- Dann backen\n"
        "- Zum Schluss servieren\n"
        ":::\n"
    ),
    "checkgrid": (
        ":::checkgrid\n"
        "columns:\n"
        '[[CURSOR]]  - "richtig"\n'
        '  - "falsch"\n'
        "rows:\n"
        '  - text: "Die Erde ist eine Scheibe."\n'
        "    correct: 2\n"
        '  - text: "Wasser besteht aus H2O."\n'
        "    correct: 1\n"
        ":::\n"
    ),
    "crossword": (
        ":::crossword maxw=15 maxh=15\n"
        "words:\n"
        '[[CURSOR]]  - word: "SONNE"\n'
        '    clue: "Scheint tagsueber am Himmel"\n'
        '  - word: "MOND"\n'
        '    clue: "Scheint nachts am Himmel"\n'
        '  - word: "STERN"\n'
        '    clue: "Funkelt nachts am Himmel"\n'
        ":::\n"
    ),
    "mindmap": (
        ":::mindmap branches=6 shape=oval\n"
        "[[CURSOR]]Thema\n"
        ":::\n"
    ),
    "selfcheck": (
        ":::selfcheck scale=smiley steps=3\n"
        "[[CURSOR]]- Ich kann das Thema erklären.\n"
        "- Ich kann Aufgaben dazu lösen.\n"
        ":::\n"
    ),
    "writebox": (
        ":::writebox style=frame lines=5\n"
        "[[CURSOR]]Schreibimpuls hier…\n"
        ":::\n"
    ),
    "matching": (
        ":::matching layout=horizontal height_mode=uniform lane_align=center show_guides=false\n"
        "left:\n"
        '[[CURSOR]]  - "Begriff A"\n'
        '  - "Begriff B"\n'
        "right:\n"
        '  - "Erklärung A"\n'
        '  - "Erklärung B"\n'
        "matches:\n"
        '  - "1-1"\n'
        '  - "2-2"\n'
        ":::\n"
    ),
}

BLOCK_INSERT_SNIPPETS.update({spec.name: spec.snippet for spec in DIAGRAM_BLOCKS})

IMAGE_INSERT_SNIPPET = '![Bildbeschreibung](bild.png "w=80% align=center")\n[[CURSOR]]'
"""Vorlage für den Eintrag „Bild“ im Menü „Einfügen“. Kein `:::`-Block, darum nicht in
`BLOCK_INSERT_SNIPPETS` (das nur echte Blocktypen kennt), aber dieselbe Vorlagenquelle."""
