"""Block-Dispatcher: rendert einen einzelnen Block nach HTML.

Aufgabenkopf/Teilaufgaben liegen in `blatt_kern_task_header_render.py`,
die Klausurteil-Überschriften in `exam_part_render.py`.
"""

from __future__ import annotations

import re
from html import escape

from .blatt_kern_shared import (
    HELP_BLOCK_TYPES,
    _new_markdown_converter,
    _option_is_enabled,
    convert_markdown_with_math,
    get_task_action_info,
    get_work_info,
    normalize_markdown,
    should_render_block,
)
from .answer_special_mindmap import render_mindmap_block
from .answer_special_struktogramm import render_struktogramm_block
from .blatt_kern_shared_data import STRUKTOGRAMM_BLOCK_TYPES
from .answer_special_selfcheck import render_selfcheck_block
from .answer_special_writebox import render_writebox_block
from .blatt_kern_answer_dispatch import _render_answer_block
from .blatt_kern_task_header_render import _render_subtask_block, _render_task_block
from .exam_part_render import render_exam_part
from .operator_legend_blocks import OPERATOR_LEGEND_HTML_KEY, OPERATORS_BLOCK_TYPE
from .solution_display import render_solution_html
from .qrcode_block import render_qrcode_block


ANSWER_BLOCK_TYPES = {
    "lines",
    "grid",
    "geometry",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
    "crossword",
    "ordering",
    "checkgrid",
}


def _normalize_object_alignment(block_type, options):
    """Normalisiert optionale Objekt-Ausrichtung auf left/right/center/block."""
    options = options or {}

    raw_alignment = options.get("align")
    if block_type == "qrcode" and not raw_alignment:
        raw_alignment = options.get("alignment")

    normalized = str(raw_alignment or "").strip().lower()
    normalized = normalized.replace("\u00fc", "u").replace("\u00df", "ss")

    aliases = {
        "left": "left",
        "links": "left",
        "linksbundig": "left",
        "linksbuendig": "left",
        "right": "right",
        "rechts": "right",
        "rechtsbundig": "right",
        "rechtsbuendig": "right",
        "center": "center",
        "centre": "center",
        "middle": "center",
        "mitte": "center",
        "zentriert": "center",
        "justify": "block",
        "block": "block",
        "blocksatz": "block",
    }
    return aliases.get(normalized, "")


def _wrap_with_object_alignment(html, alignment):
    """Wrappt gerendertes HTML optional mit einer Objekt-Ausrichtungs-Huelle."""
    if not html or not alignment:
        return html
    return f"<div class='bw-object-align bw-object-align-{alignment}'>{html}</div>"


_ROOT_TAG_PATTERN = re.compile(r"^(\s*<[a-zA-Z][^\s>]*)")


def _tag_root_element_with_block_type(html: str, block_type: str) -> str:
    """Adds `data-block-type="{block_type}"` to `html`'s own root element, without introducing a wrapper.

    Read exclusively by the experimental editable-PPTX export
    (`blatt_kern_pptx_export_editable.py`) to find each block's DOM root
    during Playwright-driven extraction. Deliberately does NOT wrap `html`
    in a new element (e.g. `f"<div data-block-type='{block_type}'>{html}</div>"`)
    -- that would shift existing CSS child-combinator rules that assume
    render_block()'s current DOM shape (e.g. `.column > *:first-child` in
    `assets/worksheet.css`). The attribute rides on whichever element is
    already `html`'s own root, so it's inert for every other consumer
    (PDF/PNG/HTML export, print CSS): just an unused `data-*` attribute.

    No-op for empty `html` (blocks that render nothing) or content that
    doesn't start with a tag (shouldn't happen for any real block, but
    stays defensive rather than producing malformed markup).
    """

    if not html:
        return html
    match = _ROOT_TAG_PATTERN.match(html)
    if not match:
        return html
    insert_at = match.end(1)
    return f"{html[:insert_at]} data-block-type=\"{block_type}\"{html[insert_at:]}"


def render_block(
    block_type,
    options,
    content,
    include_solutions=False,
    document_type="worksheet",
):
    """Rendert einen einzelnen Blocktyp nach HTML.

    Thin wrapper around `_render_block_body()` (all the actual dispatch
    logic, unchanged) that tags the result's root element with
    `data-block-type` -- kept as a wrapper rather than threading the
    tagging into every one of `_render_block_body`'s ~15 branches/`return`
    statements, so the existing dispatch logic stays untouched and this
    stays a two-line, easily-reviewed addition.
    """

    html = _render_block_body(
        block_type, options, content, include_solutions=include_solutions, document_type=document_type
    )
    return _tag_root_element_with_block_type(html, block_type)


def _render_block_body(
    block_type,
    options,
    content,
    include_solutions=False,
    document_type="worksheet",
):
    """Rendert einen einzelnen Blocktyp nach HTML (ohne `data-block-type`-Tagging, siehe `render_block()`)."""
    if not should_render_block(
        block_type,
        options,
        include_solutions,
        document_type=document_type,
    ):
        return ""

    object_alignment = _normalize_object_alignment(block_type, options)
    md = _new_markdown_converter()
    normalized_content = normalize_markdown(content)

    if block_type == "raw":
        return _wrap_with_object_alignment(
            convert_markdown_with_math(md, normalized_content), object_alignment
        )

    if block_type == "pagebreak":
        return "<div class='ab-pagebreak' aria-hidden='true'></div>"

    if block_type == "vspacer":
        raw_height = (options or {}).get("height") or "1cm"
        height_value = escape(str(raw_height).strip() or "1cm")
        return (
            "<div class='ab-vertical-space' aria-hidden='true' "
            f"style='height:{height_value};'></div>"
        )

    if block_type == "aidsplit":
        return render_exam_part(options)

    if block_type == "evaluation":
        # Fertiges HTML aus `evaluation_table.annotate_evaluation_blocks` (braucht das ganze Dokument);
        # ohne Annotation (z. B. in Präsentationen) rendert der Block nichts.
        return str((options or {}).get("_evaluation_html") or "")

    if block_type == OPERATORS_BLOCK_TYPE:
        # Fertiges HTML aus `operator_legend_blocks.annotate_operator_blocks` (Bereich über mehrere Blöcke).
        return str((options or {}).get(OPERATOR_LEGEND_HTML_KEY) or "")

    if block_type in {"framebreak", "sectionmark", "slidechromeoff"}:
        return ""

    if block_type == "material":
        return _wrap_with_object_alignment(
            _render_material_block(md, options, normalized_content),
            object_alignment,
        )

    if block_type == "info":
        info_type = options.get("type", "default")
        return _wrap_with_object_alignment(
            f"<div class='info {info_type}'>{convert_markdown_with_math(md, normalized_content)}</div>",
            object_alignment,
        )

    if block_type == "task":
        return _wrap_with_object_alignment(
            _render_task_block(
                md,
                options,
                normalized_content,
                include_solutions=include_solutions,
                document_type=document_type,
            ),
            object_alignment,
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

        return _wrap_with_object_alignment(
            _render_subtask_block(
                md,
                subtask_index,
                total_subtasks,
                options,
                normalized_content,
                parent_work_info,
                parent_action_info,
                document_type=document_type,
                include_solutions=include_solutions,
            ),
            object_alignment,
        )

    if block_type == "solution":
        show_label = _option_is_enabled(options.get("label"), default=True)
        label_html = "<div class='solution-label'>Lösung</div>" if show_label else ""
        return _wrap_with_object_alignment(
            f"<div class='solution'>{label_html}{render_solution_html(content)}</div>",
            object_alignment,
        )

    if block_type == "qrcode":
        return _wrap_with_object_alignment(render_qrcode_block(options), object_alignment)

    if block_type == "mindmap":
        return _wrap_with_object_alignment(
            render_mindmap_block(options, normalized_content), object_alignment
        )

    if block_type in STRUKTOGRAMM_BLOCK_TYPES:
        # Roher `content`: `normalize_markdown` würde die Einrückung (= Schachtelung) verfälschen.
        return _wrap_with_object_alignment(
            render_struktogramm_block(options, content, include_solutions), object_alignment
        )

    if block_type == "selfcheck":
        return _wrap_with_object_alignment(
            render_selfcheck_block(options, normalized_content), object_alignment
        )

    if block_type == "writebox":
        return _wrap_with_object_alignment(
            render_writebox_block(options, normalized_content), object_alignment
        )

    if block_type in ANSWER_BLOCK_TYPES:
        return _wrap_with_object_alignment(
            _render_answer_block(
                block_type,
                options,
                normalized_content,
                include_solutions,
            ),
            object_alignment,
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
    html += convert_markdown_with_math(md, normalized_content)
    html += "</div>"
    return html
