"""Task and generic block rendering functions."""

from __future__ import annotations

from .blatt_kern_shared import (
    HELP_BLOCK_TYPES,
    _new_markdown_converter,
    _option_is_enabled,
    get_task_action_info,
    get_task_hint_info,
    get_work_info,
    normalize_document_mode,
    normalize_markdown,
    should_render_block,
)
from .answer_line_markers import filter_answer_content_for_mode
from .blatt_kern_answer_table import _render_answer_block


ANSWER_BLOCK_TYPES = {
    "lines",
    "grid",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
}


def render_block(
    block_type,
    options,
    content,
    include_solutions=False,
    document_mode="ws",
):
    """Rendert einen einzelnen Blocktyp nach HTML."""
    if not should_render_block(block_type, options, include_solutions):
        return ""

    md = _new_markdown_converter()
    normalized_content = normalize_markdown(content)

    if block_type == "raw":
        return md.convert(normalized_content)

    if block_type == "material":
        return _render_material_block(md, options, normalized_content)

    if block_type == "info":
        info_type = options.get("type", "default")
        return f"<div class='info {info_type}'>{md.convert(normalized_content)}</div>"

    if block_type == "task":
        return _render_task_block(
            md,
            options,
            normalized_content,
            include_solutions=include_solutions,
            document_mode=document_mode,
        )

    if block_type == "subtask":
        parent_work_info = get_work_info(options.get("_parent_work", "single"))
        parent_action_info = get_task_action_info(options.get("_parent_action"))

        try:
            subtask_index = int(options.get("_subtask_index", 0))
        except ValueError:
            subtask_index = 0

        try:
            total_subtasks = int(options.get("_subtask_total", 1))
        except ValueError:
            total_subtasks = 1

        return _render_subtask_block(
            md,
            subtask_index,
            total_subtasks,
            options,
            normalized_content,
            parent_work_info,
            parent_action_info,
            document_mode=document_mode,
            include_solutions=include_solutions,
        )

    if block_type == "solution":
        show_label = _option_is_enabled(options.get("label"), default=True)
        label_html = "<div class='solution-label'>Lösung</div>" if show_label else ""
        return (
            f"<div class='solution'>{label_html}{md.convert(normalized_content)}</div>"
        )

    if block_type in ANSWER_BLOCK_TYPES:
        return _render_answer_block(
            block_type,
            options,
            normalized_content,
            include_solutions,
        )

    if block_type in HELP_BLOCK_TYPES:
        return ""

    return ""


def _render_material_block(md, options, normalized_content):
    """Rendert einen Material-Block inklusive optionalem Titel."""
    title = options.get("title")
    html = "<div class='material'>"
    if title:
        html += f"<h3>{title}</h3>"
    html += md.convert(normalized_content)
    html += "</div>"
    return html


def _render_symbol_span(symbol_info):
    """Rendert ein Symbol-Tag für Aufgabenheader."""
    if not symbol_info:
        return ""
    symbol, label, css_class = symbol_info
    return f"<span class='task-work-symbol {css_class}' title='{label}'>{symbol}</span>"


def _should_show_work_hints(document_mode):
    return normalize_document_mode(document_mode, default="ws") != "test"


def _render_subtask_block(
    md,
    subtask_index,
    total_subtasks,
    options,
    content,
    parent_work_info,
    parent_action_info,
    document_mode,
    include_solutions,
):
    """Rendert eine einzelne Teilaufgabe innerhalb eines Task-Blocks."""
    subtask_work_info = None
    subtask_action_info = None

    if options.get("work") is not None:
        candidate_work_info = get_work_info(options.get("work"))
        if candidate_work_info != parent_work_info:
            subtask_work_info = candidate_work_info

    if options.get("action") is not None:
        candidate_action_info = get_task_action_info(options.get("action"))
        if candidate_action_info and candidate_action_info != parent_action_info:
            subtask_action_info = candidate_action_info

    help_reference_text = (options.get("_help_reference_text") or "").strip()

    prefix_html = ""
    if total_subtasks > 1:
        prefix_html = (
            f"<span class='subtask-prefix'>{chr(ord('a') + subtask_index)}.</span>"
        )

    symbols_html = ""
    if subtask_action_info or subtask_work_info:
        symbols = _render_symbol_span(subtask_action_info)
        if _should_show_work_hints(document_mode):
            symbols += _render_symbol_span(subtask_work_info)
        if symbols:
            symbols_html = f"<span class='subtask-symbols'>{symbols}</span>"

    filtered_content = filter_answer_content_for_mode(
        content,
        include_solutions=include_solutions,
        default_show="both",
    )
    body_html = md.convert(normalize_markdown(filtered_content)) if filtered_content.strip() else ""
    help_reference_html = ""
    if help_reference_text:
        help_reference_html = (
            f"<span class='task-help-reference subtask-help-reference'>{help_reference_text}</span>"
        )

    return (
        f"<div class='subtask'>{prefix_html}{symbols_html}<div class='subtask-content'>{body_html}</div>"
        f"{help_reference_html}</div>"
    )


def _render_task_content(
    md,
    content,
    include_solutions,
    task_work_info,
    task_action_info,
):
    """Rendert den Task-Text als normales Markdown."""
    del task_work_info, task_action_info
    filtered_content = filter_answer_content_for_mode(
        content,
        include_solutions=include_solutions,
        default_show="both",
    )
    return md.convert(normalize_markdown(filtered_content))


def _render_task_block(
    md,
    options,
    normalized_content,
    include_solutions,
    document_mode,
):
    """Rendert Aufgabenkopf und Aufgabeninhalt."""
    task_id = options.get("_auto_number")
    points = options.get("points")
    task_work_info = get_work_info(options.get("work", "single"))
    work_icon, work_label, work_css_class = task_work_info
    task_action_info = get_task_action_info(options.get("action"))
    task_hint_info = get_task_hint_info(options.get("hint"))
    help_reference_text = (options.get("_help_reference_text") or "").strip()

    header = "<div class='task-header'>"
    header += "<div class='task-header-left'>"
    header += _render_symbol_span(task_action_info)
    header += _render_symbol_span(task_hint_info)
    if options.get("_show_task_label"):
        task_label = "Aufgabe"
        if task_id:
            task_label = f"Aufgabe {task_id}"
        header += f"<span class='task-id'>{task_label}</span>"
    if _should_show_work_hints(document_mode):
        header += f"<span class='task-work-symbol {work_css_class}' title='{work_label}'>{work_icon}</span>"
        header += f"<span class='task-work-hint'>- {work_label}</span>"
    header += "</div>"

    header_right_parts = []
    if help_reference_text:
        header_right_parts.append(
            f"<span class='task-help-reference'>{help_reference_text}</span>"
        )
    if points:
        header_right_parts.append(f"<span class='task-points'>{points} P</span>")
    if header_right_parts:
        header += f"<div class='task-header-right'>{''.join(header_right_parts)}</div>"

    header += "</div>"
    task_body = _render_task_content(
        md,
        normalized_content,
        include_solutions=include_solutions,
        task_work_info=task_work_info,
        task_action_info=task_action_info,
    )
    return f"<div class='task'>{header}{task_body}</div>"
