"""Layout estimation, columns rendering, and worksheet HTML document rendering."""

from __future__ import annotations

import re
from html import escape

from .answer_special import estimate_matching_weight, estimate_wordsearch_weight
from ..styles.blatt_styles import build_stylesheet, resolve_printable_width_cm
from .blatt_kern_shared import (
    _safe_int,
    annotate_task_help_references,
    annotate_standalone_subtasks,
    assign_task_numbers,
    format_meta_line,
    get_copyright_text,
    get_current_school_year_label,
    is_hole_punch_layout_enabled,
    normalize_document_mode,
    should_render_block,
    split_sections,
)
from .blatt_kern_task_render import render_block


def _with_runtime_layout_options(options, printable_width_cm):
    """Attach render-time layout context for answer blocks."""
    merged = dict(options or {})
    merged["_printable_width_cm"] = float(printable_width_cm)
    return merged


def parse_columns_template(options, fallback_count):
    """Parst optionale Spaltenbreitenangaben in ein CSS-Grid-Template."""
    template_raw = options.get("widths") or options.get("ratio")
    if not template_raw:
        return None, fallback_count

    normalized = template_raw.replace(":", " ").replace(",", " ")
    raw_parts = [part for part in normalized.split() if part.strip()]
    if len(raw_parts) < 2:
        return None, fallback_count

    css_parts = []
    for part in raw_parts:
        value = part.strip()
        if re.fullmatch(r"\d+(\.\d+)?", value):
            css_parts.append(f"{value}fr")
            continue

        if re.fullmatch(r"\d+(\.\d+)?(fr|%|px|cm|mm|em|rem)", value):
            css_parts.append(value)

    if len(css_parts) < 2:
        return None, fallback_count

    return " ".join(css_parts), len(css_parts)


def parse_columns_gap(options):
    """Parst optionalen Spaltenabstand (`gap`) als CSS-Laengenwert."""
    gap_raw = (options or {}).get("gap")
    if not gap_raw:
        return None

    value = str(gap_raw).strip()
    if re.fullmatch(r"\d+(\.\d+)?(px|pt|cm|mm|em|rem|%)", value):
        return value

    return None


def parse_height_cm(height_value, default_cm=4.0):
    """Extrahiert Zentimeterwerte aus Strings wie `4cm`."""
    if not height_value:
        return default_cm

    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*cm\s*", str(height_value), flags=re.IGNORECASE
    )
    if match:
        return float(match.group(1))
    return default_cm


def estimate_block_weight(
    block_type,
    options,
    content,
    include_solutions,
    document_mode="worksheet",
):
    """Schätzt den Platzbedarf eines Blocks für automatische Spaltenbreiten."""
    if not should_render_block(
        block_type,
        options,
        include_solutions,
        document_mode=document_mode,
    ):
        return 0.0

    cleaned = re.sub(r"[`*_#>\-\|\[\]\(\)]", " ", content or "")
    text_length = max(0, len(cleaned.strip()))
    if block_type == "raw" and text_length == 0:
        return 0.0

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    longest_line = max((len(line) for line in lines), default=0)
    text_complexity = (text_length / 120.0) + (longest_line / 55.0)

    if block_type in {"material", "task", "info", "raw", "solution"}:
        type_factor = {
            "material": 1.45,
            "info": 1.35,
            "raw": 1.10,
            "solution": 1.05,
            "task": 0.45,
        }.get(block_type, 1.0)
        base = 0.55
        if block_type == "task":
            base = 0.25
        return base + (text_complexity * type_factor)

    if block_type in {
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
    }:
        if block_type == "mc":
            base = 1.0 + (text_length / 140.0)
            return min(4.2, max(1.0, base))

        if block_type == "cloze":
            gap_count = len(re.findall(r"\{\{\s*[^{}]+\s*\}\}", content or ""))
            base = 1.0 + (gap_count * 0.45) + (text_length / 240.0)
            return min(4.8, max(1.0, base))

        if block_type == "matching":
            return estimate_matching_weight(text_length, include_solutions)

        if block_type == "wordsearch":
            return estimate_wordsearch_weight(options, content)

        if include_solutions:
            if text_length == 0:
                return 0.0

            if block_type == "lines":
                rows = max(1, _safe_int(options.get("rows", 3), 3))
                return max(1.0, rows * 0.7)
            if block_type == "grid":
                rows = max(1, _safe_int(options.get("rows", 5), 5))
                return max(1.4, rows * 0.85 + (text_length / 260.0))
            if block_type == "geometry":
                rows = max(1, _safe_int(options.get("rows", 5), 5))
                cols = _safe_int(options.get("cols", 20), 20) if options.get("cols") else 20
                return max(1.6, (rows * cols) / 52.0 + (text_length / 320.0))
            if block_type == "dots":
                return max(
                    1.2,
                    parse_height_cm(options.get("height", "4cm")) * 0.9
                    + (text_length / 240.0),
                )
            if block_type == "space":
                return max(
                    1.2,
                    parse_height_cm(options.get("height", "3cm")) * 0.85
                    + (text_length / 240.0),
                )
            if block_type == "numberline":
                return max(
                    1.0,
                    parse_height_cm(options.get("height", "2.7cm")) * 0.9
                    + (text_length / 260.0),
                )

            return max(1.0, text_length / 180.0)

        if block_type == "lines":
            return max(0.8, _safe_int(options.get("rows", 3), 3) * 0.7)
        if block_type == "grid":
            rows = _safe_int(options.get("rows", 5), 5)
            cols = _safe_int(options.get("cols", 20), 20) if options.get("cols") else 20
            return max(1.2, (rows * cols) / 55.0)
        if block_type == "geometry":
            rows = _safe_int(options.get("rows", 5), 5)
            cols = _safe_int(options.get("cols", 20), 20) if options.get("cols") else 20
            return max(1.4, (rows * cols) / 48.0)
        if block_type == "dots":
            return max(1.0, parse_height_cm(options.get("height", "4cm")) * 1.1)
        if block_type == "space":
            return max(1.0, parse_height_cm(options.get("height", "3cm")) * 1.0)
        if block_type == "numberline":
            return max(0.9, parse_height_cm(options.get("height", "2.7cm")) * 0.85)

    return max(0.6, text_length / 180.0)


def auto_columns_template(columns_blocks, include_solutions, document_mode="worksheet"):
    """Erzeugt ein Verhältnis-Template basierend auf geschätzten Spaltengewichten."""
    weights = []
    for column_blocks in columns_blocks:
        column_weight = 0.0
        for block_type, options, content in column_blocks:
            column_weight += estimate_block_weight(
                block_type,
                options,
                content,
                include_solutions,
                document_mode=document_mode,
            )
        weights.append(max(0.8, min(column_weight, 7.0)))

    if not weights:
        return None

    return " ".join(f"{weight:.2f}fr" for weight in weights)


def render_columns_container(
    columns_blocks,
    options,
    include_solutions,
    document_mode="ws",
    printable_width_cm=18.0,
):
    """Rendert einen `columns`-Container inklusive automatischer Breitenlogik."""
    if not columns_blocks:
        return ""

    columns_count = len(columns_blocks)
    explicit_template, explicit_count = parse_columns_template(options, columns_count)

    if explicit_template:
        columns_count = max(2, min(explicit_count, 6))
        columns_blocks = columns_blocks[:columns_count]
        template = explicit_template
    else:
        template = auto_columns_template(
            columns_blocks,
            include_solutions,
            document_mode=document_mode,
        )

    if not template:
        template = " ".join("1fr" for _ in columns_blocks)

    column_gap = parse_columns_gap(options)

    column_html = []
    for column_blocks in columns_blocks:
        rendered_parts = []
        for block_type, block_options, content in column_blocks:
            runtime_options = _with_runtime_layout_options(
                block_options,
                printable_width_cm,
            )
            rendered = render_block(
                block_type,
                runtime_options,
                content,
                include_solutions=include_solutions,
                document_mode=document_mode,
            )
            if rendered:
                rendered_parts.append(rendered)
        column_html.append(f"<div class='column'>{''.join(rendered_parts)}</div>")

    style_parts = [f"--col-template:{template}"]
    if column_gap:
        style_parts.append(f"--col-gap:{column_gap}")
    inline_style = ";".join(style_parts)

    return f"<div class='columns columns-custom' style='{escape(inline_style)}'>{''.join(column_html)}</div>"


def render_body_with_columns(
    blocks,
    include_solutions,
    document_mode="ws",
    printable_width_cm=18.0,
):
    """Rendert den Body und behandelt `columns`/`nextcol`/`endcolumns` Zustände."""
    html_parts = []
    in_columns = False
    columns_options = {}
    columns_blocks = []
    current_column_index = 0

    for block_type, options, content in blocks:
        if block_type == "columns" and not in_columns:
            # Start eines Spaltenkontexts; nachfolgende Blöcke gehen in Spaltenpuffer.
            in_columns = True
            columns_options = dict(options)

            try:
                columns_count = int(columns_options.get("cols", 2))
            except ValueError:
                columns_count = 2

            columns_count = max(2, min(columns_count, 6))
            columns_blocks = [[] for _ in range(columns_count)]
            current_column_index = 0
            continue

        if block_type == "nextcol" and in_columns:
            # Expliziter Wechsel zur nächsten Spalte.
            if current_column_index + 1 >= len(columns_blocks):
                if len(columns_blocks) < 6:
                    columns_blocks.append([])
                    current_column_index += 1
            else:
                current_column_index += 1
            continue

        if block_type == "endcolumns" and in_columns:
            # Spaltenkontext abschließen, normalisieren und als einen Container rendern.
            columns_blocks = [col for col in columns_blocks if col is not None]
            columns_blocks = [
                col for col in columns_blocks if col or len(columns_blocks) <= 2
            ]
            if len(columns_blocks) < 2:
                columns_blocks.append([])
            html_parts.append(
                render_columns_container(
                    columns_blocks,
                    columns_options,
                    include_solutions,
                    document_mode=document_mode,
                    printable_width_cm=printable_width_cm,
                )
            )
            in_columns = False
            columns_options = {}
            columns_blocks = []
            current_column_index = 0
            continue

        if in_columns:
            if not columns_blocks:
                columns_blocks = [[]]
            columns_blocks[current_column_index].append((block_type, options, content))
            continue

        runtime_options = _with_runtime_layout_options(
            options,
            printable_width_cm,
        )
        rendered = render_block(
            block_type,
            runtime_options,
            content,
            include_solutions=include_solutions,
            document_mode=document_mode,
        )
        if rendered:
            html_parts.append(rendered)

    if in_columns:
        html_parts.append(
            render_columns_container(
                columns_blocks,
                columns_options,
                include_solutions,
                document_mode=document_mode,
                printable_width_cm=printable_width_cm,
            )
        )

    return "".join(html_parts)


def _is_layout_control_block(block_type):
    return block_type in {"pagebreak", "framebreak", "sectionmark"}


def _build_presentation_slides(
    blocks,
    include_solutions,
    document_mode,
    printable_width_cm,
):
    """Build slide payloads from block stream, including frame-duplication markers."""
    slides = []
    current_blocks = []
    current_section = ""
    logical_slide_number = 1

    def _flush_slide(clear_blocks=True):
        nonlocal logical_slide_number
        if not current_blocks:
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
            }
        )
        if clear_blocks:
            current_blocks.clear()
            logical_slide_number += 1

    for block_type, options, content in blocks:
        if block_type == "sectionmark":
            title = str((options or {}).get("title") or "").strip()
            if title:
                current_section = title
            continue

        if block_type == "pagebreak":
            _flush_slide(clear_blocks=True)
            continue

        if block_type == "framebreak":
            _flush_slide(clear_blocks=False)
            continue

        current_blocks.append((block_type, options, content))

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
        mini_header_html = ""
        if show_mini_header:
            mini_header_html = (
                "<div class='presentation-mini-header'>"
                f"<span class='presentation-mini-title'>{title_text}</span>"
                f"<span class='presentation-mini-meta'>{meta_line}</span>"
                "</div>"
            )

        section_footer_html = ""
        if show_section_footer and section_names:
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

        slide_counter_html = (
            "<div class='presentation-slide-counter'>"
            f"Folie {logical_slide_number}/{logical_slide_total}"
            "</div>"
        )
        slide_html_parts.append(
            "<section class='ab-slide'>"
            f"{mini_header_html}"
            f"<div class='ab-slide-body'>{slide.get('body', '')}</div>"
            f"{section_footer_html}"
            f"{slide_counter_html}"
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
    tex: {{
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true,
    }},
    svg: {{
        fontCache: 'none'
    }}
}};
</script>
<script defer src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js\"></script>
<style>
{stylesheet}
</style>
</head>
<body class=\"presentation-document\">
{''.join(slide_html_parts)}
</body>
</html>
"""


def render_html(
    meta,
    blocks,
    include_solutions=False,
    page_format="a4_portrait",
    print_profile="standard",
    color_profile="indigo",
    font_profile="segoe",
    font_size_profile="normal",
    black_screen_mode="none",
    presentation_section_separator="dot",
    presentation_hide_future_sections=False,
):
    """Baut das vollständige HTML-Dokument inklusive Styles und Header/Footer."""
    document_mode = normalize_document_mode(
        (meta or {}).get("mode"),
        default="worksheet",
    )

    if document_mode == "presentation":
        presentation_format = str(page_format or "").strip()
        if not presentation_format or presentation_format not in {
            "presentation_16_9",
            "presentation_16_10",
            "presentation_4_3",
        }:
            presentation_format = str(
                (meta or {}).get("presentation_layout")
                or (meta or {}).get("presentation_format")
                or "presentation_16_9"
            ).strip()
        return _render_presentation_html(
            meta,
            blocks,
            include_solutions=False,
            page_format=presentation_format,
            print_profile=print_profile,
            color_profile=color_profile,
            font_profile=font_profile,
            font_size_profile=font_size_profile,
            black_screen_mode=black_screen_mode,
            presentation_section_separator=presentation_section_separator,
            presentation_hide_future_sections=presentation_hide_future_sections,
        )

    numbered_blocks = assign_task_numbers(blocks)
    enriched_blocks = annotate_standalone_subtasks(numbered_blocks)
    enriched_blocks = annotate_task_help_references(
        enriched_blocks,
        include_solutions=include_solutions,
        help_tag=(meta or {}).get("tag"),
        document_mode=document_mode,
    )
    hole_punch_enabled = is_hole_punch_layout_enabled(meta)
    printable_width_cm = resolve_printable_width_cm(
        page_format,
        hole_punch_enabled=hole_punch_enabled,
    )
    body = render_body_with_columns(
        enriched_blocks,
        include_solutions=include_solutions,
        document_mode=document_mode,
        printable_width_cm=printable_width_cm,
    )
    sectioned_body = split_sections(body)
    meta_line = format_meta_line(meta)
    school_year_label = escape(get_current_school_year_label())
    right_header_label = "Lösungsversion" if include_solutions else school_year_label
    right_header_html = right_header_label
    if include_solutions:
        right_header_html = (
            "<span class='solution-version-inline'>Lösungsversion</span>"
        )

    student_header = ""
    if meta.get("show_student_header", False):
        student_header = """
        <div class="student-header">
            <div class="student-field">
                <span class="student-label">Name</span>
                <span class="student-line"></span>
            </div>
            <div class="student-field">
                <span class="student-label">Lerngruppe</span>
                <span class="student-line"></span>
            </div>
            <div class="student-field">
                <span class="student-label">Datum</span>
                <span class="student-line"></span>
            </div>
        </div>
        """

    document_header = ""
    if meta.get("show_document_header", True):
        document_header = f"""
<div class="document-header">
<div class="header-meta">
{meta_line}
</div>
<div class="header-right">
<div class="header-school-year">{right_header_html}</div>
</div>
</div>
"""

    stylesheet = build_stylesheet(
        page_format,
        print_profile,
        hole_punch_enabled=hole_punch_enabled,
        color_profile=color_profile,
        font_profile=font_profile,
        font_size_profile=font_size_profile,
        document_mode=document_mode,
    )

    copyright_text = get_copyright_text(meta)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{meta.get("Titel", "Arbeitsblatt")}</title>
<script>
window.MathJax = {{
    tex: {{
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true,
    }},
    svg: {{
        fontCache: 'none'
    }}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<style>
{stylesheet}
</style>
</head>
<body>

{document_header}

{student_header}

<h1>{meta.get("Titel", "")}</h1>

{sectioned_body}

<!-- Footer wird nach PDF-Erzeugung einheitlich per PyMuPDF gesetzt. -->

</body>
</html>
"""
