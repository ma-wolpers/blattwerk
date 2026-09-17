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

EMU_PER_PT = 12700
"""1 Punkt (pptx `Pt`) = 12700 EMU -- Standard-OOXML-Konstante."""

_IMAGE_ONLY_BLOCK_TYPES = frozenset(
    {
        "raw",
        "lines",
        "grid",
        "geometry",
        "dots",
        "space",
        "numberline",
        "matching",
        "wordsearch",
        "crossword",
        "checkgrid",
        "mindmap",
        "selfcheck",
        "qrcode",
        "chrome",
    }
)
"""Blocktypen, deren gesamter Subtree als EIN zugeschnittenes Bild exportiert
wird, statt nach Text-Blatt-Elementen durchsucht zu werden.

Bewusst NICHT identisch mit `blatt_kern_task_render.py::ANSWER_BLOCK_TYPES`
(normativer Validator-Begriff "hat eine Antwortfeld-`type`-Option") --
diese Menge hier ist eine reine PPTX-Export-Entscheidung ("ist primär
visuell/grafisch, kein sinnvoll editierbarer Fließtext"). `mc`/`cloze`/
`ordering`/`task`/`subtask`/`info`/`material`/`solution`/`writebox`/`help`
bleiben bewusst text-fähig -- ihr Inhalt ist überwiegend Text, auch wenn
sie Checkboxen/Lückenlinien/Rahmen verlieren (dokumentierte v1-Grenze).

`"table"` ist bewusst NICHT hier enthalten -- `:::table` bekommt seit B4
eine eigene, echte zellbasierte PPTX-Tabelle (`kind="table"`, siehe
`markTable()`/`_build_table_data()` unten), kein Bild mehr.

`"chrome"` ist kein echter `:::`-Blocktyp, sondern das
`data-block-type="chrome"`-Attribut, das `blatt_kern_layout_presentation.py`
auf Mini-Header- und Fußzeilen-/Folienzähler-Bereiche setzt (zwei Regionen,
nicht drei Einzel-Shapes -- Mini-Header liegt vor, Fußzeile+Zähler liegen
nach `.ab-slide-body` im bestehenden DOM, absichtlich nicht umsortiert)."""

_CLASSIFY_JS = """
(imageBlockTypes) => {
    const INLINE_TAGS = new Set([
        'STRONG', 'EM', 'B', 'I', 'U', 'S', 'SPAN', 'A', 'SUB', 'SUP',
        'BR', 'CODE', 'MARK', 'SMALL', 'ABBR',
    ]);
    const IMAGE_TAGS = new Set(['IMG', 'SVG', 'CANVAS']);

    function isImageLikeElement(el) {
        if (IMAGE_TAGS.has(el.tagName)) return true;
        return el.tagName.startsWith('MJX-');
    }

    function isLeafTextElement(el) {
        for (const child of el.children) {
            if (!INLINE_TAGS.has(child.tagName)) return false;
        }
        return true;
    }

    function relRect(el, originRect) {
        const r = el.getBoundingClientRect();
        return { x: r.x - originRect.x, y: r.y - originRect.y, width: r.width, height: r.height };
    }

    function mark(el, kind, originRect, results, counter) {
        // Only ever called with kind='image' now (text entries go through
        // `markRuns`/`markTextRange` below, both of which always emit a
        // `runs` array -- ONE uniform shape for every kind="text" entry,
        // never a parallel flat text/style representation).
        const index = counter.next++;
        el.setAttribute('data-pptx-index', String(index));
        const entry = { index: index, kind: kind, rect: relRect(el, originRect) };
        if (el.tagName === 'IMG') {
            // Only a real <img> has a meaningful "original asset" to fetch
            // instead of screenshotting -- MathJax/SVG/canvas/chrome/table
            // images have no such source and stay on the screenshot path
            // (Python only reads `src` for `kind === 'image'` entries that
            // actually have it). `currentSrc` reflects e.g. `srcset`-
            // selected/lazy-loaded state; `src` is the plain fallback.
            const resolvedSrc = el.currentSrc || el.src;
            if (resolvedSrc) entry.src = resolvedSrc;
        }
        results.push(entry);
    }

    function runFromStyle(text, styleEl) {
        const style = getComputedStyle(styleEl);
        return {
            text: text,
            fontSizePx: parseFloat(style.fontSize) || 12,
            fontWeight: style.fontWeight,
            fontStyle: style.fontStyle,
            color: style.color,
        };
    }

    function buildRuns(el) {
        // `el` already satisfies `isLeafTextElement` (only inline-
        // formatting descendants, no images/blocks) -- walks every
        // descendant text node, using ITS OWN direct parent element for
        // `getComputedStyle()` (the cascade already resolves inherited +
        // own styles at any nesting depth, e.g. <strong><em>...</em></strong>
        // correctly reports both bold AND italic on the innermost text
        // node's parent -- no manual style-merging needed).
        const runs = [];
        function walk(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent.replace(/\\s+/g, ' ');
                if (text) runs.push(runFromStyle(text, node.parentElement || el));
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                for (const child of Array.from(node.childNodes)) walk(child);
            }
        }
        for (const child of Array.from(el.childNodes)) walk(child);

        if (runs.length > 0) {
            runs[0].text = runs[0].text.replace(/^\\s+/, '');
            runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\\s+$/, '');
        }
        return runs.filter(function (run) { return run.text.length > 0; });
    }

    function markRuns(el, runs, originRect, results, counter) {
        const index = counter.next++;
        el.setAttribute('data-pptx-index', String(index));
        results.push({
            index: index, kind: 'text',
            rect: relRect(el, originRect),
            align: getComputedStyle(el).textAlign,
            runs: runs,
        });
    }

    function markTextRange(range, parentEl, originRect, results, counter, text) {
        // A bare text node between e.g. a formula and a bold word has no
        // element of its own to tag with data-pptx-index (Range isn't an
        // Element) -- doesn't matter, kind is always "text" here, which
        // never needs a later page.query_selector('[data-pptx-index]')
        // lookup for a screenshot the way "image" entries do. Still a
        // one-item `runs` array, same uniform shape as `markRuns`.
        const r = range.getBoundingClientRect();
        const index = counter.next++;
        results.push({
            index: index, kind: 'text',
            rect: { x: r.x - originRect.x, y: r.y - originRect.y, width: r.width, height: r.height },
            align: getComputedStyle(parentEl).textAlign,
            runs: [runFromStyle(text, parentEl)],
        });
    }

    function walkTextCapable(el, originRect, results, handled, counter) {
        if (isImageLikeElement(el)) { mark(el, 'image', originRect, results, counter); return; }
        if (el.hasAttribute('data-block-type')) { processWrapper(el, originRect, results, handled, counter); return; }
        if (isLeafTextElement(el)) {
            // Covers both a childless leaf (a lone text node) and mixed
            // inline formatting (bold/italic/... children) -- a childless
            // element vacuously satisfies "every child is an inline tag",
            // so this replaces what used to be two separate branches.
            const runs = buildRuns(el);
            if (runs.length > 0) markRuns(el, runs, originRect, results, counter);
            return;
        }
        // Mixed content: at least one child is neither inline-formatting
        // nor a leaf (e.g. an <mjx-container> formula sitting inside an
        // otherwise plain paragraph) -- walk childNodes, not just element
        // children, so bare text nodes between such children get their
        // own Range-based fragment instead of silently vanishing (a plain
        // text node is invisible to `el.children`, which only sees
        // Element nodes).
        for (const child of Array.from(el.childNodes)) {
            if (child.nodeType === Node.TEXT_NODE) {
                const text = child.textContent.replace(/\\s+/g, ' ').trim();
                if (!text) continue;
                const range = document.createRange();
                range.selectNodeContents(child);
                markTextRange(range, el, originRect, results, counter, text);
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                walkTextCapable(child, originRect, results, handled, counter);
            }
        }
    }

    function markTable(wrapper, originRect, results, counter) {
        // `:::table` gets a real, cell-based PPTX table (B4) instead of a
        // screenshot -- unlike `mark()`, no `data-pptx-index` is set here,
        // since `kind: 'table'` never goes through the screenshot-fallback
        // element-handle lookup. `wrapper` itself is the tagged
        // `data-block-type='table'` root (the `.answer.table-answer` div,
        // or `.answer-with-solution` when a solution is shown -- either
        // way `<table>` sits somewhere inside it), so the actual
        // `<table>` element is found via `querySelector`, not assumed to
        // be `wrapper` itself. `table.rows`/`row.cells` already return
        // EVERY row/cell (thead + tbody, `<th>` + `<td>`) in document
        // order -- no manual thead/tbody stitching needed. Each cell's
        // own rendered rect is captured; the Python side reconstructs the
        // actual grid-line positions from ALL cells' rects (not just the
        // first row/column, which breaks under rowspan/colspan -- see
        // `_build_table_data()`/`merge_nearby_grid_edges()`).
        const table = wrapper.querySelector('table');
        if (!table) { mark(wrapper, 'image', originRect, results, counter); return; }

        const index = counter.next++;
        const cells = [];
        for (const row of Array.from(table.rows)) {
            for (const cell of Array.from(row.cells)) {
                const style = getComputedStyle(cell);
                cells.push({
                    rect: relRect(cell, originRect),
                    // Flat/simplified cell text (v1 -- see TableCell docstring
                    // in blatt_kern_pptx_export_editable.py): no per-cell
                    // TextRun list, mixed inline formatting *within* one
                    // cell collapses to plain text, deliberately not a
                    // second, independent run-parser next to B3's.
                    text: (cell.textContent || '').replace(/\\s+/g, ' ').trim(),
                    fontWeight: style.fontWeight,
                    textAlign: style.textAlign,
                    backgroundColor: style.backgroundColor,
                });
            }
        }
        results.push({ index: index, kind: 'table', rect: relRect(wrapper, originRect), cells: cells });
    }

    function processWrapper(wrapper, originRect, results, handled, counter) {
        handled.add(wrapper);
        const blockType = wrapper.getAttribute('data-block-type');
        if (blockType === 'table') {
            markTable(wrapper, originRect, results, counter);
        } else if (imageBlockTypes.indexOf(blockType) !== -1) {
            mark(wrapper, 'image', originRect, results, counter);
        } else {
            for (const child of Array.from(wrapper.children)) walkTextCapable(child, originRect, results, handled, counter);
        }
    }

    const counter = { next: 0 };
    const slideSections = Array.from(document.querySelectorAll('.ab-slide'));
    return slideSections.map(section => {
        const originRect = section.getBoundingClientRect();
        const results = [];
        const handled = new Set();
        const wrappers = section.querySelectorAll('[data-block-type]');
        for (const wrapper of Array.from(wrappers)) {
            if (!handled.has(wrapper)) processWrapper(wrapper, originRect, results, handled, counter);
        }
        return { slideWidth: originRect.width, slideHeight: originRect.height, elements: results };
    });
}
"""
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
    reconstructed (documented v1 limitation, not silently approximated as
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
    list (documented v1 limitation, see `TableCell` in
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
