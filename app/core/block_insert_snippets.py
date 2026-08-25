"""Einzige Quelle für die Ctrl+B-Block-Einfüge-Vorlagen des Editors.

`BLOCK_INSERT_SNIPPETS` enthält für jeden Blocktyp mit einem Ctrl+B-
Menüeintrag (`app/ui/blatt_ui_editor.py`, `_EDITOR_BLOCK_MENU_ITEMS`) exakt
den Text, der beim Einfügen per Shortcut in den Editor geschrieben wird --
inklusive `\x01`-Cursor-Marker (derselbe Vertrag wie bisher im Editor).

**Wichtig:** Ein Snippet ist ein *minimales, bequemes Beispiel* für die
Verwendung eines Blocktyps -- nicht die vollständige Grammatikspezifikation
(die liefern `BLOCK_OPTION_SPECS`/die Options-Tabelle in der generierten
Anleitung). Konsumenten: der Editor (Ctrl+B-Menü) und der Doku-Generator
(`tools/docs/generate_authoring_guides.py`, als belegtes "Beispiel" pro
Block). Reine Datendatei, keine Logik -- bewusst in `app/core`, damit die
Doku-Pipeline sie ohne GUI-Abhängigkeit (`bw_gui`) importieren kann.

Nicht jeder Blocktyp aus `KNOWN_BLOCK_TYPES` hat hier einen Eintrag (z. B.
`nextcol`/`endcolumns`/`hilfe`/die Control-Marker-Pseudoblöcke) -- fehlende
Einträge sind kein Fehler, `markdown_conventions.py` re-verpackt sie als
`None`.
"""

from __future__ import annotations

BLOCK_INSERT_SNIPPETS: dict[str, str] = {
    "mc": (
        ":::mc inline=true\n"
        "\x01Frage oder Einleitung…\n"
        "- [x] Richtige Antwort\n"
        "- [ ] Falsche Antwort A\n"
        "- [ ] Falsche Antwort B\n"
        ":::\n"
    ),
    "table": (
        ':::table rows=3 cols=3 headers="A|B|C"\n'
        "cells:\n"
        '\x01  - ["", "", ""]\n'
        '  - ["", "", ""]\n'
        '  - ["", "", ""]\n'
        ":::\n"
    ),
    "columns": (
        ':::columns cols=2 widths="1 1" :::\n'
        "\x01\n"
        ":::nextcol :::\n"
        "\n"
        ":::endcolumns :::\n"
    ),
    "dots": (
        ":::dots height=4cm\n"
        "\x01\n"
        ":::\n"
    ),
    "geometry": (
        ':::geometry scale=0.5cm axis=true origin="10,10"\n'
        "points:\n"
        '\x01  - {x: 0, y: 0, label: "A", show: "&"}\n'
        ":::\n"
    ),
    "info": (
        ":::info type=tip\n"
        "\x01Hinweis hier…\n"
        ":::\n"
    ),
    "grid": (
        ":::grid scale=0.5cm\n"
        "\x01\n"
        ":::\n"
    ),
    "help": (
        ':::help title="Hilfe" level=1\n'
        "\x01Hilfetext hier…\n"
        ":::\n"
    ),
    "cloze": (
        ":::cloze gap=fixed words=below\n"
        "\x01Text mit {{Lücke}} hier.\n"
        ":::\n"
    ),
    "lines": (
        ":::lines rows=3\n"
        "\x01\n"
        ":::\n"
    ),
    "material": (
        ':::material title="Titel"\n'
        "\x01Inhalt hier…\n"
        ":::\n"
    ),
    "numberline": (
        ":::numberline min=0 max=10 tick_step=1 major_every=5 height=2cm\n"
        "labels:\n"
        '\x01  - {value: 0, show: "&"}\n'
        '  - {value: 10, show: "&"}\n'
        "answers:\n"
        "  - {value: 5}\n"
        ":::\n"
    ),
    "space": (
        ":::space height=3cm\n"
        "\x01\n"
        ":::\n"
    ),
    "qrcode": (
        ":::qrcode url=https://example.org w=3cm h=3cm maxw=45% :::\n"
        "\x01"
    ),
    "solution": (
        ":::solution\n"
        "\x01Musterlösung hier…\n"
        ":::\n"
    ),
    "subtask": (
        ":::subtask work=single\n"
        "\x01Teilaufgabe hier…\n"
        ":::\n"
    ),
    "task": (
        ":::task work=single action=write\n"
        "\x01Aufgabentext hier…\n"
        ":::\n"
    ),
    "wordsearch": (
        ":::wordsearch min_size=10x12 diagonal=false\n"
        "\x01- Wort1\n"
        "- Wort2\n"
        "- Wort3\n"
        ":::\n"
    ),
    "categorize": (
        ":::categorize\n"
        "categories:\n"
        '\x01  - "Tiere"\n'
        '  - "Pflanzen"\n'
        "items:\n"
        '  - word: "Hund"\n'
        "    category: 1\n"
        '  - word: "Rose"\n'
        "    category: 2\n"
        ":::\n"
    ),
    "ordering": (
        ":::ordering numbering=numeric\n"
        "\x01- Zuerst das Ei kaufen\n"
        "- Dann den Teig anrühren\n"
        "- Dann backen\n"
        "- Zum Schluss servieren\n"
        ":::\n"
    ),
    "checkgrid": (
        ":::checkgrid\n"
        "columns:\n"
        '\x01  - "richtig"\n'
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
        '\x01  - word: "Wort1"\n'
        '    clue: "Hinweis 1"\n'
        '  - word: "Wort2"\n'
        '    clue: "Hinweis 2"\n'
        '  - word: "Wort3"\n'
        '    clue: "Hinweis 3"\n'
        ":::\n"
    ),
    "mindmap": (
        ":::mindmap branches=6 shape=oval\n"
        "\x01Thema\n"
        ":::\n"
    ),
    "selfcheck": (
        ":::selfcheck scale=smiley steps=3\n"
        "\x01- Ich kann das Thema erklären.\n"
        "- Ich kann Aufgaben dazu lösen.\n"
        ":::\n"
    ),
    "writebox": (
        ":::writebox style=frame lines=5\n"
        "\x01Schreibimpuls hier…\n"
        ":::\n"
    ),
    "matching": (
        ":::matching layout=horizontal height_mode=uniform lane_align=center show_guides=false\n"
        "left:\n"
        '\x01  - "Begriff A"\n'
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
