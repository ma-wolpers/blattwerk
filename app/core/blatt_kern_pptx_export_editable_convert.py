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
        "table",
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
        const index = counter.next++;
        el.setAttribute('data-pptx-index', String(index));
        const entry = { index: index, kind: kind, rect: relRect(el, originRect) };
        if (kind === 'text') {
            const style = getComputedStyle(el);
            entry.text = el.textContent.replace(/\\s+/g, ' ').trim();
            entry.fontSizePx = parseFloat(style.fontSize) || 12;
            entry.fontWeight = style.fontWeight;
            entry.color = style.color;
            entry.textAlign = style.textAlign;
        } else if (el.tagName === 'IMG') {
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

    function markTextRange(range, parentEl, originRect, results, counter, text) {
        // A bare text node between e.g. a formula and a bold word has no
        // element of its own to tag with data-pptx-index (Range isn't an
        // Element) -- doesn't matter, kind is always "text" here, which
        // never needs a later page.query_selector('[data-pptx-index]')
        // lookup for a screenshot the way "image" entries do.
        const r = range.getBoundingClientRect();
        const style = getComputedStyle(parentEl);
        const index = counter.next++;
        results.push({
            index: index, kind: 'text',
            rect: { x: r.x - originRect.x, y: r.y - originRect.y, width: r.width, height: r.height },
            text: text,
            fontSizePx: parseFloat(style.fontSize) || 12,
            fontWeight: style.fontWeight,
            color: style.color,
            textAlign: style.textAlign,
        });
    }

    function walkTextCapable(el, originRect, results, handled, counter) {
        if (isImageLikeElement(el)) { mark(el, 'image', originRect, results, counter); return; }
        if (el.hasAttribute('data-block-type')) { processWrapper(el, originRect, results, handled, counter); return; }
        if (el.children.length === 0) {
            const text = el.textContent.replace(/\\s+/g, ' ').trim();
            if (text) mark(el, 'text', originRect, results, counter);
            return;
        }
        if (isLeafTextElement(el)) {
            const text = el.textContent.replace(/\\s+/g, ' ').trim();
            if (text) mark(el, 'text', originRect, results, counter);
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

    function processWrapper(wrapper, originRect, results, handled, counter) {
        handled.add(wrapper);
        const blockType = wrapper.getAttribute('data-block-type');
        if (imageBlockTypes.indexOf(blockType) !== -1) {
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
alle `[data-block-type]`-Wrapper (Bild-Allow-Liste vs. Text-Blatt-Walk,
siehe `_IMAGE_ONLY_BLOCK_TYPES`) und markiert jedes resultierende Shape-
Element mit einem global eindeutigen `data-pptx-index`-Attribut, über das
Python danach per `page.query_selector('[data-pptx-index="N"]')` denselben
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
    text = str(font_weight or "").strip().lower()
    if text in {"bold", "bolder"}:
        return True
    try:
        return int(text) >= 600
    except ValueError:
        return False


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

        text = str(entry.get("text") or "").strip()
        if not text:
            continue
        font_size_pt = max(1.0, float(entry.get("fontSizePx") or 12) * scale_x / EMU_PER_PT)
        built.append(
            {
                "kind": "text",
                "left_emu": left_emu,
                "top_emu": top_emu,
                "width_emu": width_emu,
                "height_emu": height_emu,
                "text": text,
                "font_size_pt": font_size_pt,
                "bold": _is_bold(entry.get("fontWeight")),
                "color_rgb": _parse_rgb(entry.get("color")),
                "align": _ALIGN_MAP.get(str(entry.get("textAlign") or "left").lower(), "left"),
            }
        )
    return built
