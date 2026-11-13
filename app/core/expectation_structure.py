"""Struktur eines `:::expectation`-Blocks: einzige Zerlegung in einzelne Erwartungen.

Bewertung (`expectation_items`, Validator, Erwartungshorizont) und die
Erkennung veralteter Punkte in `:::solution` (SL024) lesen Erwartungen nur
über `classify_expectations` -- es gibt keine zweite Zerlegung.

Regeln (auf dem Rohtext, mit 0-basierten Zeilennummern):

1. **Geschützte Bereiche** in der Reihenfolge der Render-Pipeline und mit
   deren eigenen Mustern: Mathe (`find_math_span_ranges`), dann
   `%%`-Kommentare (`COMMENT_PATTERN`), dann Codezäune (`FENCE_PATTERN`).
   Text darin beendet nie eine Erwartung und beginnt nie eine Nummer.
2. **Ende einer Erwartung:** die erste Zeile, deren ungeschützter Text auf
   einen Punkt-Kandidaten endet (`points_suffix.has_points_candidate`,
   gültig oder unlesbar). Eine Erwartung darf über mehrere Zeilen gehen.
3. **Optionale Nummer:** Eine Zeile, die außerhalb geschützter Bereiche mit
   `^ {0,3}\\d+\\.\\s+` beginnt, startet eine neue Erwartung (eine noch offene
   endet dort ohne Punkte) und gibt ihr die Nummer als `label`. Nummern sind
   freiwillig, z. B. für Lösungsschritte; es wird nie automatisch nummeriert.
4. **Rest:** Text nach der letzten Punktklammer ist eine Erwartung ohne
   Punkte. Leerzeilen trennen nichts und gehören zu keiner Erwartung, wenn
   gerade keine offen ist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .inline_markup.spans import COMMENT_PATTERN, FENCE_PATTERN
from .math_span_protection import find_math_span_ranges
from .points_suffix import has_points_candidate

LABEL_RE = re.compile(r"^ {0,3}(\d+)\.\s+(.*)$")
"""Optionale Nummer am Anfang einer Erwartung (wie eine Markdown-Liste: `1)` ist keine)."""

_MASK = "\x00"


@dataclass
class ExpectationEntry:
    """Eine Erwartung: ihre Rohzeilen (ohne Nummer) bis einschließlich der Punktklammer.

    Attributes:
        label: Nummer wie geschrieben (`"1"`) oder ``None``.
        lines: Rohzeilen; in der ersten ist eine Nummer bereits entfernt.
        line_numbers: 0-basierte Zeilennummern zu `lines`.
    """

    label: str | None
    lines: list[str] = field(default_factory=list)
    line_numbers: list[int] = field(default_factory=list)

    def visible_lines(self) -> list[str]:
        """Zeilen ohne `%%`-Kommentare, wie die Pipeline sie sieht (mehrzeilige Kommentare verbinden Zeilen)."""
        return COMMENT_PATTERN.sub("", "\n".join(self.lines)).split("\n")

    def suffix_line(self) -> str:
        """Letzte nicht leere sichtbare Zeile -- dort steht eine eventuelle Punktklammer."""
        return next((line for line in reversed(self.visible_lines()) if line.strip()), "")


@dataclass
class ExpectationLayout:
    """Ergebnis von `classify_expectations`.

    Attributes:
        entries: Erwartungen in Dokumentreihenfolge.
        lines: alle Rohzeilen (Zeilenenden vereinheitlicht), Index = Zeilennummer.
    """

    entries: list[ExpectationEntry]
    lines: list[str] = field(default_factory=list)


def classify_expectations(content: str) -> ExpectationLayout:
    """Zerlegt den Rohinhalt eines Erwartungsblocks nach den Regeln im Moduldocstring."""
    text = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    masked_lines = _masked(text).split("\n")
    entries: list[ExpectationEntry] = []
    current: ExpectationEntry | None = None
    for number, (line, masked) in enumerate(zip(lines, masked_lines)):
        label = LABEL_RE.match(masked)
        if label:
            current = _close(entries, current)
            current = ExpectationEntry(label.group(1))
            line = line[label.start(2):]
        elif current is None:
            if not line.strip():
                continue
            current = ExpectationEntry(None)
        current.lines.append(line)
        current.line_numbers.append(number)
        if has_points_candidate(masked.replace(_MASK, "")):
            current = _close(entries, current)
    _close(entries, current)
    return ExpectationLayout(entries, lines)


def _close(entries: list[ExpectationEntry], entry: ExpectationEntry | None) -> None:
    """Übernimmt eine offene Erwartung mit sichtbarem Inhalt; liefert immer ``None`` (keine offene mehr)."""
    if entry is not None and any(line.strip() for line in entry.visible_lines()):
        entries.append(entry)
    return None


def _masked(text: str) -> str:
    """Text mit allen geschützten Bereichen als neutrale Zeichen (Zeilenumbrüche bleiben).

    Spätere Muster laufen auf dem schon maskierten Text, damit z. B. `%%` in
    einer Formel keinen Kommentar beginnt -- wie in der Pipeline, die Mathe vor
    Kommentaren schützt.
    """
    masked = text
    for finder in (find_math_span_ranges, _comment_ranges, _fence_ranges):
        masked = _mask(masked, finder(masked))
    return masked


def _comment_ranges(text: str) -> list[tuple[int, int]]:
    """Zeichenbereiche aller `%%…%%`-Kommentare."""
    return [match.span() for match in COMMENT_PATTERN.finditer(text)]


def _fence_ranges(text: str) -> list[tuple[int, int]]:
    """Zeichenbereiche aller Codezäune (inklusive der Zaunzeilen)."""
    return [match.span() for match in FENCE_PATTERN.finditer(text)]


def _mask(text: str, ranges: list[tuple[int, int]]) -> str:
    """Ersetzt alle Zeichen in `ranges` außer Zeilenumbrüchen durch `_MASK`."""
    chars = list(text)
    for begin, end in ranges:
        for index in range(begin, end):
            if chars[index] != "\n":
                chars[index] = _MASK
    return "".join(chars)
