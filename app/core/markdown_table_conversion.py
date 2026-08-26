"""Converts raw GFM Markdown tables in top-level document prose into `:::table` blocks.

Used by the editor's "Extras -> Markdown-Tabellen in Blattwerk-Tabellen
umwandeln" action (`app/ui/blatt_ui_editor.py`). **Not** a full GFM table
parser -- it recognizes ordinary tables (header row, `---` separator row,
data rows, standard `|`-cell splitting with `\\|` escaping) and leaves
anything more exotic (cell text spanning multiple lines, unusual escape
conventions, ...) untouched rather than risk a wrong conversion. Only
top-level prose is scanned -- text inside a `:::block ... :::` fence is
never rewritten, since a `:::table` block cannot be nested inside another
block (splitting the surrounding block around the table would, for a type
like `:::task`, duplicate `points=`/`work=` options and corrupt the
worksheet's point total -- see docs/intern/DEVELOPMENT_LOG.md).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

_BLOCK_START_PATTERN = re.compile(r"^:::(\w+)(.*)$")
_SELF_CLOSING_BLOCK_PATTERN = re.compile(r"^:::(\w+)(.*?):::$")
"""Mirrors `blatt_kern_shared_parsing.py::parse_blocks`'s fence regexes
exactly. Kept as an intentional local duplicate rather than an import of
those private module-level constants -- the same two patterns are already
independently duplicated twice in `app/ui/blatt_ui_editor.py` (syntax
highlighting, block-pair matching), so this follows established project
precedent rather than introducing new cross-module coupling."""

_UNESCAPED_PIPE_PATTERN = re.compile(r"(?<!\\)\|")
_DELIMITER_CELL_PATTERN = re.compile(r"^(:?)-+(:?)$")
_UNSAFE_HEADER_CHARS = re.compile(r'[|,"]')
"""Characters a header cell must not contain to be safely representable in
the target `headers="H1|H2|..."` option -- `_parse_option_list`
(`blatt_kern_answer_table.py`) naively replaces `,` with `|` and splits on
`|`, with no escape mechanism at all."""


@dataclass(frozen=True)
class MarkdownTableConversionResult:
    """Result of `convert_markdown_tables_to_blocks`.

    `new_text` is byte-identical to the input whenever `converted_count`
    is `0` (including when tables were found but all skipped -- skipped
    tables are never rewritten). `skipped` holds one human-readable German
    message per table that was recognized but deliberately left untouched.
    """

    new_text: str
    converted_count: int
    skipped: list[str]


def convert_markdown_tables_to_blocks(document_text):
    """Converts every recognizable top-level GFM Markdown table in `document_text`
    into an equivalent `:::table` block.

    Walks the document line by line, tracking whether the current line sits
    inside a `:::block ... :::` fence (in which case it is passed through
    completely unchanged) or in top-level prose (in which case contiguous
    runs of prose lines are handed to `_convert_tables_in_run`). This makes
    the transform lossless everywhere except inside a genuinely recognized,
    convertible table span.
    """
    lines = (document_text or "").splitlines(keepends=True)

    output_parts = []
    outside_run = []
    run_start_line_number = 1
    converted_count = 0
    skipped = []
    inside_block = False
    line_number = 0

    def _flush_outside_run():
        nonlocal converted_count
        if not outside_run:
            return
        transformed, run_converted, run_skipped = _convert_tables_in_run(
            outside_run, run_start_line_number
        )
        output_parts.append(transformed)
        converted_count += run_converted
        skipped.extend(run_skipped)
        outside_run.clear()

    for line in lines:
        line_number += 1
        stripped = line.strip()

        if inside_block:
            output_parts.append(line)
            if stripped == ":::":
                inside_block = False
            continue

        if _SELF_CLOSING_BLOCK_PATTERN.match(stripped):
            _flush_outside_run()
            output_parts.append(line)
            continue

        if _BLOCK_START_PATTERN.match(stripped):
            _flush_outside_run()
            output_parts.append(line)
            inside_block = True
            continue

        if not outside_run:
            run_start_line_number = line_number
        outside_run.append(line)

    _flush_outside_run()

    return MarkdownTableConversionResult(
        new_text="".join(output_parts),
        converted_count=converted_count,
        skipped=skipped,
    )


def _convert_tables_in_run(run_lines, start_line_number):
    """Scans one contiguous run of top-level prose lines for GFM tables.

    Returns `(new_text, converted_count, skipped_messages)`. Every line not
    part of a recognized, convertible table is re-emitted verbatim.
    """
    output = []
    converted = 0
    skipped = []
    index = 0
    total = len(run_lines)

    while index < total:
        header_cells = _split_table_row(run_lines[index]) if index + 1 < total else None
        delimiter_cells = _parse_delimiter_row(run_lines[index + 1]) if header_cells else None

        if not header_cells or not delimiter_cells:
            output.append(run_lines[index])
            index += 1
            continue

        table_line_number = start_line_number + index
        columns_count = len(delimiter_cells)
        body_start = index + 2
        body_end = body_start
        while (
            body_end < total
            and run_lines[body_end].strip()
            and "|" in run_lines[body_end]
        ):
            body_end += 1

        if body_end == body_start:
            skipped.append(
                f"Tabelle ab Zeile {table_line_number} übersprungen: keine Datenzeile gefunden."
            )
            output.extend(run_lines[index:body_end])
            index = body_end
            continue

        header_cells = _normalize_row_length(header_cells, columns_count)
        unsafe_cell = next(
            (cell for cell in header_cells if _UNSAFE_HEADER_CHARS.search(cell)), None
        )
        if unsafe_cell is not None:
            skipped.append(
                f"Tabelle ab Zeile {table_line_number} übersprungen: Kopfzeile enthält ein "
                f'Zeichen (|, , oder "), das im headers=-Format nicht sicher darstellbar ist.'
            )
            output.extend(run_lines[index:body_end])
            index = body_end
            continue

        body_rows = [
            _normalize_row_length(_split_table_row(run_lines[i]) or [], columns_count)
            for i in range(body_start, body_end)
        ]
        alignment_tokens = _resolve_alignment_tokens(delimiter_cells)
        line_ending = _line_ending_of(run_lines[index])

        output.append(_render_table_block(header_cells, body_rows, alignment_tokens, line_ending))
        converted += 1
        index = body_end

    return "".join(output), converted, skipped


def _split_table_row(line):
    """Splits one GFM table row line into its raw cell strings, or `None`
    if the line doesn't look like a table row at all (no unescaped `|`)."""
    stripped = line.strip()
    if "|" not in stripped:
        return None

    trimmed = stripped
    if trimmed.startswith("|"):
        trimmed = trimmed[1:]
    if trimmed.endswith("|") and not trimmed.endswith("\\|"):
        trimmed = trimmed[:-1]

    cells = _UNESCAPED_PIPE_PATTERN.split(trimmed)
    return [cell.strip().replace("\\|", "|") for cell in cells]


def _parse_delimiter_row(line):
    """Returns the delimiter-row cell tokens (e.g. `[":--", "--:"]`) when
    `line` is a valid GFM separator row, else `None`."""
    cells = _split_table_row(line)
    if not cells:
        return None
    if not all(_DELIMITER_CELL_PATTERN.match(cell) for cell in cells):
        return None
    return cells


def _normalize_row_length(row, columns_count):
    """Pads with empty cells or truncates `row` to exactly `columns_count`
    entries -- standard GFM behavior for a column-count mismatch."""
    if len(row) < columns_count:
        return row + [""] * (columns_count - len(row))
    return row[:columns_count]


def _resolve_alignment_tokens(delimiter_cells):
    """Maps GFM delimiter-cell colons to `left`/`center`/`right` tokens.

    Returns `None` when no delimiter cell has any `:` at all (the
    `alignment=` option is then omitted entirely, matching today's default
    rendering) -- otherwise every column gets an explicit token (columns
    without a `:` default to `left`), since `_parse_table_alignment`
    (`blatt_kern_answer_table.py`) silently ignores a partial token list.
    """
    if not any(":" in cell for cell in delimiter_cells):
        return None

    tokens = []
    for cell in delimiter_cells:
        left, right = cell.startswith(":"), cell.endswith(":")
        if left and right:
            tokens.append("center")
        elif right:
            tokens.append("right")
        else:
            tokens.append("left")
    return tokens


def _line_ending_of(line):
    """Returns the line ending used by `line` (`\\r\\n`/`\\n`), defaulting
    to `\\n` for a line with none (e.g. the document's last line)."""
    if line.endswith("\r\n"):
        return "\r\n"
    return "\n"


def _render_table_block(header_cells, body_rows, alignment_tokens, line_ending):
    """Renders one recognized table as `:::table ...:::` block text.

    `rows=`/`cols=` are always set explicitly to the table's actual size --
    `_render_table_answer` (`blatt_kern_answer_table.py`) defaults to
    `rows=4 cols=2` when omitted, which would silently pad a smaller
    converted table with extra empty cells.
    """
    option_parts = [
        f"rows={len(body_rows)}",
        f"cols={len(header_cells)}",
        f'headers="{"|".join(header_cells)}"',
    ]
    if alignment_tokens is not None:
        option_parts.append(f'alignment="{" ".join(alignment_tokens)}"')

    block_lines = [":::table " + " ".join(option_parts), "cells:"]
    for row in body_rows:
        cell_literals = ", ".join(json.dumps(cell, ensure_ascii=False) for cell in row)
        block_lines.append(f"  - [{cell_literals}]")
    block_lines.append(":::")

    return line_ending.join(block_lines) + line_ending
