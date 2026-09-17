"""Baut Präsentations-Folien und das vollständige Präsentations-HTML-Dokument.

Dritte Schicht der `blatt_kern_layout_*`-Modulfamilie (siehe
`blatt_kern_layout_render.py`s Modul-Docstring fuer die Gesamtuebersicht) --
baut auf `blatt_kern_layout_columns.py` auf (Body-Rendering pro Folie), wird
selbst nur von `blatt_kern_layout_render.py::render_html` importiert.
"""

from __future__ import annotations

from html import escape

from ..styles.blatt_styles import build_stylesheet, resolve_printable_width_cm
from .blatt_kern_layout_columns import render_body_with_columns
from .blatt_kern_shared import (
    annotate_standalone_subtasks,
    annotate_task_help_references,
    assign_task_numbers,
    format_meta_line,
    is_hole_punch_layout_enabled,
)


def _is_layout_control_block(block_type):
    return block_type in {"pagebreak", "framebreak", "sectionmark", "slidechromeoff"}


def _build_presentation_slides(
    blocks,
    include_solutions,
    document_mode,
    printable_width_cm,
    ignore_framebreaks=False,
):
    """Build slide payloads from block stream, including frame-duplication markers.

    `ignore_framebreaks=True` treats `-+`-Marker (framebreak) als reines
    No-Op statt eine neue, den bisherigen Inhalt behaltende Folie zu
    beginnen -- der gesamte durch `-+` verbundene Inhalt landet dann in
    einer einzigen finalen Folie. Wirkt als Eigenschaft der
    Präsentationsstruktur einheitlich für alle Ausgabeformate, da dies der
    einzige gemeinsame Punkt ist, den PDF/HTML/PNG/PPTX-Export letztlich
    durchlaufen (siehe `render_html`/`build_worksheet`).
    """
    slides = []
    current_blocks = []
    current_section = ""
    logical_slide_number = 1
    current_hide_slide_chrome = False

    def _append_slide_block(block_type, options, content):
        if (
            block_type == "raw"
            and current_blocks
            and current_blocks[-1][0] == "raw"
        ):
            prev_type, prev_options, prev_content = current_blocks[-1]
            if prev_content.endswith(("\n", "\r")):
                merged_content = f"{prev_content}{content}"
            else:
                merged_content = f"{prev_content}\n{content}"
            current_blocks[-1] = (prev_type, prev_options, merged_content)
            return

        current_blocks.append((block_type, options, content))

    def _flush_slide(clear_blocks=True):
        nonlocal logical_slide_number, current_hide_slide_chrome
        if not current_blocks:
            if clear_blocks:
                current_hide_slide_chrome = False
            return
        body_html = render_body_with_columns(
            list(current_blocks),
            include_solutions=include_solutions,
            document_mode=document_mode,
            printable_width_cm=printable_width_cm,
        )
        if not body_html.strip():
            return
        slides.append(
            {
                "section": current_section,
                "body": body_html,
                "logical_slide_number": logical_slide_number,
                "hide_slide_chrome": bool(current_hide_slide_chrome),
            }
        )
        current_hide_slide_chrome = False
        if clear_blocks:
            current_blocks.clear()
            logical_slide_number += 1

    for block_type, options, content in blocks:
        if block_type == "sectionmark":
            title = str((options or {}).get("title") or "").strip()
            if title:
                current_section = title
            continue

        if block_type == "slidechromeoff":
            current_hide_slide_chrome = True
            continue

        if block_type == "pagebreak":
            _flush_slide(clear_blocks=True)
            continue

        if block_type == "framebreak":
            if not ignore_framebreaks:
                _flush_slide(clear_blocks=False)
            continue

        _append_slide_block(block_type, options, content)

    _flush_slide(clear_blocks=True)
    return slides


def _render_presentation_html(
    meta,
    blocks,
    include_solutions,
    page_format,
    print_profile,
    color_profile,
    font_profile,
    font_size_profile,
    black_screen_mode,
    presentation_section_separator,
    presentation_hide_future_sections,
    presentation_ignore_framebreaks=False,
):
    hole_punch_enabled = is_hole_punch_layout_enabled(meta)
    printable_width_cm = resolve_printable_width_cm(
        page_format,
        hole_punch_enabled=hole_punch_enabled,
    )
    numbered_blocks = assign_task_numbers(blocks)
    enriched_blocks = annotate_standalone_subtasks(numbered_blocks)
    enriched_blocks = annotate_task_help_references(
        enriched_blocks,
        include_solutions=False,
        help_tag=(meta or {}).get("tag"),
        document_mode="presentation",
    )
    slides = _build_presentation_slides(
        enriched_blocks,
        include_solutions=include_solutions,
        document_mode="presentation",
        printable_width_cm=printable_width_cm,
        ignore_framebreaks=bool(presentation_ignore_framebreaks),
    )

    if not slides:
        slides = [{"section": "", "body": "<p>Keine Folieninhalte gefunden.</p>"}]

    section_names = []
    slide_section_indices = []
    last_section_name = ""
    active_section_index = None
    for slide in slides:
        label = str(slide.get("section") or "").strip()
        if not label:
            slide_section_indices.append(None)
            continue
        if label != last_section_name:
            section_names.append(label)
            active_section_index = len(section_names) - 1
            last_section_name = label
        slide_section_indices.append(active_section_index)

    title_text = escape(str((meta or {}).get("Titel") or "Präsentation"))
    meta_line = escape(format_meta_line(meta))
    show_mini_header = bool((meta or {}).get("presentation_show_mini_header", True))
    show_section_footer = bool(
        (meta or {}).get("presentation_show_section_footer", True)
    )
    section_separator_key = str(presentation_section_separator or "dot").strip().lower()
    if section_separator_key not in {"dot", "arrow"}:
        section_separator_key = "dot"
    section_separator_text = "·" if section_separator_key == "dot" else "->"
    hide_future_sections = bool(presentation_hide_future_sections)

    logical_slide_total = max(
        int(slide.get("logical_slide_number") or 1)
        for slide in slides
    )
    slide_html_parts = []
    black_screen_mode = str(black_screen_mode or "none").strip().lower()

    if black_screen_mode in {"before", "both"}:
        slide_html_parts.append("<section class='ab-slide ab-slide-black'></section>")

    for index, slide in enumerate(slides, start=1):
        current_section_index = slide_section_indices[index - 1]
        logical_slide_number = int(slide.get("logical_slide_number") or index)
        hide_slide_chrome = bool(slide.get("hide_slide_chrome"))
        mini_header_html = ""
        if show_mini_header and not hide_slide_chrome:
            mini_header_html = (
                "<div class='presentation-mini-header'>"
                f"<span class='presentation-mini-title'>{title_text}</span>"
                f"<span class='presentation-mini-meta'>{meta_line}</span>"
                "</div>"
            )

        section_footer_html = ""
        if show_section_footer and section_names and not hide_slide_chrome:
            visible_indices = list(range(len(section_names)))
            append_ellipsis = False
            if hide_future_sections and current_section_index is not None:
                visible_indices = [
                    section_idx
                    for section_idx in range(len(section_names))
                    if section_idx <= current_section_index
                ]
                append_ellipsis = current_section_index < (len(section_names) - 1)

            section_parts = []
            for visible_pos, section_idx in enumerate(visible_indices):
                section_name = section_names[section_idx]
                css_class = "active" if section_idx == current_section_index else ""
                section_parts.append(
                    f"<span class='presentation-section-item {css_class}'>{escape(section_name)}</span>"
                )
                has_next_visible = visible_pos < len(visible_indices) - 1
                if has_next_visible or append_ellipsis:
                    section_parts.append(
                        "<span class='presentation-section-separator' aria-hidden='true'>"
                        f"{escape(section_separator_text)}"
                        "</span>"
                    )

            if append_ellipsis:
                section_parts.append(
                    "<span class='presentation-section-item presentation-section-item-ellipsis' aria-hidden='true'>...</span>"
                )

            section_footer_html = (
                "<div class='presentation-section-footer'>"
                f"{''.join(section_parts)}"
                "</div>"
            )

        slide_counter_html = ""
        if not hide_slide_chrome:
            slide_counter_html = (
                "<div class='presentation-slide-counter'>"
                f"Folie {logical_slide_number}/{logical_slide_total}"
                "</div>"
            )
        # `data-block-type="chrome"` marks these two regions for the
        # experimental editable-PPTX export (`blatt_kern_pptx_export_editable_convert.py`,
        # `_IMAGE_ONLY_BLOCK_TYPES`) so they become one small image each
        # instead of fragmenting into a separate shape per header/footer/
        # counter `<div>`. Two regions, not one: the mini-header sits
        # *before* `.ab-slide-body` and the footer/counter sit *after* it
        # in the existing DOM order, which stays untouched here (reordering
        # them into one contiguous wrapper would risk shifting the visual
        # flex-column layout for every export, not just the experimental
        # one) -- both regions share the same "chrome" type, so the
        # extractor treats them identically even though they're two shapes.
        top_chrome_html = f"<div data-block-type='chrome'>{mini_header_html}</div>" if mini_header_html else ""
        bottom_chrome_source = f"{section_footer_html}{slide_counter_html}"
        bottom_chrome_html = (
            f"<div data-block-type='chrome'>{bottom_chrome_source}</div>" if bottom_chrome_source else ""
        )
        slide_html_parts.append(
            "<section class='ab-slide'>"
            f"{top_chrome_html}"
            f"<div class='ab-slide-body'>{slide.get('body', '')}</div>"
            f"{bottom_chrome_html}"
            "</section>"
        )

    if black_screen_mode in {"after", "both"}:
        slide_html_parts.append("<section class='ab-slide ab-slide-black'></section>")

    stylesheet = build_stylesheet(
        page_format,
        print_profile,
        hole_punch_enabled=hole_punch_enabled,
        color_profile=color_profile,
        font_profile=font_profile,
        font_size_profile=font_size_profile,
        document_mode="presentation",
    )

    return f"""<!DOCTYPE html>
<html lang=\"de\">
<head>
<meta charset=\"utf-8\">
<title>{title_text}</title>
<script>
window.MathJax = {{
    loader: {{
        load: ['[tex]/boldsymbol']
    }},
    tex: {{
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true,
        packages: {{'[+]': ['boldsymbol']}},
    }},
    svg: {{
        fontCache: 'none'
    }}
}};
</script>
<script defer src=\"https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js\" onerror=\"document.body.classList.add('mathjax-load-failed')\"></script>
<style>
{stylesheet}
</style>
</head>
<body class=\"presentation-document\">
{''.join(slide_html_parts)}
</body>
</html>
"""
