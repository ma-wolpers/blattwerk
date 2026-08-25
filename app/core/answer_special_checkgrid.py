"""Checkgrid answer renderer -- a compact statement x checkbox-column table.

Distinct from `mc`'s `tf=true` mode: column headers (e.g. "richtig"/"falsch")
are rendered once, not repeated per statement -- much more compact for many
statements sharing the same set of columns.
"""

from __future__ import annotations

from html import escape

import yaml

from .answer_special_shared import _new_markdown_converter, normalize_markdown

_CHECKED_GLYPH = "☑"
_UNCHECKED_GLYPH = "☐"


def parse_checkgrid_payload(content):
    """Parses `columns:`/rows YAML into `(columns, rows)`.

    `columns` is a list of header strings. Each row is `(text, correct_index)`,
    `correct_index` 1-based into `columns`, or `None` if the row doesn't mark
    any column as correct (e.g. an intentionally ungraded statement).
    Returns `([], [])` for empty/unparsable content, mirroring
    `parse_crossword_entries`'s fail-quiet convention.
    """
    if not (content or "").strip():
        return [], []

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError:
        return [], []

    if not isinstance(parsed, dict):
        return [], []

    columns_raw = parsed.get("columns") or parsed.get("spalten") or []
    columns = (
        [str(column).strip() for column in columns_raw if str(column).strip()]
        if isinstance(columns_raw, list)
        else []
    )
    if not columns:
        return [], []

    rows_raw = parsed.get("rows") or parsed.get("zeilen") or parsed.get("items") or []
    rows = []
    if isinstance(rows_raw, list):
        for entry in rows_raw:
            if not isinstance(entry, dict):
                continue
            text = str(entry.get("text") or entry.get("statement") or "").strip()
            if not text:
                continue
            correct_raw = entry.get("correct") or entry.get("richtig")
            correct_index = None
            try:
                candidate = int(correct_raw)
                if 1 <= candidate <= len(columns):
                    correct_index = candidate
            except (TypeError, ValueError):
                correct_index = None
            rows.append((text, correct_index))

    return columns, rows


def render_checkgrid_answer(options, content, include_solutions):
    """Renders a `:::checkgrid` block: one compact table, checkbox glyphs
    per statement/column, correct column marked only in solution mode."""
    columns, rows = parse_checkgrid_payload(content)
    if not columns or not rows:
        return ""

    md = _new_markdown_converter()
    header_cells = "".join(f"<th class='checkgrid-column'>{escape(column)}</th>" for column in columns)

    body_rows = []
    for text, correct_index in rows:
        statement_html = md.convert(normalize_markdown(text)).strip()
        checkbox_cells = []
        for column_index in range(1, len(columns) + 1):
            is_correct = include_solutions and column_index == correct_index
            glyph = _CHECKED_GLYPH if is_correct else _UNCHECKED_GLYPH
            cell_classes = "checkgrid-box is-correct" if is_correct else "checkgrid-box"
            checkbox_cells.append(f"<td class='{cell_classes}'>{glyph}</td>")
        body_rows.append(
            f"<tr><td class='checkgrid-statement'>{statement_html}</td>{''.join(checkbox_cells)}</tr>"
        )

    table_html = (
        "<table class='checkgrid-table'>"
        f"<thead><tr><th></th>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    return f"<div class='answer checkgrid-answer'>{table_html}</div>"


def estimate_checkgrid_weight(options, content):
    """Estimates layout weight from row/column counts."""
    columns, rows = parse_checkgrid_payload(content)
    if not columns or not rows:
        return 0.0
    return max(1.2, min(7.0, 0.6 + len(rows) * 0.35 + len(columns) * 0.15))
