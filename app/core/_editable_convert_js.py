"""Daten fuer den editierbaren PPTX-Export: das im Browser ausgefuehrte Klassifizierungs-Skript
(`_CLASSIFY_JS`) und die Blocktypen, die immer als Bild uebernommen werden.

Reine Daten (JavaScript als Zeichenkette); die Auswertung lebt in
`blatt_kern_pptx_export_editable_convert.py`, das beide Namen re-exportiert.
"""

# line-limit: data-only
from __future__ import annotations




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
        "struktogramm",
        "structogram",
        "selfcheck",
        "qrcode",
        "chrome",
    }
)


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
            fontFamily: style.fontFamily,
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
