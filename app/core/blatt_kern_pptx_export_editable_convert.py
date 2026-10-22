"""Reine Umrechnungslogik für den editierbaren PPTX-Export: DOM-Klassifikation
(JS, ausgeführt via Playwright) plus die CSS-px-zu-EMU-/Pt-Umrechnung, die daraus
`RenderableElement`-taugliche Daten macht.

Bewusst ohne jede Playwright-/Browser-Abhängigkeit -- `_build_slide_elements`
nimmt nur das bereits von `page.evaluate(_CLASSIFY_JS, ...)` zurückgegebene
JSON entgegen (siehe `blatt_kern_pptx_export_editable.py::extract_slide_elements`),
sodass diese Umrechnung ohne echten Browser testbar ist. Halte diese Trennung
bei künftigen Änderungen bei -- Browser-I/O gehört ins Geschwistermodul.
"""

from __future__ import annotations

import re
from ._editable_convert_js import (  # noqa: F401 -- re-exportiert (blatt_kern_pptx_export_editable.py)
    _CLASSIFY_JS,
    _IMAGE_ONLY_BLOCK_TYPES,
)

EMU_PER_PT = 12700
"""1 Punkt (pptx `Pt`) = 12700 EMU -- Standard-OOXML-Konstante."""

"""Blocktypen, deren gesamter Subtree als EIN zugeschnittenes Bild exportiert
wird, statt nach Text-Blatt-Elementen durchsucht zu werden.

Bewusst NICHT identisch mit `blatt_kern_task_render.py::ANSWER_BLOCK_TYPES`
(normativer Validator-Begriff "hat eine Antwortfeld-`type`-Option") --
diese Menge hier ist eine reine PPTX-Export-Entscheidung ("ist primär
visuell/grafisch, kein sinnvoll editierbarer Fließtext"). `mc`/`cloze`/
`ordering`/`task`/`subtask`/`info`/`material`/`solution`/`writebox`/`help`
bleiben bewusst text-fähig -- ihr Inhalt ist überwiegend Text, auch wenn
sie Checkboxen/Lückenlinien/Rahmen verlieren (GRENZE(v1): bewusst in Kauf
genommen).

`"table"` ist bewusst NICHT hier enthalten -- `:::table` bekommt seit B4
eine eigene, echte zellbasierte PPTX-Tabelle (`kind="table"`, siehe
`markTable()`/`_build_table_data()` unten), kein Bild mehr.

`"chrome"` ist kein echter `:::`-Blocktyp, sondern das
`data-block-type="chrome"`-Attribut, das `blatt_kern_layout_presentation.py`
auf Mini-Header- und Fußzeilen-/Folienzähler-Bereiche setzt (zwei Regionen,
nicht drei Einzel-Shapes -- Mini-Header liegt vor, Fußzeile+Zähler liegen
nach `.ab-slide-body` im bestehenden DOM, absichtlich nicht umsortiert)."""

"""JS ausgeführt via `page.evaluate()`: klassifiziert pro `.ab-slide`-Sektion
alle `[data-block-type]`-Wrapper (Bild-Allow-Liste vs. Text-Blatt-Walk vs.
`:::table`-Zellwalk, siehe `_IMAGE_ONLY_BLOCK_TYPES`/`markTable()`) und
markiert jedes resultierende Bild-Shape-Element mit einem global eindeutigen
`data-pptx-index`-Attribut, über das Python danach per
`page.query_selector('[data-pptx-index="N"]')` denselben
Element-Handle für Bild-Screenshots wiederfindet -- `page.evaluate()`
selbst liefert nur JSON-Daten zurück, keine Element-Handles.

`<img>`/`<svg>`/`<canvas>` und MathJax-Container (`<mjx-container>`, über
den Tag-Präfix `MJX-` erkannt) werden IMMER als eigenes Bild behandelt,
auch innerhalb eines Text-Blocks -- ohne diese Sonderregel würde z. B.
eine Formel beim Blatt-Element-Walk spurlos verschwinden (kein Text,
kein erkannter Block)."""

_ALIGN_MAP = {
    "left": "left", "start": "left",
    "center": "center",
    "right": "right", "end": "right",
    "justify": "justify",
}

_RGB_PATTERN = re.compile(r"rgba?\((\d+),\s*(\d+),\s*(\d+)")


def first_font_family(css_font_family) -> str | None:
    """Erster Familienname einer CSS-`font-family`-Liste, ohne Anführungszeichen.

    Example:
        >>> first_font_family("'Comic Neue', 'Comic Sans MS', cursive")
        'Comic Neue'
    """
    for name in str(css_font_family or "").split(","):
        cleaned = name.strip().strip("'\"").strip()
        if cleaned:
            return cleaned
    return None


def _parse_rgb(css_color) -> tuple[int, int, int]:
    """Parses `"rgb(r, g, b)"`/`"rgba(r, g, b, a)"` (the only format
    `getComputedStyle(...).color` ever returns) into an `(r, g, b)` tuple.
    Falls back to black for anything unparseable rather than raising --
    a color that can't be read is a cosmetic miss, not worth failing the
    whole slide over."""

    match = _RGB_PATTERN.search(str(css_color or ""))
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _is_bold(font_weight) -> bool:
    """v1 reduces every CSS weight to a binary bold/not-bold -- `400`/`500`
    both count as not-bold, `600`+ as bold. Finer weight gradations aren't
    reconstructed (GRENZE(v1): documented, not silently approximated as
    if it were exact)."""

    text = str(font_weight or "").strip().lower()
    if text in {"bold", "bolder"}:
        return True
    try:
        return int(text) >= 600
    except ValueError:
        return False


def _is_italic(font_style) -> bool:
    return str(font_style or "").strip().lower() in {"italic", "oblique"}


_ALPHA_PATTERN = re.compile(r"rgba\([^)]*,\s*([\d.]+)\s*\)")


def _parse_background_rgb(css_color) -> tuple[int, int, int] | None:
    """Parses a cell's `getComputedStyle(...).backgroundColor` into an
    `(r, g, b)` tuple, but only when the browser actually rendered a
    VISIBLE background -- `None` for a fully transparent
    (`"rgba(r, g, b, 0)"`, Chromium's default for an element with no own
    `background-color`) or unparseable value. A `:::table` cell without
    its own background CSS (every plain `<td>`, see `.answer-table td` in
    `assets/worksheet.css`) must end up with NO explicit PPTX fill --
    treating its transparent computed color as if it were literal black
    would paint every data cell black. Partial alpha (`0 < a < 1`) is
    treated as opaque (v1 doesn't blend against a page background)."""

    text = str(css_color or "")
    alpha_match = _ALPHA_PATTERN.search(text)
    if alpha_match and float(alpha_match.group(1)) <= 0:
        return None
    rgb_match = _RGB_PATTERN.search(text)
    if not rgb_match:
        return None
    return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))


_GRID_EDGE_MERGE_TOLERANCE_PX = 1.5
"""Default tolerance for `merge_nearby_grid_edges()`. Browser cell rects
are floating-point and adjacent cells that share a border can report
slightly different edge coordinates for what is visually the same grid
line (sub-pixel layout rounding) -- without merging, `199.999`/`200.001`
would become two separate PPTX columns/rows instead of one. Chosen well
under a realistic column/row width so genuinely distinct grid lines are
never accidentally merged."""


def merge_nearby_grid_edges(
    edges: list[float], tolerance: float = _GRID_EDGE_MERGE_TOLERANCE_PX
) -> list[float]:
    """Collapses near-duplicate floating-point edge coordinates (e.g. the
    left/right or top/bottom rect boundaries of every `:::table` cell)
    into one sorted list of distinct logical grid lines.

    A single centralized helper instead of scattered tolerance checks --
    used by `_build_table_data()` for both the column (x) and row (y)
    axis. Greedy forward merge: each edge is compared only to the last
    KEPT edge, not pairwise to every other edge, so a run of edges each
    within `tolerance` of its neighbour collapses to one line even if the
    first and last of that run are more than `tolerance` apart -- correct
    here because real table borders never sit that densely packed."""

    if not edges:
        return []
    sorted_edges = sorted(edges)
    merged = [sorted_edges[0]]
    for edge in sorted_edges[1:]:
        if edge - merged[-1] > tolerance:
            merged.append(edge)
    return merged


def _nearest_edge_index(edges: list[float], value: float) -> int:
    """Finds which already-merged grid line `value` (a cell's own rect
    edge) belongs to -- since `merge_nearby_grid_edges()` was built FROM
    every cell's rect edges in the first place, `value` always lies
    within `tolerance` of exactly one entry; nearest-by-distance is a
    safe, simple way to look that entry back up without re-deriving the
    tolerance logic here."""

    return min(range(len(edges)), key=lambda i: abs(edges[i] - value))


def _build_table_data(entry: dict, scale_x: float, scale_y: float) -> dict | None:
    """Converts one raw `kind="table"` entry (`markTable()`'s per-cell
    rect/text/style list) into EMU-positioned grid data for a real
    `python-pptx` table.

    **Geometry-driven, not `rowSpan`/`colSpan`-driven:** the actual grid
    line positions are reconstructed from EVERY cell's own rendered rect
    (`merge_nearby_grid_edges()` on all x-edges/y-edges), not just the
    first row/column -- a first-row/first-column-only approach breaks as
    soon as any cell spans multiple rows/columns, since a spanning cell's
    own rect never reveals the grid lines it crosses. Each cell's logical
    `(row, col, row_span, col_span)` then falls out purely from looking up
    where ITS OWN rect edges land in that merged grid (`_nearest_edge_index`)
    -- consistent by construction, since those merged edges were built
    from exactly this cell's (and every other cell's) rect in the first
    place.

    Returns `None` for a table with no usable cells (empty `:::table`,
    or every cell degenerate-sized) -- the caller drops the entry
    entirely, same as a text entry with zero runs."""

    raw_cells = [c for c in (entry.get("cells") or []) if (c.get("rect") or {}).get("width", 0) and (c.get("rect") or {}).get("height", 0)]
    if not raw_cells:
        return None

    x_edges = merge_nearby_grid_edges(
        [float((c["rect"]).get("x") or 0) for c in raw_cells]
        + [float((c["rect"]).get("x") or 0) + float((c["rect"]).get("width") or 0) for c in raw_cells]
    )
    y_edges = merge_nearby_grid_edges(
        [float((c["rect"]).get("y") or 0) for c in raw_cells]
        + [float((c["rect"]).get("y") or 0) + float((c["rect"]).get("height") or 0) for c in raw_cells]
    )
    if len(x_edges) < 2 or len(y_edges) < 2:
        return None

    cells_out = []
    for raw_cell in raw_cells:
        rect = raw_cell["rect"]
        x = float(rect.get("x") or 0)
        y = float(rect.get("y") or 0)
        width = float(rect.get("width") or 0)
        height = float(rect.get("height") or 0)
        start_col = _nearest_edge_index(x_edges, x)
        end_col = _nearest_edge_index(x_edges, x + width)
        start_row = _nearest_edge_index(y_edges, y)
        end_row = _nearest_edge_index(y_edges, y + height)
        cells_out.append(
            {
                "row": start_row,
                "col": start_col,
                "row_span": max(1, end_row - start_row),
                "col_span": max(1, end_col - start_col),
                "text": str(raw_cell.get("text") or ""),
                "bold": _is_bold(raw_cell.get("fontWeight")),
                "align": _ALIGN_MAP.get(str(raw_cell.get("textAlign") or "left").lower(), "left"),
                "background_rgb": _parse_background_rgb(raw_cell.get("backgroundColor")),
            }
        )

    return {
        "rows": len(y_edges) - 1,
        "cols": len(x_edges) - 1,
        "column_widths_emu": [round((x_edges[i + 1] - x_edges[i]) * scale_x) for i in range(len(x_edges) - 1)],
        "row_heights_emu": [round((y_edges[i + 1] - y_edges[i]) * scale_y) for i in range(len(y_edges) - 1)],
        "cells": cells_out,
    }


def build_slide_elements(raw_slide: dict, slide_width_emu: int, slide_height_emu: int) -> list[dict]:
    """Converts one slide's raw JS-extracted entries (`_CLASSIFY_JS`'s
    return value for one slide) into EMU-positioned dicts.

    `kind="image"` entries still carry only `index` (not `image_bytes`
    yet) -- filling that in needs either a live Playwright element-handle
    screenshot or a fetch of the `src` URI, both of which only
    `extract_slide_elements` (the caller, which has the `page`) can do.
    `src` is passed through as-is when present (a real `<img>` -- see
    `_CLASSIFY_JS::mark()`), so the caller can prefer reading/fetching the
    original asset bytes over rasterizing a screenshot of it. Kept as a
    plain function with no Playwright dependency so the EMU-scaling math
    itself is unit-testable without a browser.

    `.ab-slide` sizes itself via `min-height:100vh`/`width:100%` (see
    `assets/worksheet.css`), not a fixed cm box, so there is no fixed
    px-per-cm constant to convert with -- every element's CSS-px rect is
    scaled proportionally to the slide's OWN measured
    `slideWidth`/`slideHeight` (in `raw_slide`) against the target
    `slide_width_emu`/`slide_height_emu`. The same per-axis scale factor
    is reused for font size (`scale_x`, since the caller picks a viewport
    whose aspect ratio already matches the target slide format, so
    `scale_x`≈`scale_y` by construction) -- keeps text sized consistently
    relative to the slide regardless of which viewport pixel width was
    used to render it.

    `kind="text"` entries always carry a `"runs"` list (one dict per
    formatting span: `text`/`font_size_pt`/`bold`/`italic`/`color_rgb`)
    plus one shared `"align"` -- a single, uniform representation for
    every text entry, whether it came from a plain paragraph (one run) or
    one with inline `**bold**`/`*italic*` formatting (several runs, each
    with the actual computed style of its own span, not the paragraph's).
    A `raw_run` with empty text (possible after `_CLASSIFY_JS`'s
    leading/trailing-whitespace trim) is dropped; an entry left with zero
    runs is dropped entirely, same as the old "no text, no entry" rule.

    `kind="table"` entries (B4) carry a `"table"` dict (`_build_table_data()`)
    with EMU-scaled `column_widths_emu`/`row_heights_emu` and a flat
    `"cells"` list (`row`/`col`/`row_span`/`col_span`/`text`/`bold`/`align`/
    `background_rgb`) -- unlike `kind="text"`, cell text has NO inline-run
    list (GRENZE(v1): documented, see `TableCell` in
    `blatt_kern_pptx_export_editable.py`).
    """

    slide_width_px = float(raw_slide.get("slideWidth") or 0)
    slide_height_px = float(raw_slide.get("slideHeight") or 0)
    if slide_width_px <= 0 or slide_height_px <= 0:
        return []

    scale_x = slide_width_emu / slide_width_px
    scale_y = slide_height_emu / slide_height_px

    built = []
    for entry in raw_slide.get("elements") or []:
        rect = entry.get("rect") or {}
        left_emu = round(float(rect.get("x") or 0) * scale_x)
        top_emu = round(float(rect.get("y") or 0) * scale_y)
        width_emu = round(float(rect.get("width") or 0) * scale_x)
        height_emu = round(float(rect.get("height") or 0) * scale_y)
        if width_emu <= 0 or height_emu <= 0:
            continue

        if entry.get("kind") == "image":
            built_image = {
                "kind": "image",
                "index": entry.get("index"),
                "left_emu": left_emu,
                "top_emu": top_emu,
                "width_emu": width_emu,
                "height_emu": height_emu,
            }
            src = entry.get("src")
            if src:
                built_image["src"] = src
            built.append(built_image)
            continue

        if entry.get("kind") == "table":
            table = _build_table_data(entry, scale_x, scale_y)
            if table is None:
                continue
            built.append(
                {
                    "kind": "table",
                    "left_emu": left_emu,
                    "top_emu": top_emu,
                    "width_emu": width_emu,
                    "height_emu": height_emu,
                    "table": table,
                }
            )
            continue

        runs = []
        for raw_run in entry.get("runs") or []:
            run_text = str(raw_run.get("text") or "")
            if not run_text:
                continue
            runs.append(
                {
                    "text": run_text,
                    "font_size_pt": max(1.0, float(raw_run.get("fontSizePx") or 12) * scale_x / EMU_PER_PT),
                    "bold": _is_bold(raw_run.get("fontWeight")),
                    "italic": _is_italic(raw_run.get("fontStyle")),
                    "color_rgb": _parse_rgb(raw_run.get("color")),
                    "font_name": first_font_family(raw_run.get("fontFamily")),
                }
            )
        if not runs:
            continue

        built.append(
            {
                "kind": "text",
                "left_emu": left_emu,
                "top_emu": top_emu,
                "width_emu": width_emu,
                "height_emu": height_emu,
                "align": _ALIGN_MAP.get(str(entry.get("align") or "left").lower(), "left"),
                "runs": runs,
            }
        )
    return built
