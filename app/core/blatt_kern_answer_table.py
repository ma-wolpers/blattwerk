"""Table/grid/space answer rendering helpers and answer dispatcher."""

from __future__ import annotations

import re
from html import escape

from .answer_special import render_matching_answer, render_wordsearch_answer
from .blatt_kern_shared import _new_markdown_converter, _safe_int
from .answer_grid_plot import (
    render_dots_answer,
    render_geometry_answer,
    render_grid_answer,
)
from .answer_numberline import render_number_line_answer
from .answer_table_content import parse_table_content_payload, render_solution_marked_cell_text
from .answer_line_markers import (
    count_visible_answer_lines,
    render_answer_line_rows_html_for_mode,
)
from .blatt_kern_answer_choice import (
    _normalize_choice_values,
    _render_answer_solution_text,
    _render_cloze_answer,
    _render_multiple_choice_answer,
)

def _parse_option_list(raw_value):
    """Parst Listenwerte aus `a|b|c` oder `a,b,c`."""
    if not raw_value:
        return []

    normalized = str(raw_value).replace(",", "|")
    return [item.strip() for item in normalized.split("|") if item.strip()]

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
    """Rendert eine ausfüllbare Tabelle mit optionalen Zeilenlabels."""

    cols = max(1, _safe_int(options.get("cols", 2), 2))
    rows = max(1, _safe_int(options.get("rows", 4), 4))
    row_height = _parse_css_size(options.get("row_height"), "1.9cm")

    headers = _parse_option_list(options.get("headers"))
    if headers:
        cols = max(cols, len(headers))

    row_labels = _parse_option_list(options.get("row_labels"))
    if row_labels:
        rows = max(rows, len(row_labels))

    cells_matrix, extra_solution_text = parse_table_content_payload(content)
    if cells_matrix:
        rows = max(rows, len(cells_matrix))
        max_payload_cols = max((len(row) for row in cells_matrix), default=0)
        cols = max(cols, max_payload_cols)

    header_columns_raw = options.get("header_columns")
    if header_columns_raw is None:
        header_columns_raw = options.get("header_cols")
    header_columns = max(0, min(cols, _safe_int(header_columns_raw, 0)))

    table_alignment, column_alignments = _parse_table_alignment(
        options.get("alignment"), cols
    )

    widths = _parse_table_widths(options.get("widths"), cols)

    colgroup = ""
    if widths:
        colgroup = "<colgroup>" + "".join(f"<col style='width:{escape(part)}'>" for part in widths) + "</colgroup>"

    thead = ""
    if headers:
        if len(headers) < cols:
            headers.extend([""] * (cols - len(headers)))
        thead_cells = []
        for col_index, text in enumerate(headers[:cols]):
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
        first_label = row_labels[row_index] if row_index < len(row_labels) else ""
        source_row = cells_matrix[row_index] if row_index < len(cells_matrix) else []
        source_cursor = 0
        col_index = 0
        cells = []

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

            if source_text:
                cell_content = render_solution_marked_cell_text(source_text, include_solutions)
            elif col_index == 0 and first_label and colspan == 1:
                cell_content = escape(first_label)
            else:
                cell_content = ""

            is_row_label_cell = col_index == 0 and first_label and colspan == 1
            css_class = " class='table-row-label'" if is_row_label_cell else ""
            span_attrs = ""
            style_attr = ""
            tag_name = "td"
            scope_attr = ""
            if colspan > 1:
                span_attrs += f" colspan='{colspan}'"
            if rowspan > 1:
                span_attrs += f" rowspan='{rowspan}'"

            in_header_columns = (
                header_columns > 0
                and col_index < header_columns
                and (col_index + colspan) <= header_columns
            )
            if in_header_columns:
                tag_name = "th"
                scope_attr = " scope='row'"

            if column_alignments and not is_row_label_cell:
                style_attr = f" style='text-align:{escape(column_alignments[col_index])}'"

            cells.append(
                f"<{tag_name}{css_class}{span_attrs}{scope_attr}{style_attr}>{cell_content}</{tag_name}>"
            )

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

def _render_answer_block(block_type, options=None, content=None, include_solutions=False):
    """Rendert dedizierte Antwort-Blocktypen (lines/grid/geometry/...)."""
    if isinstance(block_type, dict) and isinstance(options, str):
        # Legacy helper-Aufruf aus Unit-Tests: _render_answer_block(options, content, ...)
        legacy_options = block_type
        block_type = legacy_options.get("type", "")
        content = options
        options = legacy_options

    options = options or {}
    content = content or ""
    normalized_block_type = (block_type or "").strip().lower()
    if not normalized_block_type:
        return ""

    if normalized_block_type == "mc":
        return _render_multiple_choice_answer(options, content, include_solutions)

    if normalized_block_type == "cloze":
        md = _new_markdown_converter()
        return _render_cloze_answer(md, options, content, include_solutions)

    if normalized_block_type == "table":
        return _render_table_answer(options, content, include_solutions)

    if normalized_block_type == "matching":
        return render_matching_answer(options, content, include_solutions)

    if normalized_block_type == "wordsearch":
        return render_wordsearch_answer(options, content, include_solutions)

    if normalized_block_type == "lines":
        base_rows = max(1, _safe_int(options.get("rows", 3), 3))
        line_pitch = _parse_css_size(options.get("height"), "")
        lines_style_attr = (
            f" style='--answer-line-pitch:{escape(line_pitch)}'"
            if line_pitch
            else ""
        )

        if include_solutions:
            solution_rows_html, _solution_visible_rows = render_answer_line_rows_html_for_mode(
                content,
                include_solutions=True,
                default_show="both",
                highlight_solution_segments=True,
            )
            if solution_rows_html:
                solution_visible_rows = count_visible_answer_lines(
                    content,
                    include_solutions=True,
                    default_show="both",
                )
                solution_rows = max(
                    1,
                    max(base_rows, solution_visible_rows),
                )
                lines = "".join(
                    "<div class='line'></div>" for _ in range(solution_rows)
                )
                return (
                    f"<div class='answer lines answer-overlay-container'{lines_style_attr}>"
                    f"{lines}<div class='answer-overlay-text lines-overlay-text'>"
                    f"<div class='answer-solution-text lines-row-stack'>{solution_rows_html}</div>"
                    "</div>"
                    "</div>"
                )
            return ""

        worksheet_visible_rows = count_visible_answer_lines(
            content,
            include_solutions=False,
            default_show="both",
        )
        worksheet_rows = max(base_rows, worksheet_visible_rows)
        lines = "".join("<div class='line'></div>" for _ in range(worksheet_rows))

        worksheet_rows_html, _worksheet_visible_rows = render_answer_line_rows_html_for_mode(
            content,
            include_solutions=False,
            default_show="both",
            highlight_solution_segments=True,
        )
        if worksheet_rows_html:
            return (
                f"<div class='answer lines answer-overlay-container'{lines_style_attr}>"
                f"{lines}<div class='answer-overlay-text lines-overlay-text'>"
                f"<div class='answer-solution-text lines-row-stack'>{worksheet_rows_html}</div>"
                "</div>"
                "</div>"
            )

        return f"<div class='answer lines'{lines_style_attr}>{lines}</div>"

    if normalized_block_type == "grid":
        return render_grid_answer(
            options, content, include_solutions, _render_answer_solution_text
        )

    if normalized_block_type == "geometry":
        return render_geometry_answer(
            options, content, include_solutions, _render_answer_solution_text
        )

    if normalized_block_type == "numberline":
        return render_number_line_answer(options, content, include_solutions, _render_answer_solution_text)

    if normalized_block_type == "dots":
        return render_dots_answer(options, content, include_solutions, _render_answer_solution_text)

    if normalized_block_type == "space":
        height = options.get("height", "3cm")
        base_html = f"<div class='answer space' style='height:{height}'></div>"

        if include_solutions:
            solution_text = _render_answer_solution_text(
                content,
                include_solutions=True,
            )
            if not solution_text:
                return ""
            return _wrap_answer_with_solution(base_html, solution_text)

        worksheet_text = _render_answer_solution_text(
            content,
            include_solutions=False,
        )
        if worksheet_text:
            return _wrap_answer_with_solution(base_html, worksheet_text)

        return base_html

    return ""
