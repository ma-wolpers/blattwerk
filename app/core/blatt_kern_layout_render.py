"""Baut das vollständige Arbeitsblatt-HTML-Dokument (öffentlicher Einstiegspunkt).

Oberste Schicht der `blatt_kern_layout_*`-Modulfamilie -- die Aufteilung
entstand, weil die urspruengliche `blatt_kern_layout_render.py` mit 950
Zeilen weit ueber dem projektweiten ~300-Zeilen-Limit lag (siehe
`docs/intern/DEVELOPMENT_LOG.md`). Vier Verantwortlichkeiten, jede in einem
eigenen Modul, mit einseitiger, azyklischer Abhaengigkeitskette:

- `blatt_kern_layout_estimate.py` (Platzbedarfs-Schaetzung fuer Bloecke)
- `blatt_kern_layout_columns.py` (baut auf estimate.py auf: `columns`/
  `nextcol`/`endcolumns`-Rendering, normaler Block-Body)
- `blatt_kern_layout_presentation.py` (baut auf columns.py auf: Folien +
  vollstaendiges Praesentations-HTML-Dokument)
- dieses Modul (baut auf presentation.py auf: `render_html`, der von aussen
  genutzte Arbeitsblatt/Praesentation-Einstiegspunkt)

`render_columns_container` wird hier zusaetzlich re-exportiert (unveraendert
importierbar fuer `tests/test_layout_section_breaks.py`), obwohl die
Funktion inzwischen in `blatt_kern_layout_columns.py` lebt -- derselbe
Re-Export-Stil wie z. B. `answer_special.py` fuer seine Submodule.
"""

from __future__ import annotations

from html import escape

from .operator_legend import collect_used_operators, render_operator_legend_html
from ..styles.blatt_styles import build_stylesheet, resolve_printable_height_cm, resolve_printable_width_cm
from ..styles.page_geometry import resolve_gutter_widths_cm
from .blatt_kern_shared import (
    _meta_bool_ja_nein,
    annotate_task_help_references,
    annotate_standalone_subtasks,
    assign_task_numbers,
    format_meta_line,
    get_copyright_text,
    get_current_school_year_label,
    is_hole_punch_layout_enabled,
    normalize_document_mode,
    split_sections,
)
from .blatt_kern_layout_columns import render_body_with_columns, render_columns_container
from .blatt_kern_layout_presentation import _render_presentation_html


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
    presentation_ignore_framebreaks=False,
    cache=None,
):
    """Baut das vollständige HTML-Dokument inklusive Styles und Header/Footer.

    `cache` is an optional `BlockComputationCache` opened by the application
    layer (see `app/core/block_computation_cache.py`); it is threaded down to
    every block via `_with_runtime_layout_options()` so block renderers can
    reuse a computation already performed during validation. Presentation
    documents currently render through a separate path that does not yet
    consume `cache` (out of scope until a block needing it appears there).

    Appends the Operatoren-Legende (`operator_legend.py`, the "Garage" in
    the Haus/Garage split -- this function itself stays fach-/stufen-
    neutral) only when `include_solutions=False`; the presentation branch
    above returns before this point, so Kurzentwurf/presentation documents
    never see it either. A document with no `!!...!!`-marked operator is
    an unaffected no-op (see `collect_used_operators`'s cheap guard).
    """
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
            presentation_ignore_framebreaks=presentation_ignore_framebreaks,
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
    gutter_left_cm, gutter_right_cm = resolve_gutter_widths_cm(reserve_gutters=True)
    printable_width_cm = max(
        0.5,
        resolve_printable_width_cm(page_format, hole_punch_enabled=hole_punch_enabled)
        - gutter_left_cm
        - gutter_right_cm,
    )
    printable_height_cm = resolve_printable_height_cm(
        page_format,
        hole_punch_enabled=hole_punch_enabled,
    )
    body = render_body_with_columns(
        enriched_blocks,
        include_solutions=include_solutions,
        document_mode=document_mode,
        printable_width_cm=printable_width_cm,
        printable_height_cm=printable_height_cm,
        cache=cache,
    )
    sectioned_body = split_sections(body)

    operator_legend_html = ""
    if not include_solutions:
        matched_operators, _operator_diagnostics = collect_used_operators(blocks, meta)
        operator_legend_html = render_operator_legend_html(matched_operators)

    meta_line = format_meta_line(meta)
    school_year_label = escape(get_current_school_year_label())
    right_header_label = "Lösungsversion" if include_solutions else school_year_label
    right_header_html = right_header_label
    if include_solutions:
        right_header_html = (
            "<span class='solution-version-inline'>Lösungsversion</span>"
        )

    student_header = ""
    if _meta_bool_ja_nein(meta.get("show_student_header"), default=False):
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
    if _meta_bool_ja_nein(meta.get("show_document_header"), default=True):
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
        reserve_gutters=True,
    )

    copyright_text = get_copyright_text(meta)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{meta.get("Titel", "Arbeitsblatt")}</title>
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
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js" onerror="document.body.classList.add('mathjax-load-failed')"></script>
<style>
{stylesheet}
</style>
</head>
<body>

{document_header}

{student_header}

<h1>{meta.get("Titel", "")}</h1>

{sectioned_body}

{operator_legend_html}

<!-- Footer wird nach PDF-Erzeugung einheitlich per PyMuPDF gesetzt. -->

</body>
</html>
"""
