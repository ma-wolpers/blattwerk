"""Block einfügen: am Cursor, um eine Markierung herum oder als Spalten (reine Funktion, ohne Tk).

`plan_block_insert` beschreibt die Änderung als `BlockInsertEdit`
(ersetze `[start, end)` durch `text`, Cursor danach bei `start + cursor`)
oder meldet per `BlockInsertError`, warum es hier nicht geht. Der Editor
wendet die Änderung nur noch an (`blatt_ui_editor_block_insert.py`).

Regeln (vom Nutzer festgelegt, siehe Wunschliste Blattwerk › blöcke):

- **Ohne Markierung:** Der Block steht auf eigenen Zeilen. Steht Text vor
  oder hinter dem Cursor, wird die Zeile dort geteilt. Der Cursor landet auf
  dem Platzhalter der Vorlage.
- **Mit Markierung:** Die Markierung wird Inhalt. An Trennzeilen (Kontroll-
  marker wie `--`, `--!`, selbstschließende `:::`-Zeilen) wird sie in mehrere
  Blöcke geteilt; die Trennzeilen bleiben stehen. Ganz markierte Blöcke
  bekommen nur einen neuen Kopf, mit den Optionen, die der neue Typ laut
  `BLOCK_ALLOWED_OPTIONS` kennt; der Rest wird in `note` genannt.
- **`columns`:** Die `--`-Teile der Markierung werden Spalten (2 bis
  `COLUMNS_MAX`), eine Markierung ohne `--` kommt in die erste Spalte.
- **Immer ein Fehler:** Stelle oder Markierung in einem Block, im
  Frontmatter, ein nur teilweise markierter Block, Spalten in Spalten, eine
  Markierung für einen Block ohne Inhalt (`BODYLESS_BLOCK_TYPES`) oder für
  das Bild. Ob eine Markierung eine Formel schneidet, prüft der Editor vorher
  mit derselben Funktion wie die Marker-Tasten.
"""

from __future__ import annotations

from dataclasses import dataclass

from .answer_table_layout import width_tokens
from .blatt_kern_shared_parsing import _SOFT_SECTION_BREAK_LITERAL, format_block_header, parse_options
from .blatt_validator_columns import COLUMNS_SCOPE_RESET_BLOCK_TYPES
from .blatt_validator_constants import BLOCK_ALLOWED_OPTIONS, BODYLESS_BLOCK_TYPES
from .block_insert_context import BlockInsertError, DocumentLayout
from .block_line_scan import BLOCK_CLOSE_MARKER, LineKind, scan_block_lines
from .columns_count import COLUMNS_MAX, COLUMNS_MIN
from .control_markers import is_control_marker_line
from .exam_parts_position import PART_SPLIT_BLOCKS
from .insert_placeholders import resolve_insert_placeholders

__all__ = ["BlockInsertEdit", "BlockInsertError", "plan_block_insert"]

_MARKERS_NOT_IN_COLUMNS = COLUMNS_SCOPE_RESET_BLOCK_TYPES | PART_SPLIT_BLOCKS
"""Marker, die keinen Platz in einem Spaltenbereich haben: `--!` beendet ihn, `--hm`/`--w` meldet KL004."""


@dataclass(frozen=True)
class BlockInsertEdit:
    """Eine Textänderung: `[start, end)` durch `text` ersetzen, Cursor danach bei `start + cursor`.

    Attributes:
        note: Hinweis für die Statusleiste (z. B. verworfene Optionen), sonst `None`.
    """

    start: int
    end: int
    text: str
    cursor: int
    note: str | None = None


def plan_block_insert(document: str, start: int, end: int, snippet: str, block_type: str | None) -> BlockInsertEdit:
    """Plant das Einfügen von `snippet` (Blocktyp `block_type`, `None` = kein Block, z. B. Bild).

    Args:
        document: Gesamter Editortext.
        start, end: Markierung als Offsets; `start == end` (oder nur Leerraum markiert) = Cursor.
        snippet: Vorlage mit Cursor-Platzhalter (`BLOCK_INSERT_SNIPPETS`).
        block_type: Blocktyp der Vorlage.

    Raises:
        BlockInsertError: Mit einer Meldung für die Statusleiste.
    """
    layout = DocumentLayout(document)
    if end > start and document[end - 1] == "\n":
        end -= 1  # Markierung bis an den Anfang der nächsten Zeile = bis zum Ende dieser Zeile
    if not document[start:end].strip():
        layout.check_point(start, outside_columns=block_type == "columns")
        body, cursor = _snippet_body(snippet)
        return _place(layout, start, start, body, cursor)
    if block_type is None:
        raise BlockInsertError("Ein Bild übernimmt keine Markierung. Setze den Cursor ohne Markierung.")
    if block_type in BODYLESS_BLOCK_TYPES - {"columns"}:
        raise BlockInsertError(f"`:::{block_type}` hat keinen Inhalt und kann keine Markierung aufnehmen.")
    if layout.covered_regions(start, end):
        start, end = layout.line_start(layout.line_of(start)), layout.line_end(layout.line_of(end))
    if block_type == "columns":
        return _wrap_in_columns(layout, start, end, snippet)
    return _wrap_selection(layout, start, end, snippet, block_type)


def _snippet_body(snippet: str) -> tuple[str, int]:
    """Vorlagentext ohne Platzhalter und ohne abschließenden Zeilenumbruch, plus Cursor darin."""
    text, cursor = resolve_insert_placeholders(snippet)
    body = text[:-1] if text.endswith("\n") else text
    return body, min(cursor, len(body))


def _place(layout: DocumentLayout, start: int, end: int, body: str, cursor: int, note: str | None = None) -> BlockInsertEdit:
    """Setzt `body` auf eigene Zeilen an `[start, end)`; Text davor/danach in derselben Zeile bleibt getrennt stehen.

    Leerraum an der Trennstelle wird mit ersetzt: Aus `a |b` wird `a`, Block,
    `b`, nicht `a `, Block, ` b`; reiner Leerraum vor oder hinter der Stelle
    hinterlässt keine Zeile aus Leerzeichen.
    """
    text = layout.text
    first, last = layout.line_of(start), layout.line_of(end)
    before = text[layout.line_start(first):start]
    after = text[end:layout.line_end(last)]
    prefix = "\n" if before.strip() else ""
    suffix = "\n" if after.strip() else ""
    edit_start = start - (len(before) - len(before.rstrip())) if before.strip() else layout.line_start(first)
    edit_end = end + (len(after) - len(after.lstrip())) if after.strip() else layout.line_end(last)
    return BlockInsertEdit(edit_start, edit_end, prefix + body + suffix, len(prefix) + cursor, note)


def _is_separator(stripped: str) -> bool:
    """Trennzeile, die nicht in einen Block darf: Kontrollmarker oder eine `:::`-Zeile außerhalb eines Blocks."""
    return is_control_marker_line(stripped) or stripped.startswith(BLOCK_CLOSE_MARKER)


def _selected_lines(layout: DocumentLayout, start: int, end: int):
    """`(Zeilennummer, markierter Text der Zeile)` für jede Zeile der Markierung."""
    first = layout.line_of(start)
    return [(first + index, piece) for index, piece in enumerate(layout.text[start:end].split("\n"))]


def _wrap_selection(layout: DocumentLayout, start: int, end: int, snippet: str, block_type: str) -> BlockInsertEdit:
    """Macht aus jedem Textabschnitt der Markierung einen Block und tauscht die Köpfe ganz markierter Blöcke."""
    header = _snippet_body(snippet)[0].split("\n")[0]
    output: list[str] = []
    text_run: list[str] = []
    dropped: list[str] = []
    cursor_line: list[int] = []

    def flush_text():
        lines = list(text_run)
        text_run.clear()
        while lines and not lines[0].strip():
            output.append(lines.pop(0))
        trailing = []
        while lines and not lines[-1].strip():
            trailing.insert(0, lines.pop())
        if lines:
            cursor_line.append(len(output) + 1)
            output.extend([header, *lines, BLOCK_CLOSE_MARKER])
        output.extend(trailing)

    for line, piece in _selected_lines(layout, start, end):
        scanned = layout.scanned(line)
        if scanned.span is not None:
            flush_text()
            if scanned.kind is LineKind.OPEN:
                cursor_line.append(len(output) + 1)
                piece = _replace_header(piece, scanned.header_type, scanned.header_options, block_type, dropped)
            output.append(piece)
        elif _is_separator(piece.strip()):
            flush_text()
            output.append(piece)
        else:
            text_run.append(piece)
    flush_text()

    cursor = sum(len(line) + 1 for line in output[: cursor_line[0]]) if cursor_line else 0
    note = None
    if dropped:
        note = f"Nicht übernommene Optionen (gelten nicht für `:::{block_type}`): {', '.join(dropped)}"
    return _place(layout, start, end, "\n".join(output), cursor, note)


def _replace_header(line: str, old_type: str, old_options: str, new_type: str, dropped: list[str]) -> str:
    """Neuer Kopf für einen ganz markierten Block: erlaubte Optionen bleiben, der Rest landet in `dropped`."""
    if old_type.lower() == new_type:
        return line
    allowed = BLOCK_ALLOWED_OPTIONS.get(new_type, frozenset())
    options = parse_options(old_options)
    dropped.extend(f"{key}={value}" for key, value in options.items() if key not in allowed)
    indent = line[: len(line) - len(line.lstrip())]
    return indent + format_block_header(new_type, {key: value for key, value in options.items() if key in allowed})


def _wrap_in_columns(layout: DocumentLayout, start: int, end: int, snippet: str) -> BlockInsertEdit:
    """Legt einen Spaltenbereich um die Markierung; jede `--`-Zeile beginnt eine neue Spalte."""
    layout.check_point(start, outside_columns=True)
    layout.check_no_columns(start, end)
    parts: list[list[str]] = [[]]
    for line, piece in _selected_lines(layout, start, end):
        marker = layout.marker_block_type(line)
        if marker in _MARKERS_NOT_IN_COLUMNS:
            raise BlockInsertError(f"`{piece.strip()}` (Zeile {line}) darf nicht in einem Spaltenbereich stehen.")
        if layout.scanned(line).span is None and piece.strip() == _SOFT_SECTION_BREAK_LITERAL:
            parts.append([])
        else:
            parts[-1].append(piece)
    parts = [_trim_blank_edges(part) for part in parts]
    if len(parts) > COLUMNS_MAX:
        raise BlockInsertError(f"Die Markierung hat {len(parts)} Teile; ein Spaltenbereich fasst höchstens {COLUMNS_MAX} Spalten.")
    if len(parts) < COLUMNS_MIN:
        parts.append([""])

    header_line = scan_block_lines(_snippet_body(snippet)[0]).headers[0]
    options = parse_options(header_line.header_options)
    options["cols"] = str(len(parts))
    for key in ("widths", "ratio"):
        # Gezählt wie BL014; passt die Zahl nicht, fällt die Angabe weg und der Renderer verteilt automatisch.
        if key in options and len(width_tokens(options[key])) != len(parts):
            del options[key]
    nextcol = format_block_header("nextcol", self_closing=True)
    output = [format_block_header("columns", options, self_closing=True), *parts[0]]
    for part in parts[1:]:
        output.extend([nextcol, *part])
    output.append(format_block_header("endcolumns", self_closing=True))
    return _place(layout, start, end, "\n".join(output), len(output[0]) + 1)


def _trim_blank_edges(lines: list[str]) -> list[str]:
    """Entfernt Leerzeilen am Anfang und Ende einer Spalte (mindestens eine Zeile bleibt)."""
    while len(lines) > 1 and not lines[0].strip():
        lines.pop(0)
    while len(lines) > 1 and not lines[-1].strip():
        lines.pop()
    return lines
