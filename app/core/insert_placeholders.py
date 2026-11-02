"""Platzhalter in Einfügetexten: wo der Cursor nach dem Einfügen landet.

Die eine Konvention für alle Einfügetexte des Editors: Block-Vorlagen
(`block_insert_snippets.py`, Diagramm-Snippets in `diagram_block_catalog.py`)
und Vorschläge der Autovervollständigung. Vorher markierten die Vorlagen den
Cursor mit `\\x01`, die Vervollständigung mit `[[CURSOR]]`/`[[n:…]]`, und
jeder Verbraucher (Editor, Doku-Generator, Tests) entfernte seinen Marker
selbst.

Reiner Core ohne Tk, damit der Doku-Generator dieselbe Auflösung nutzt.
`[[` kommt in der Dokumentsyntax nicht vor, die Platzhalter kollidieren also
mit keinem Inhalt.
"""

from __future__ import annotations

import re

CURSOR_PLACEHOLDER = "[[CURSOR]]"
"""Hier steht der Cursor nach dem Einfügen."""

_NUMBERED_PLACEHOLDER = re.compile(r"\[\[(\d+):([^\]]*)\]\]")
"""`[[n:Text]]`: Text wird eingefügt; der Cursor landet am Anfang des niedrigsten `n`."""


def resolve_insert_placeholders(text: str) -> tuple[str, int]:
    """Entfernt die Platzhalter und liefert den Einfügetext samt Cursorposition.

    Regeln, in dieser Reihenfolge:
    1. Gibt es nummerierte Platzhalter `[[n:Text]]`, bleibt jeweils `Text`
       stehen, und der Cursor steht am Anfang des Platzhalters mit dem
       kleinsten `n` (bei Gleichstand der vorderste).
    2. Sonst steht der Cursor dort, wo `[[CURSOR]]` stand (nur das erste
       Vorkommen zählt und wird entfernt).
    3. Sonst steht er am Ende.

    Returns:
        `(Text ohne Platzhalter, Cursor-Offset in diesem Text)`.
    """
    parts: list[str] = []
    occurrences: list[tuple[int, int]] = []
    length = 0
    scan = 0
    for match in _NUMBERED_PLACEHOLDER.finditer(text):
        parts.append(text[scan:match.start()])
        length += match.start() - scan
        occurrences.append((int(match.group(1)), length))
        parts.append(match.group(2))
        length += len(match.group(2))
        scan = match.end()
    parts.append(text[scan:])
    resolved = "".join(parts)

    if occurrences:
        return resolved, min(occurrences)[1]
    marker = resolved.find(CURSOR_PLACEHOLDER)
    if marker >= 0:
        return resolved.replace(CURSOR_PLACEHOLDER, "", 1), marker
    return resolved, len(resolved)


def strip_insert_placeholders(text: str) -> str:
    """Der Einfügetext ohne Platzhalter (für Doku und Prüfungen, die den Cursor nicht brauchen)."""
    return resolve_insert_placeholders(text)[0]
