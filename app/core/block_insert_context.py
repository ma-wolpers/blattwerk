"""Wo im Dokument ein Block eingefügt werden darf: Zeilen-Offsets, Block- und Spaltenbereiche.

Grundlage für `block_insert_transform.py`. Alle Strukturfragen beantworten
die vorhandenen Quellen: Blöcke `scan_block_lines`, Spaltenbereiche
`analyze_columns_structure` (dieselbe Zustandsmaschine wie der Validator),
Markerzeilen `_parse_inline_control_marker` (wie der Parser), Frontmatter
`frontmatter_editing_lines` (wie im Editor). Hier wird daraus nur in
Zeichen-Offsets umgerechnet und geprüft.

Alle Offsets sind Zeichen-Offsets in `text`; Zeilen sind 1-basiert und nur
an `\\n` getrennt (wie im Tk-`Text`).
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from functools import cached_property

from .blatt_kern_shared_parsing import _parse_inline_control_marker, parse_options
from .blatt_validator_columns import COLUMNS_SCOPE_RESET_BLOCK_TYPES, analyze_columns_structure
from .block_line_scan import BlockSpan, LineKind, ScannedLine, scan_block_lines
from .frontmatter import frontmatter_editing_lines


class BlockInsertError(ValueError):
    """Einfügen ist an dieser Stelle nicht möglich; die Nachricht steht so in der Statusleiste."""


@dataclass(frozen=True)
class BlockRegion:
    """Ein Block als Zeichenbereich `[start, end)`: vom `:::` des Kopfes bis hinter die Schlusszeile.

    Attributes:
        span: Der Block aus `scan_block_lines`.
        start: Offset des ersten Nicht-Leerzeichens der Kopfzeile.
        end: Offset hinter dem letzten Zeichen der Schlusszeile (ohne `\\n`);
            bei einem offenen Block das Textende.
    """

    span: BlockSpan
    start: int
    end: int


class DocumentLayout:
    """Blockstruktur eines Dokuments, umgerechnet in Zeichen-Offsets."""

    def __init__(self, text: str):
        self.text = text
        self.scan = scan_block_lines(text)
        self._line_starts = [0] + [index + 1 for index, char in enumerate(text) if char == "\n"]

    # -- Zeilen ------------------------------------------------------------------

    def line_of(self, offset: int) -> int:
        """Zeile (1-basiert), in der `offset` liegt."""
        return bisect_right(self._line_starts, offset)

    def line_start(self, line: int) -> int:
        """Offset des Zeilenanfangs."""
        return self._line_starts[line - 1]

    def line_end(self, line: int) -> int:
        """Offset hinter dem letzten Zeichen der Zeile (vor ihrem `\\n`)."""
        return self._line_starts[line] - 1 if line < len(self._line_starts) else len(self.text)

    def lines_between(self, start: int, end: int) -> range:
        """Alle Zeilen, die der Bereich `[start, end)` berührt (mindestens die Zeile von `start`)."""
        return range(self.line_of(start), self.line_of(max(start, end - 1)) + 1)

    def scanned(self, line: int) -> ScannedLine:
        """Die klassifizierte Zeile."""
        return self.scan.line(line)

    def marker_block_type(self, line: int) -> str | None:
        """Pseudo-Blocktyp einer Kontrollmarker-Zeile auf oberster Ebene (`--!` -> `pagebreak`), sonst `None`."""
        scanned = self.scanned(line)
        if scanned.kind is not LineKind.OUTSIDE:
            return None
        parsed = _parse_inline_control_marker(scanned.stripped)
        return parsed[0] if parsed else None

    # -- Bereiche -----------------------------------------------------------------

    @cached_property
    def block_regions(self) -> tuple[BlockRegion, ...]:
        """Alle Blöcke als Zeichenbereiche."""
        regions = []
        for span in self.scan.spans:
            header_start = self.line_start(span.open_line)
            header_text = self.text[header_start:self.line_end(span.open_line)]
            start = header_start + len(header_text) - len(header_text.lstrip())
            end = self.line_end(span.close_line) if span.close_line is not None else len(self.text)
            regions.append(BlockRegion(span, start, end))
        return tuple(regions)

    @cached_property
    def columns_regions(self) -> tuple[tuple[int, int, int], ...]:
        """Spaltenbereiche als `(start, end, Kopfzeile)` laut `analyze_columns_structure`.

        Ein Bereich reicht bis hinter `:::endcolumns :::`, bei einem Ende an
        einem Scope-Wechsel (`--!`) bis vor dessen Zeile, sonst bis zum Textende.
        """
        items, item_lines = [], []
        for scanned in self.scan.lines:
            if scanned.kind in (LineKind.OPEN, LineKind.SELF_CLOSING):
                items.append((scanned.header_type.lower(), parse_options(scanned.header_options), ""))
                item_lines.append(scanned.number)
            elif self.marker_block_type(scanned.number):
                items.append((self.marker_block_type(scanned.number), {}, ""))
                item_lines.append(scanned.number)
        _diagnostics, scopes = analyze_columns_structure(items)
        regions = []
        for scope in scopes:
            open_line = item_lines[scope.open_index]
            if scope.close_index is None:
                end = len(self.text)
            elif items[scope.close_index][0] in COLUMNS_SCOPE_RESET_BLOCK_TYPES:
                end = self.line_start(item_lines[scope.close_index])
            else:
                end = self.line_end(item_lines[scope.close_index])
            regions.append((self.line_start(open_line), end, open_line))
        return tuple(regions)

    # -- Prüfungen ----------------------------------------------------------------

    def check_point(self, offset: int, *, outside_columns: bool = False) -> None:
        """Fehler, wenn an `offset` kein Block beginnen darf (Frontmatter, in einem Block, ggf. in Spalten)."""
        if self.line_of(offset) in frontmatter_editing_lines(self.text):
            raise BlockInsertError("Im Frontmatter kann kein Block stehen.")
        for region in self.block_regions:
            # Ein offener Block reicht bis einschließlich Textende: auch dort steht man noch in ihm.
            unclosed = region.span.close_line is None
            if region.start < offset < region.end or (unclosed and region.start < offset == region.end):
                raise BlockInsertError(_inside_message(region.span))
        if outside_columns:
            for start, end, open_line in self.columns_regions:
                if start < offset < end:
                    raise BlockInsertError(f"Hier liegt schon ein Spaltenbereich (ab Zeile {open_line}); Spalten lassen sich nicht verschachteln.")

    def covered_regions(self, start: int, end: int) -> list[BlockRegion]:
        """Die Blöcke, die `[start, end)` ganz enthält; Fehler bei jeder anderen Überschneidung.

        Raises:
            BlockInsertError: Die Markierung berührt das Frontmatter, liegt in
                einem Block, schneidet einen Block nur teilweise oder enthält
                einen nicht geschlossenen Block.
        """
        frontmatter = frontmatter_editing_lines(self.text)
        if any(line in frontmatter for line in self.lines_between(start, end)):
            raise BlockInsertError("Die Markierung reicht ins Frontmatter; dort kann kein Block stehen.")
        covered = []
        for region in self.block_regions:
            if not (start < region.end and end > region.start):
                continue
            if region.span.close_line is None:
                raise BlockInsertError(_unclosed_message(region.span))
            if start <= region.start and end >= region.end:
                covered.append(region)
            elif start > region.start and end < region.end:
                raise BlockInsertError(_inside_message(region.span))
            else:
                raise BlockInsertError(
                    f"Die Markierung schneidet den Block `:::{region.span.block_type}` (Zeile {region.span.open_line}). "
                    "Markiere ihn ganz oder gar nicht."
                )
        return covered

    def check_no_columns(self, start: int, end: int) -> None:
        """Fehler, wenn `[start, end)` einen Spaltenbereich berührt oder Spalten-Marker enthält."""
        for region_start, region_end, open_line in self.columns_regions:
            if start < region_end and end > region_start:
                raise BlockInsertError(f"Die Markierung berührt einen Spaltenbereich (ab Zeile {open_line}); Spalten lassen sich nicht verschachteln.")
        for line in self.lines_between(start, end):
            if (self.scanned(line).header_type or "").lower() in ("columns", "nextcol", "endcolumns"):
                raise BlockInsertError(f"Die Markierung enthält einen Spalten-Marker (Zeile {line}); Spalten lassen sich nicht verschachteln.")


def _inside_message(span: BlockSpan) -> str:
    """Meldung für eine Stelle innerhalb eines Blocks."""
    if span.close_line is None:
        return _unclosed_message(span)
    return f"Die Stelle liegt im Block `:::{span.block_type}` (Zeile {span.open_line}). Blöcke lassen sich nicht verschachteln."


def _unclosed_message(span: BlockSpan) -> str:
    """Meldung für einen offenen Block, der bis zum Textende reicht."""
    return f"Der Block `:::{span.block_type}` (Zeile {span.open_line}) ist nicht geschlossen. Schließe ihn zuerst mit `:::`."
