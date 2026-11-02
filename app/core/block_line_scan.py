"""Zeilenweise Blockstruktur eines Blattwerk-Dokuments -- die eine Zustandsmaschine dafür.

Ordnet jeder Quellzeile genau eine `LineKind` zu und fasst Blöcke als
`BlockSpan` zusammen. Die Regeln sind **die des Parsers** (`parse_blocks` in
`blatt_kern_shared_parsing.py`, dieselben Muster):

- Blöcke sind flach. Innerhalb eines Blocks ist jede Zeile Inhalt, bis eine
  Zeile genau `:::` lautet (nach `strip()`).
- Eine Kopfzeile innerhalb eines Blocks öffnet nichts (der Parser liest sie
  als Inhalt); sie wird als `NESTED_OPEN`/`NESTED_SELF_CLOSING` markiert,
  damit der Validator `BL004` melden kann.
- `:::` mit weiterem Text dahinter (`::: x`, `:::-`) ist weder Kopf noch
  Schluss (`MALFORMED`, Validator `BL002`).
- Ein am Dokumentende offener Block hat `close_line=None` (Validator `BL017`;
  der Parser macht daraus Rohtext).

Nutzer: Validator (Markersyntax), Editor (Hervorhebung, Gliederung,
Blockpaar, Completion-Kontext, Nutzungszählung), die Tabellenumwandlung und
das Block-Einfügen. Vorher hatte jede dieser Stellen eine eigene Schleife mit
teils anderen Schließregeln.

GRENZE: `parse_blocks` und `build_block_index_line_map` behalten ihre eigene
Schleife. Sie bauen zusätzlich Rohtext- und Markerblöcke mit Blockindizes und
sind die Referenz, an der diese Regeln ausgerichtet sind.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cached_property

from .blatt_kern_shared_parsing import _BLOCK_START_PATTERN, _SELF_CLOSING_BLOCK_PATTERN
from .frontmatter import frontmatter_bounds

BLOCK_CLOSE_MARKER = ":::"
"""Die einzige gültige Schlusszeile eines Blocks (nach `strip()`)."""


class LineKind(Enum):
    """Rolle einer Quellzeile in der Blockstruktur."""

    FRONTMATTER = "frontmatter"
    OUTSIDE = "outside"
    OPEN = "open"
    SELF_CLOSING = "self_closing"
    CONTENT = "content"
    CLOSE = "close"
    STRAY_CLOSE = "stray_close"
    NESTED_OPEN = "nested_open"
    NESTED_SELF_CLOSING = "nested_self_closing"
    MALFORMED = "malformed"


_HEADER_KINDS = frozenset({LineKind.OPEN, LineKind.SELF_CLOSING, LineKind.NESTED_OPEN, LineKind.NESTED_SELF_CLOSING})


@dataclass(frozen=True)
class ScannedLine:
    """Eine klassifizierte Quellzeile.

    Attributes:
        number: Zeilennummer (1-basiert, inklusive `base_line`-Versatz).
        stripped: Zeileninhalt ohne Rand-Leerraum.
        kind: Rolle der Zeile.
        header_type: Blockname, wenn die Zeile selbst ein Kopf ist (sonst `None`), wie geschrieben.
        header_options: Optionstext des Kopfes (ohne schließendes `:::`), sonst `""`.
        span: Index in `BlockScan.spans` des Blocks, zu dem die Zeile gehört
            (Kopf, Inhalt, Schluss), sonst `None`.
    """

    number: int
    stripped: str
    kind: LineKind
    header_type: str | None = None
    header_options: str = ""
    span: int | None = None

    @property
    def is_header(self) -> bool:
        """True für jede Kopfzeile, auch eine verschachtelte (vom Parser als Inhalt gelesene)."""
        return self.kind in _HEADER_KINDS


@dataclass(frozen=True)
class BlockSpan:
    """Ein Block mit Inhalt von der Kopf- bis zur Schlusszeile.

    Attributes:
        open_line: Zeilennummer des Kopfes.
        close_line: Zeilennummer der `:::`-Zeile, `None` wenn der Block offen bleibt.
        block_type: Blockname wie geschrieben.
        options_text: Optionstext des Kopfes.
    """

    open_line: int
    close_line: int | None
    block_type: str
    options_text: str

    def contains(self, line: int, last_line: int) -> bool:
        """True, wenn `line` zwischen Kopf und Schluss liegt (beide eingeschlossen).

        Ein offener Block reicht bis `last_line` (letzte Zeile des Dokuments).
        """
        end = self.close_line if self.close_line is not None else last_line
        return self.open_line <= line <= end


@dataclass(frozen=True)
class BlockScan:
    """Ergebnis von `scan_block_lines`: alle Zeilen plus die Blöcke."""

    lines: tuple[ScannedLine, ...]
    spans: tuple[BlockSpan, ...]
    base_line: int = 1

    @property
    def last_line(self) -> int:
        """Nummer der letzten Zeile (`base_line - 1` bei leerem Text)."""
        return self.base_line + len(self.lines) - 1

    def line(self, number: int) -> ScannedLine | None:
        """Die klassifizierte Zeile mit dieser Nummer, oder `None` außerhalb des Textes."""
        index = number - self.base_line
        return self.lines[index] if 0 <= index < len(self.lines) else None

    def span_at(self, number: int) -> BlockSpan | None:
        """Der Block, zu dem Zeile `number` gehört (Kopf bis Schluss), oder `None`."""
        scanned = self.line(number)
        if scanned is None or scanned.span is None:
            return None
        return self.spans[scanned.span]

    @cached_property
    def headers(self) -> tuple[ScannedLine, ...]:
        """Alle Kopfzeilen auf oberster Ebene (öffnend und selbstschließend), in Dokumentreihenfolge."""
        return tuple(line for line in self.lines if line.kind in (LineKind.OPEN, LineKind.SELF_CLOSING))

    @cached_property
    def frontmatter_lines(self) -> range:
        """Zeilennummern des Frontmatters (leer, wenn keins erkannt wurde)."""
        numbers = [line.number for line in self.lines if line.kind is LineKind.FRONTMATTER]
        return range(numbers[0], numbers[-1] + 1) if numbers else range(0)


def scan_block_lines(text: str, *, base_line: int = 1, detect_frontmatter: bool = True) -> BlockScan:
    """Klassifiziert alle Zeilen von `text` nach den Blockregeln des Parsers.

    Args:
        text: Dokumenttext. Getrennt wird nur an `\\n` (wie Tk-`Text` und
            `frontmatter.py`), damit die Zeilennummern denen im Editor entsprechen.
        base_line: Nummer der ersten Zeile. Der Validator übergibt hier die
            Startzeile des Inhalts hinter dem Frontmatter.
        detect_frontmatter: Frontmatter am Textanfang per `frontmatter_bounds`
            erkennen und als `FRONTMATTER` markieren. `False`, wenn `text`
            schon der Inhalt hinter dem Frontmatter ist (sonst würde eine
            Trennlinie `---` am Inhaltsanfang als Frontmatter gelten).

    Returns:
        Die Zeilen und Blöcke.
    """
    raw_lines = (text or "").split("\n")
    frontmatter_count = _frontmatter_line_count(text) if detect_frontmatter else 0
    lines: list[ScannedLine] = []
    spans: list[BlockSpan] = []
    open_index: int | None = None
    open_header: tuple[int, str, str] | None = None

    for offset, raw_line in enumerate(raw_lines):
        number = base_line + offset
        stripped = raw_line.strip()
        if offset < frontmatter_count:
            lines.append(ScannedLine(number, stripped, LineKind.FRONTMATTER))
            continue
        if open_header is not None:
            kind, header_type, options = _classify_inside(stripped)
            lines.append(ScannedLine(number, stripped, kind, header_type, options, open_index))
            if kind is LineKind.CLOSE:
                spans.append(BlockSpan(open_header[0], number, open_header[1], open_header[2]))
                open_header = None
            continue
        kind, header_type, options = _classify_outside(stripped)
        if kind is LineKind.OPEN:
            open_index = len(spans)
            open_header = (number, header_type or "", options)
            lines.append(ScannedLine(number, stripped, kind, header_type, options, open_index))
            continue
        lines.append(ScannedLine(number, stripped, kind, header_type, options))

    if open_header is not None:
        spans.append(BlockSpan(open_header[0], None, open_header[1], open_header[2]))
    return BlockScan(tuple(lines), tuple(spans), base_line)


def _frontmatter_line_count(text: str) -> int:
    """Anzahl der Zeilen, die zum Frontmatter gehören (0 ohne Frontmatter)."""
    bounds = frontmatter_bounds(text or "")
    return 0 if bounds is None else bounds.content_start_line - 1


def _match_header(stripped: str) -> tuple[bool, str, str] | None:
    """`(selbstschließend, Name, Optionstext)` für eine Kopfzeile, sonst `None`."""
    self_closing = _SELF_CLOSING_BLOCK_PATTERN.match(stripped)
    if self_closing:
        return True, self_closing.group(1), self_closing.group(2).strip()
    opening = _BLOCK_START_PATTERN.match(stripped)
    if opening:
        return False, opening.group(1), opening.group(2).strip()
    return None


def _classify_inside(stripped: str) -> tuple[LineKind, str | None, str]:
    """Rolle einer Zeile innerhalb eines offenen Blocks."""
    if stripped == BLOCK_CLOSE_MARKER:
        return LineKind.CLOSE, None, ""
    header = _match_header(stripped)
    if header is not None:
        self_closing, name, options = header
        return (LineKind.NESTED_SELF_CLOSING if self_closing else LineKind.NESTED_OPEN), name, options
    if stripped.startswith(BLOCK_CLOSE_MARKER):
        return LineKind.MALFORMED, None, ""
    return LineKind.CONTENT, None, ""


def _classify_outside(stripped: str) -> tuple[LineKind, str | None, str]:
    """Rolle einer Zeile auf oberster Ebene."""
    if stripped == BLOCK_CLOSE_MARKER:
        return LineKind.STRAY_CLOSE, None, ""
    header = _match_header(stripped)
    if header is not None:
        self_closing, name, options = header
        return (LineKind.SELF_CLOSING if self_closing else LineKind.OPEN), name, options
    if stripped.startswith(BLOCK_CLOSE_MARKER):
        return LineKind.MALFORMED, None, ""
    return LineKind.OUTSIDE, None, ""
