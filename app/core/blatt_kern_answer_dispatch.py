"""Blocktyp-übergreifender Dispatcher für Antwort-Blöcke (`_render_answer_block`).

Ausgelagert aus `blatt_kern_answer_table.py`, damit jene Datei auf die
Tabellen-spezifische Logik begrenzt bleibt (Datei-Größenlimit). Importiert
`_render_table_answer`/`_wrap_answer_with_solution`/`_parse_css_size` von dort
-- keine Rückimporte, also keine zyklische Abhängigkeit.
"""

from __future__ import annotations

from html import escape

from .answer_special import (
    render_checkgrid_answer,
    render_crossword_answer,
    render_matching_answer,
    render_ordering_answer,
    render_wordsearch_answer,
)
from .blatt_kern_shared import _new_markdown_converter, _safe_int
from .answer_grid_plot import (
    render_dots_answer,
    render_geometry_answer,
    render_grid_answer,
)
from .answer_numberline import render_number_line_answer
from .answer_line_markers import (
    count_visible_answer_lines,
    render_answer_line_rows_html_for_mode,
)
from .blatt_kern_answer_choice import (
    _render_answer_solution_text,
    _render_cloze_answer,
    _render_multiple_choice_answer,
)
from .blatt_kern_answer_table import (
    _parse_css_size,
    _render_table_answer,
    _wrap_answer_with_solution,
)


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

    if normalized_block_type == "crossword":
        return render_crossword_answer(options, content, include_solutions)

    if normalized_block_type == "ordering":
        return render_ordering_answer(options, content, include_solutions)

    if normalized_block_type == "checkgrid":
        return render_checkgrid_answer(options, content, include_solutions)

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
