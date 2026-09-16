"""Table-Antwort-Rendering: Optionen-Parsing (Header/Breiten/Ausrichtung) und
`_render_table_answer` selbst. Der blocktyp-übergreifende Dispatcher
(`_render_answer_block`) lebt in `blatt_kern_answer_dispatch.py`, damit diese
Datei auf die Tabellen-spezifische Logik begrenzt bleibt."""

from __future__ import annotations

import re
from html import escape

from .blatt_kern_shared import _safe_int
from .answer_table_content import parse_table_content_payload, render_solution_marked_cell_text
from .blatt_kern_answer_choice import _render_answer_solution_text

def _parse_positional_option_list(raw_value):
    """Parst Listenwerte aus `a|b|c` oder `a,b,c` positionsgetreu -- leere
    Einträge (z. B. durch `||`) bleiben als eigene Position erhalten, damit
    Header-Optionen gezielt einzelne Zellen leer lassen können."""
    if not raw_value:
        return []

    normalized = str(raw_value).replace(",", "|")
    return [item.strip() for item in normalized.split("|")]

def _parse_css_size(value, default_value):
    """Liest sichere CSS-Längenangaben (z. B. `2.4cm`)."""
    if not value:
        return default_value

    text = str(value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?(px|%|cm|mm|in|pt|em|rem|vh|vw)", text, flags=re.IGNORECASE):
        return text
    return default_value

def _parse_table_widths(widths_raw, expected_cols):
    """Parst Spaltengewichte für answer-Tabellen."""
    if expected_cols < 1:
        return []

    if not widths_raw:
        return []

    normalized = str(widths_raw).replace(":", " ").replace(",", " ")
    parts = [part.strip().lower() for part in normalized.split() if part.strip()]
    if len(parts) < expected_cols:
        return []

    parts = parts[:expected_cols]

    ratio_values = []
    explicit_values = []

    for part in parts:
        number_match = re.fullmatch(r"\d+(?:\.\d+)?", part)
        fr_match = re.fullmatch(r"(\d+(?:\.\d+)?)fr", part)
        explicit_match = re.fullmatch(r"\d+(?:\.\d+)?(%|px|cm|mm|in|pt|em|rem|vh|vw)", part)

        if number_match:
            value = float(number_match.group(0))
            if value <= 0:
                return []
            ratio_values.append(value)
            continue

        if fr_match:
            value = float(fr_match.group(1))
            if value <= 0:
                return []
            ratio_values.append(value)
            continue

        if explicit_match:
            explicit_values.append(part)
            continue

        return []

    if ratio_values and explicit_values:
        return []

    if explicit_values:
        return explicit_values

    ratio_total = sum(ratio_values)
    if ratio_total <= 0:
        return []

    return [f"{(value / ratio_total) * 100:.4f}%" for value in ratio_values]


def _normalize_table_alignment_token(value):
    """Normalisiert Alias- und Kurzschreibweisen auf CSS-Ausrichtungswerte."""
    aliases = {
        "l": "left",
        "links": "left",
        "left": "left",
        "c": "center",
        "mitte": "center",
        "center": "center",
        "zentriert": "center",
        "r": "right",
        "rechts": "right",
        "right": "right",
        "j": "justify",
        "justify": "justify",
        "block": "justify",
    }
    return aliases.get(str(value).strip().lower())


def _parse_table_alignment(raw_value, expected_cols):
    """Liest globale oder spaltenindividuelle Tabellenausrichtung."""
    if not raw_value:
        return "left", []

    normalized = str(raw_value).replace(":", " ").replace(",", " ")
    parts = [part for part in normalized.split() if part.strip()]
    if not parts:
        return "left", []

    if len(parts) == 1:
        global_alignment = _normalize_table_alignment_token(parts[0])
        return (global_alignment or "left"), []

    if expected_cols < 1 or len(parts) < expected_cols:
        return "left", []

    per_column_alignments = []
    for part in parts[:expected_cols]:
        normalized_part = _normalize_table_alignment_token(part)
        if not normalized_part:
            return "left", []
        per_column_alignments.append(normalized_part)

    return per_column_alignments[0], per_column_alignments


def _render_table_answer(options, content, include_solutions):
    """Rendert eine ausfüllbare Tabelle mit optionalen Spalten-/Zeilenüberschriften."""

    cols = max(1, _safe_int(options.get("cols", 2), 2))
    rows = max(1, _safe_int(options.get("rows", 4), 4))
    row_height = _parse_css_size(options.get("row_height"), "1.9cm")

    column_headers = _parse_positional_option_list(options.get("column_headers"))
    if column_headers:
        cols = max(cols, len(column_headers))

    row_headers = _parse_positional_option_list(options.get("row_headers"))
    if row_headers:
        rows = max(rows, len(row_headers))

    cells_matrix, extra_solution_text = parse_table_content_payload(content)
    if cells_matrix:
        rows = max(rows, len(cells_matrix))
        max_payload_cols = max((len(row) for row in cells_matrix), default=0)
        cols = max(cols, max_payload_cols)

    has_row_header_column = bool(row_headers)

    table_alignment, column_alignments = _parse_table_alignment(
        options.get("alignment"), cols
    )

    widths = _parse_table_widths(options.get("widths"), cols)

    colgroup = ""
    if widths:
        col_tags = "".join(f"<col style='width:{escape(part)}'>" for part in widths)
        if has_row_header_column:
            # Ungewichtete Extra-Spalte für die Row-Header-Spalte, damit `widths=`
            # weiterhin auf die Datenspalten trifft und nicht um eine Spalte verrutscht.
            col_tags = "<col>" + col_tags
        colgroup = f"<colgroup>{col_tags}</colgroup>"

    thead = ""
    if column_headers:
        if len(column_headers) < cols:
            column_headers = column_headers + [""] * (cols - len(column_headers))
        thead_cells = []
        if has_row_header_column:
            # Schnittzelle Zeile 0/Spalte 0 hat keinen Datenbezug -- automatisch leer.
            thead_cells.append("<th></th>")
        for col_index, text in enumerate(column_headers[:cols]):
            alignment_style = ""
            if column_alignments:
                alignment_style = (
                    f" style='text-align:{escape(column_alignments[col_index])}'"
                )
            thead_cells.append(f"<th{alignment_style}>{escape(text)}</th>")
        thead = f"<thead><tr>{''.join(thead_cells)}</tr></thead>"

    body_rows = []
    blocked_columns = [0] * cols
    for row_index in range(rows):
        source_row = cells_matrix[row_index] if row_index < len(cells_matrix) else []
        source_cursor = 0
        col_index = 0
        cells = []

        if has_row_header_column:
            row_header_text = row_headers[row_index] if row_index < len(row_headers) else ""
            cells.append(
                f"<th scope='row' class='table-row-header'>{escape(row_header_text)}</th>"
            )

        while col_index < cols:
            if blocked_columns[col_index] > 0:
                blocked_columns[col_index] -= 1
                col_index += 1
                continue

            if source_cursor < len(source_row):
                source_entry = source_row[source_cursor]
                source_cursor += 1
            else:
                source_entry = None

            if isinstance(source_entry, dict):
                source_text = str(source_entry.get("text") or "")
                requested_colspan = max(1, _safe_int(source_entry.get("colspan", 1), 1))
                requested_rowspan = max(1, _safe_int(source_entry.get("rowspan", 1), 1))
            else:
                source_text = "" if source_entry is None else str(source_entry)
                requested_colspan = 1
                requested_rowspan = 1

            max_free_colspan = 1
            probe_col = col_index + 1
            while probe_col < cols and blocked_columns[probe_col] <= 0:
                max_free_colspan += 1
                probe_col += 1

            colspan = min(requested_colspan, max_free_colspan)
            rowspan = min(requested_rowspan, rows - row_index)

            cell_content = (
                render_solution_marked_cell_text(source_text, include_solutions)
                if source_text
                else ""
            )

            span_attrs = ""
            style_attr = ""
            if colspan > 1:
                span_attrs += f" colspan='{colspan}'"
            if rowspan > 1:
                span_attrs += f" rowspan='{rowspan}'"

            if column_alignments:
                style_attr = f" style='text-align:{escape(column_alignments[col_index])}'"

            cells.append(f"<td{span_attrs}{style_attr}>{cell_content}</td>")

            if rowspan > 1:
                for span_col in range(col_index, col_index + colspan):
                    blocked_columns[span_col] = max(blocked_columns[span_col], rowspan - 1)

            col_index += colspan

        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    table_html = (
        f"<div class='answer table-answer' style='--table-row-height:{escape(row_height)};--table-text-align:{escape(table_alignment)}'>"
        f"<table class='answer-table'>{colgroup}{thead}<tbody>{''.join(body_rows)}</tbody></table>"
        "</div>"
    )

    if include_solutions:
        solution_text = _render_answer_solution_text(
            extra_solution_text,
            include_solutions=True,
        )
        if solution_text:
            return _wrap_answer_with_solution(table_html, solution_text)

    return table_html

def _wrap_answer_with_solution(base_answer_html, solution_text_html):
    """Kombiniert Antwortfläche und zugehörigen Lösungstext."""
    if not solution_text_html:
        return base_answer_html

    return f"<div class='answer-with-solution'>{solution_text_html}{base_answer_html}</div>"
