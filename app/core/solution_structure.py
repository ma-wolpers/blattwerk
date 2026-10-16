"""Struktur eines `:::solution`-Blocks: einzige Zerlegung in Text-Segmente und Lösungspunkte.

Warum ein eigenes Modell statt Python-Markdowns Listenparser: Bewertung
(`solution_items`, Validator, Erwartungshorizont) und Darstellung
(`solution_display`) müssen *dieselben* Lösungspunkte sehen. Früher las der
Validator Zeilen per Regex, während Python-Markdown die Liste selbst
strukturierte -- beide wichen ab (z. B. zählte `1)` als Punkt, wurde aber als
Absatz gerendert; ein mit zwei Leerzeichen eingerücktes `- x` war für den
Validator Fortsetzung, für Markdown ein eigener nummerierter Punkt). Jetzt
baut der Renderer die oberste Liste aus dieser Klassifikation, der Inhalt
jedes Punkts läuft weiter durch die unveränderte Markdown-Pipeline.

Regeln (auf dem Rohtext, mit 0-basierten Zeilennummern):

1. **Geschützte Bereiche** in der Reihenfolge der Render-Pipeline und mit
   deren eigenen Mustern: Mathe (`find_math_span_ranges`), dann
   `%%`-Kommentare (`COMMENT_PATTERN`), dann Codezäune (`FENCE_PATTERN`).
   Eine Zeile, deren Anfang in einem solchen Bereich liegt, beginnt nie
   einen Punkt und gehört zum laufenden Segment.
2. **Kopfzeile** eines Punkts: `^ {0,3}\\d+\\.\\s+` (wie Markdown: `1)` ist keiner).
3. **Fortsetzung:** Leerzeilen, eingerückte Zeilen sowie eine nicht
   eingerückte Zeile *direkt* nach Kopf oder Fortsetzung (Lazy Continuation).
4. **Ende der Punktgruppe:** nach einer Leerzeile eine nicht eingerückte
   Zeile, die keine Kopfzeile ist.
5. **Locker** ist eine Gruppe, wenn eine Leerzeile vor einer weiteren
   Kopfzeile oder vor eingerückter Fortsetzung steht (wie Markdown: dann
   behalten die Listenpunkte ihre Absätze).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .inline_markup.spans import COMMENT_PATTERN, FENCE_PATTERN
from .math_span_protection import find_math_span_ranges

ITEM_HEAD_RE = re.compile(r"^ {0,3}(\d+)\.\s+(.*)$")
LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
"""Aufzählungs- oder Listenzeile beliebiger Einrückung (für SL004 und Unterlisten)."""


@dataclass
class SolutionEntry:
    """Ein Lösungspunkt: Kopfzeile plus Fortsetzungszeilen (Rohtext).

    Attributes:
        head: Text der Kopfzeile nach dem Listenmarker, inklusive Punkt-Suffix.
        head_line: 0-basierte Zeilennummer der Kopfzeile im Blockinhalt.
        continuation: Rohzeilen der Fortsetzung (Originaleinrückung).
        continuation_lines: 0-basierte Zeilennummern zu `continuation`.
    """

    head: str
    head_line: int
    continuation: list[str] = field(default_factory=list)
    continuation_lines: list[int] = field(default_factory=list)

    def visible_lines(self) -> list[str]:
        """Kopf- und Fortsetzungszeilen ohne `%%`-Kommentare, wie die Pipeline sie sieht.

        Kommentare werden über den ganzen Punkt entfernt (mehrzeilige Kommentare
        verbinden dabei Zeilen, wie beim Rendern). Element 0 ist die sichtbare
        Kopfzeile -- nur dort zählt ein Punkt-Suffix, z. B. auch bei
        `Text (1P) %%Notiz%%`.
        """
        return COMMENT_PATTERN.sub("", "\n".join([self.head, *self.continuation])).split("\n")


@dataclass
class SolutionSegment:
    """Ein Segment: entweder Text (`entries` leer) oder eine Gruppe von Lösungspunkten."""

    text: list[str] = field(default_factory=list)
    entries: list[SolutionEntry] = field(default_factory=list)
    loose: bool = False

    @property
    def is_items(self) -> bool:
        """Ob das Segment eine Punktgruppe (oberste nummerierte Liste) ist."""
        return bool(self.entries)


@dataclass
class SolutionLayout:
    """Ergebnis von `classify_solution`.

    Attributes:
        segments: Text-Segmente und Punktgruppen in Dokumentreihenfolge.
        protected_lines: 0-basierte Nummern der Zeilen, die in einem
            geschützten Bereich beginnen (Mathe, Kommentar, Codezaun).
        lines: alle Rohzeilen (Zeilenenden vereinheitlicht), Index = Zeilennummer.
    """

    segments: list[SolutionSegment]
    protected_lines: frozenset[int]
    lines: list[str] = field(default_factory=list)

    @property
    def entries(self) -> list[SolutionEntry]:
        """Alle Lösungspunkte in Dokumentreihenfolge."""
        return [entry for segment in self.segments for entry in segment.entries]


def classify_solution(content: str) -> SolutionLayout:
    """Zerlegt den Rohinhalt eines Lösungsblocks nach den Regeln im Moduldocstring."""
    text = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    protected = _protected_line_numbers(text, lines)
    builder = _LayoutBuilder()
    for number, line in enumerate(lines):
        builder.feed(number, line, number in protected)
    return SolutionLayout(builder.finish(), frozenset(protected), lines)


def _protected_line_numbers(text: str, lines: list[str]) -> set[int]:
    """Zeilen, deren Anfang in Mathe, Kommentar oder Codezaun liegt (Pipeline-Reihenfolge).

    Spätere Muster laufen auf einer Kopie, in der frühere Bereiche durch ein
    neutrales Zeichen ersetzt sind (Zeilenumbrüche bleiben erhalten), damit
    z. B. `%%` in einer Formel keinen Kommentar beginnt -- wie in der
    Pipeline, die Mathe vor Kommentaren schützt.
    """
    ranges: list[tuple[int, int]] = []
    masked = text
    for finder in (find_math_span_ranges, _comment_ranges, _fence_ranges):
        found = finder(masked)
        ranges.extend(found)
        masked = _mask(masked, found)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    return {number for number, start in enumerate(starts) if any(begin < start < end for begin, end in ranges)}


def _comment_ranges(text: str) -> list[tuple[int, int]]:
    """Zeichenbereiche aller `%%…%%`-Kommentare."""
    return [match.span() for match in COMMENT_PATTERN.finditer(text)]


def _fence_ranges(text: str) -> list[tuple[int, int]]:
    """Zeichenbereiche aller Codezäune (inklusive der Zaunzeilen)."""
    return [match.span() for match in FENCE_PATTERN.finditer(text)]


def _mask(text: str, ranges: list[tuple[int, int]]) -> str:
    """Ersetzt alle Zeichen in `ranges` außer Zeilenumbrüchen durch ein neutrales Zeichen."""
    chars = list(text)
    for begin, end in ranges:
        for index in range(begin, end):
            if chars[index] != "\n":
                chars[index] = "\x00"
    return "".join(chars)


class _LayoutBuilder:
    """Zustandsautomat für `classify_solution` (eine Zeile nach der anderen)."""

    def __init__(self) -> None:
        """Startet im Textmodus ohne offene Punktgruppe."""
        self.segments: list[SolutionSegment] = []
        self.current = SolutionSegment()
        self.entry: SolutionEntry | None = None
        self.after_blank = False

    def feed(self, number: int, line: str, protected: bool) -> None:
        """Ordnet eine Zeile dem passenden Segment zu (Regeln 1–5)."""
        head = None if protected else ITEM_HEAD_RE.match(line)
        if head:
            self._start_entry(number, head.group(2))
        elif self.entry is None:
            self.current.text.append(line)
        elif protected or not line.strip() or line[:1] in (" ", "\t") or not self.after_blank:
            if self.after_blank and line.strip() and line[:1] in (" ", "\t"):
                self.current.loose = True
            self.entry.continuation.append(line)
            self.entry.continuation_lines.append(number)
        else:
            self._close_group()
            self.current.text.append(line)
        self.after_blank = not protected and not line.strip()

    def _start_entry(self, number: int, head: str) -> None:
        """Beginnt einen Punkt; schließt vorher ein Text-Segment ab."""
        if self.entry is None:
            self._push(self.current)
            self.current = SolutionSegment()
        elif self.after_blank:
            self.current.loose = True
        self.entry = SolutionEntry(head, number)
        self.current.entries.append(self.entry)

    def _close_group(self) -> None:
        """Schließt die laufende Punktgruppe und öffnet ein neues Text-Segment."""
        self._push(self.current)
        self.current = SolutionSegment()
        self.entry = None

    def _push(self, segment: SolutionSegment) -> None:
        """Übernimmt ein nicht-leeres Segment in das Ergebnis."""
        if segment.entries or segment.text:
            self.segments.append(segment)

    def finish(self) -> list[SolutionSegment]:
        """Schließt das letzte Segment ab und liefert alle Segmente."""
        self._push(self.current)
        return self.segments
