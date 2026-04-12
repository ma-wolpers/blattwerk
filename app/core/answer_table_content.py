"""Helpers for table-answer content payloads and per-cell solution markers."""

from __future__ import annotations

from html import escape

import yaml

from .answer_line_markers import render_answer_content_html_for_mode


def _as_positive_int(value, default_value=1):
    """Parse optional positive integer with safe fallback."""
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default_value
    return parsed if parsed > 0 else default_value


def _normalize_table_cell(raw_cell):
    """Normalize scalar/object table cell payloads to a common dict shape."""
    if isinstance(raw_cell, dict):
        text_value = raw_cell.get("text")
        if text_value is None:
            text_value = raw_cell.get("value")
        if text_value is None:
            text_value = raw_cell.get("label")
        return {
            "text": "" if text_value is None else str(text_value),
            "colspan": _as_positive_int(raw_cell.get("colspan"), default_value=1),
            "rowspan": _as_positive_int(raw_cell.get("rowspan"), default_value=1),
        }

    return {
        "text": "" if raw_cell is None else str(raw_cell),
        "colspan": 1,
        "rowspan": 1,
    }


def parse_table_content_payload(content):
    """Parse table YAML payload and return `(cells, extra_solution_text)`.

    Behavior:
    - If the block content is a YAML mapping and contains `cells`, that matrix is used.
    - Optional keys `solution` or `solution_text` are interpreted as additional
      solution-only text shown above the table.
    - If content is not a YAML mapping, the content is treated as plain legacy
      solution text and no cell matrix is returned.
    """
    text = (content or "").strip()
    if not text:
        return [], ""

    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError:
        return [], ""

    if not isinstance(payload, dict):
        return [], ""

    raw_cells = payload.get("cells")
    if isinstance(raw_cells, list):
        cells = []
        for row in raw_cells:
            if isinstance(row, list):
                cells.append([_normalize_table_cell(value) for value in row])
            else:
                cells.append([_normalize_table_cell(row)])
    else:
        cells = []

    extra_solution_text = payload.get("solution") or payload.get("solution_text") or ""
    return cells, str(extra_solution_text)


def render_solution_marked_cell_text(raw_text, include_solutions):
    """Render table cell text with inline visibility tokens (`§{}`, `%{}`, `&{}`)."""
    text = "" if raw_text is None else str(raw_text)
    rendered = render_answer_content_html_for_mode(
        text,
        include_solutions=include_solutions,
        default_show="both",
        highlight_solution_segments=True,
    )
    return rendered if rendered.strip() else ""
