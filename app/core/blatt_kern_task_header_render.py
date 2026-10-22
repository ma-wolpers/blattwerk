"""Rendering von Aufgabenkopf, Aufgabeninhalt und Teilaufgaben (`task`/`subtask`).

Aus `blatt_kern_task_render.py` ausgelagert, damit der Block-Dispatcher
unter der 300-Zeilen-Grenze bleibt. Verhalten unverändert; aufgerufen
ausschließlich aus `blatt_kern_task_render._render_block_body`.
"""

from __future__ import annotations

from html import escape

from .blatt_kern_shared import (
    convert_markdown_with_math,
    get_task_action_info,
    get_task_hint_info,
    get_work_info,
)
from .answer_line_markers import filter_answer_content_for_mode
from .document_type_registry import shows_work_hints
from .points_model import points_badge


def _render_symbol_span(symbol_info):
    """Rendert ein Symbol-Tag für Aufgabenheader."""
    if not symbol_info:
        return ""
    symbol, label, css_class = symbol_info
    return f"<span class='task-work-symbol {css_class}' title='{label}'>{symbol}</span>"


def _should_show_work_hints(document_type):
    """Ob der Dokumenttyp Arbeitsform-Symbole zeigt (Registry-Capability `work_hints`)."""
    return shows_work_hints(document_type)


def _render_subtask_block(
    md,
    subtask_index,
    total_subtasks,
    options,
    content,
    parent_work_info,
    parent_action_info,
    document_type,
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
    time_minutes = (options.get("time") or "").strip()
    subtask_points = points_badge(options)

    prefix_html = ""
    if total_subtasks > 1:
        prefix_html = (
            f"<span class='subtask-prefix'>{chr(ord('a') + subtask_index)}.</span>"
        )

    symbols_html = ""
    if subtask_action_info or subtask_work_info:
        symbols = _render_symbol_span(subtask_action_info)
        if _should_show_work_hints(document_type):
            symbols += _render_symbol_span(subtask_work_info)
        if symbols:
            symbols_html = f"<span class='subtask-symbols'>{symbols}</span>"

    filtered_content = filter_answer_content_for_mode(
        content,
        include_solutions=include_solutions,
        default_show="both",
    )
    body_html = convert_markdown_with_math(md, filtered_content) if filtered_content.strip() else ""
    subtask_meta_parts = []
    if help_reference_text:
        subtask_meta_parts.append(
            f"<span class='task-help-reference subtask-help-reference'>{help_reference_text}</span>"
        )
    if subtask_points:
        subtask_meta_parts.append(f"<span class='task-points subtask-points'>{escape(subtask_points)}</span>")
    if time_minutes:
        subtask_meta_parts.append(
            f"<span class='subtask-time'>{time_minutes} min</span>"
        )

    subtask_meta_html = ""
    if subtask_meta_parts:
        subtask_meta_html = f"<span class='subtask-meta'>{''.join(subtask_meta_parts)}</span>"

    return (
        f"<div class='subtask'>{prefix_html}{symbols_html}<div class='subtask-content'>{body_html}</div>"
        f"{subtask_meta_html}</div>"
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
    return convert_markdown_with_math(md, filtered_content)


def _render_task_block(
    md,
    options,
    normalized_content,
    include_solutions,
    document_type,
):
    """Rendert Aufgabenkopf und Aufgabeninhalt.

    Die Aufgabensymbole (Operator, Hinweis, Arbeitsform) stehen NICHT im
    Kopf, sondern in einem eigenen `.task-margin-icons`-Block, den das CSS
    in die linke Randspalte schiebt. So beginnt das Label "Aufgabe N"
    unabhängig von gesetzten `action=`/`hint=`-Optionen immer an derselben
    x-Position wie alle anderen Seitenelemente. Der frühere Text neben dem
    Arbeitsform-Icon ("- Einzelarbeit") entfällt (kein Platz in der Spalte);
    die Bezeichnung bleibt als `title`-Attribut des Icons erhalten.
    """
    task_id = options.get("_auto_number")
    points = points_badge(options)
    time_minutes = (options.get("time") or "").strip()
    task_work_info = get_work_info(options.get("work", "single"))
    task_action_info = get_task_action_info(options.get("action"))
    task_hint_info = get_task_hint_info(options.get("hint"))
    help_reference_text = (options.get("_help_reference_text") or "").strip()
    task_title = (options.get("title") or "").strip()

    margin_icons = _render_symbol_span(task_action_info)
    margin_icons += _render_symbol_span(task_hint_info)
    if _should_show_work_hints(document_type):
        margin_icons += _render_symbol_span(task_work_info)
    margin_icons_html = (
        f"<div class='task-margin-icons'>{margin_icons}</div>" if margin_icons else ""
    )

    header = "<div class='task-header'>"
    header += "<div class='task-header-left'>"
    if options.get("_show_task_label"):
        task_label = "Aufgabe"
        if task_id:
            task_label = f"Aufgabe {task_id}"
        if task_title:
            task_label = f"{task_label} - {task_title}"
        header += f"<span class='task-id'>{escape(task_label)}</span>"
    header += "</div>"

    header_right_parts = []
    if help_reference_text:
        header_right_parts.append(
            f"<span class='task-help-reference'>{help_reference_text}</span>"
        )
    if points:
        header_right_parts.append(f"<span class='task-points'>{escape(points)}</span>")
    if time_minutes:
        header_right_parts.append(f"<span class='task-time'>{time_minutes} min</span>")
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
    return f"<div class='task'>{margin_icons_html}{header}{task_body}</div>"
