"""Rendert `columns`/`nextcol`/`endcolumns`-Spaltenlayouts und den normalen Block-Body.

Zweite Schicht der `blatt_kern_layout_*`-Modulfamilie (siehe
`blatt_kern_layout_render.py`s Modul-Docstring fuer die Gesamtuebersicht) --
baut auf `blatt_kern_layout_estimate.py` auf (automatische Spaltenbreiten),
wird selbst von `blatt_kern_layout_presentation.py` und
`blatt_kern_layout_render.py` importiert.
"""

from __future__ import annotations

import re
from html import escape

from .blatt_kern_layout_estimate import auto_columns_template
from .blatt_kern_task_render import render_block


def _normalize_object_alignment(raw_value):
    """Normalisiert align-Werte auf left/right/center/block."""
    normalized = str(raw_value or "").strip().lower()
    normalized = normalized.replace("ü", "u").replace("ß", "ss")
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


def _with_runtime_layout_options(options, printable_width_cm, printable_height_cm=None, cache=None):
    """Attach render-time layout context for answer blocks.

    `cache` is an optional `BlockComputationCache` (see
    `app/core/block_computation_cache.py`), injected as `_computation_cache`
    the same way `_printable_width_cm`/`_printable_height_cm` already are --
    individual block renderers read these via `options.get(...)` rather
    than needing a dedicated parameter threaded through every dispatch
    layer. `printable_height_cm` is optional (unlike width) since not every
    call site has resolved it yet; blocks that need it (e.g. `crossword`'s
    `maxh` default) fall back on their own when it's absent.
    """
    merged = dict(options or {})
    merged["_printable_width_cm"] = float(printable_width_cm)
    if printable_height_cm is not None:
        merged["_printable_height_cm"] = float(printable_height_cm)
    merged["_computation_cache"] = cache
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


def render_columns_container(
    columns_blocks,
    options,
    include_solutions,
    document_mode="ws",
    printable_width_cm=18.0,
    printable_height_cm=None,
    cache=None,
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
    container_alignment = _normalize_object_alignment((options or {}).get("align"))

    column_html = []
    for column_blocks in columns_blocks:
        rendered_parts = []
        for block_type, block_options, content in column_blocks:
            runtime_options = _with_runtime_layout_options(
                block_options,
                printable_width_cm,
                printable_height_cm=printable_height_cm,
                cache=cache,
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

    columns_html = (
        f"<div class='columns columns-custom' style='{escape(inline_style)}'>{''.join(column_html)}</div>"
    )
    if container_alignment:
        return (
            f"<div class='bw-object-align bw-object-align-{container_alignment}'>"
            f"{columns_html}</div>"
        )
    return columns_html


def render_body_with_columns(
    blocks,
    include_solutions,
    document_mode="ws",
    printable_width_cm=18.0,
    printable_height_cm=None,
    cache=None,
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
                    printable_height_cm=printable_height_cm,
                    cache=cache,
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
            printable_height_cm=printable_height_cm,
            cache=cache,
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
