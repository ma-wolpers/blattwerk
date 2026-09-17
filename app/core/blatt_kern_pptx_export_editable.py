"""Experimenteller editierbarer PPTX-Export: extrahiert DOM-Geometrie und
Text aus dem gerenderten Präsentations-HTML über einen browsergesteuerten
Playwright-Prozess und baut daraus echte PowerPoint-Text-/Bild-Shapes,
statt wie der bestehende Raster-Export (`blatt_kern_pptx_export.py`) jede
Folie als ein einziges Vollbild abzulegen.

Rendering-Pfad: HTML/CSS -> Browser-Layout -> DOM-Geometrie + Styles ->
`RenderableElement`-Liste (dieses Modul, Klassifikation/Umrechnung in
`blatt_kern_pptx_export_editable_convert.py`) -> PPTX-Shapes
(`blatt_kern_pptx_export.py::build_editable_slide`).

**"Editierbar" bedeutet in v1 ausdrücklich NICHT "vollständig editierbar"**:
unterstützte Texte werden echte PowerPoint-Textboxen, unterstützte
Grafiken echte, einzelne Bild-Shapes -- keine semantische Rekonstruktion
der HTML-/CSS-Darstellung. Unterstützungsmatrix:

| Inhalt                                               | Ergebnis in v1 |
|-------------------------------------------------------|----------------|
| Fließtext (Absätze, Überschriften, einfache Listen)    | echte Textbox |
| `<img>` mit lesbarer Quelle (`data:`/`file:`/`http(s):`) | eigenes Bild-Shape, **Original-Asset-Bytes** (kein Screenshot-Reencode) |
| MathJax-Formeln (`<mjx-container>`), rohes `<svg>`/`<canvas>`, `<img>` ohne lesbare Quelle | eigenes Bild-Shape (Screenshot, zugeschnitten) |
| `:::table`, `:::geometry`, `:::grid`, `:::dots`, `:::crossword`, `:::wordsearch`, `:::qrcode`, `:::matching`, `:::mindmap`, `:::selfcheck`, `:::numberline`, `:::checkgrid`, `:::lines`, `:::space`, `raw`-Blöcke | eigenes Bild-Shape (ganzer Block, kein Zell-/Element-Mapping) |
| gemischte Inline-Formatierung (`**fett** normal`)      | echte, mehrere PowerPoint-Runs in einer Textbox (fett/kursiv je Run) |
| CSS-Gradients, Schatten, `border-radius`               | nicht übertragen (nur Flächenfarbe, falls überhaupt) |
| `position:absolute`/`z-index` außerhalb der Bild-Blöcke | Stapelreihenfolge nur über Dokumentreihenfolge, keine CSS-Stacking-Garantie |
| Folien-Chrome (Mini-Header, Abschnitts-Footer, Folienzähler) | eigenes Bild-Shape (zwei Regionen: vor/nach dem Folieninhalt) |

Diese Liste ist bewusst unvollständig und kann mit wachsender Unterstützung
erweitert werden -- sie ist kein Versprechen auf vollständige Abdeckung.

**Klassifizierung** läuft über das `data-block-type`-Attribut, das
`blatt_kern_task_render.py::render_block()` auf den Root jedes Blocks
schreibt (kein CSS-Klassen-Sniffing, das wäre ein brüchiger Vertrag mit
reinen Styling-Klassen) -- Details zur Bild-vs-Text-Entscheidung in
`blatt_kern_pptx_export_editable_convert.py`.

**Fallback-Stufen** (siehe `blatt_kern_pptx_export.py::build_presentation_pptx`):
Stufe A (alles editierbar, so weit v1 das unterstützt) läuft normal durch
`extract_slide_elements()`; Stufe B (eine einzelne Folie lässt sich nicht
extrahieren, Rest bleibt editierbar) wird hier selbst behandelt
(`page.screenshot(clip=...)` für nur die betroffene Folie, ohne den
Browser neu zu starten); Stufe C (Playwright/Browser gar nicht verfügbar)
wird über `EditableExportUnavailable` signalisiert, das der Aufrufer auf
den bestehenden Raster-Export umleitet.

Nur bekannte, erwartbare Infrastrukturfehler (Playwright fehlt, kein
Browser gefunden, `playwright.sync_api.Error`/`TimeoutError` bei Start/
Navigation/Extraktion) werden hier abgefangen und in
`EditableExportUnavailable`/`SlideExtractionResult`-Rasterfallback
übersetzt. Ein Bug in diesem Modul selbst (z. B. in der reinen
Umrechnungslogik) propagiert unverändert als echter Fehler -- kein
pauschales `except Exception`.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from .blatt_kern_pptx_export_editable_convert import _CLASSIFY_JS, _IMAGE_ONLY_BLOCK_TYPES, build_slide_elements


class EditableExportUnavailable(Exception):
    """Die editierbare Export-Pipeline kann gar nicht starten (Playwright
    nicht installiert, kein unterstützter Browser gefunden, Browser-Start/
    Navigation schlägt fehl) -- Stufe-C-Trigger in
    `blatt_kern_pptx_export.py::build_presentation_pptx` (voller Raster-
    Fallback)."""


@dataclass(frozen=True)
class TextRun:
    """Eine einzelne, einheitlich formatierte Textspanne innerhalb einer
    Textbox -- ein unformatierter Absatz wird genau eine `TextRun`, ein
    Absatz mit `**fett**`/`*kursiv*`-Formatierung mehrere, je mit ihrem
    eigenen tatsächlichen `getComputedStyle()` (siehe `buildRuns()` in
    `blatt_kern_pptx_export_editable_convert.py::_CLASSIFY_JS`). CSS-
    Schriftgewichte werden v1 binär auf `bold` reduziert (`_is_bold()`) --
    feinere Abstufungen (400/500/600/700 ...) werden nicht nachgebildet."""

    text: str
    font_size_pt: float
    bold: bool
    italic: bool
    color_rgb: tuple[int, int, int]


@dataclass(frozen=True)
class RenderableElement:
    """Ein einzelnes, platzierbares PPTX-Shape -- die Trennlinie zwischen
    DOM-Extraktion (dieses Modul) und reinem `python-pptx`-Bau
    (`build_editable_slide` in `blatt_kern_pptx_export.py`), der selbst
    keine Browser-/DOM-Logik mehr sieht.

    `kind="text"` trägt IMMER eine `runs`-Liste (nie ein separates flaches
    `text`/Style-Feld) -- ein einzeln formatierter Absatz ist einfach eine
    Ein-Element-Liste, keine Sonderform. `align` gilt für die ganze
    Textbox (Absatz-Ebene), nicht pro Run."""

    kind: Literal["text", "image"]
    left_emu: int
    top_emu: int
    width_emu: int
    height_emu: int
    align: Literal["left", "center", "right", "justify"] | None = None
    runs: list[TextRun] | None = None
    image_bytes: bytes | None = None


@dataclass(frozen=True)
class SlideExtractionResult:
    """Ergebnis für EINE Folie: entweder eine `RenderableElement`-Liste
    (Stufe A) oder ein Fallback-Vollbild dieser einen Folie samt Grund
    (Stufe B) -- nie beides."""

    elements: list[RenderableElement] | None
    raster_image_bytes: bytes | None = None
    raster_reason: str | None = None


def is_editable_pptx_available() -> bool:
    """Returns whether the experimental editable PPTX export could even be
    attempted right now -- `playwright` importable AND a supported browser
    found. Cheap (no browser launch): used by the export dialog
    (`app/ui/export_dialog.py`) to disable the "Editierbare Text-/
    Bildelemente"-checkbox with an explanatory hint instead of letting the
    user enable an option that could only ever silently fall back."""

    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False

    from .blatt_kern_io_pdf import find_chromium_executable

    return bool(find_chromium_executable())


def _resolve_playwright_executable_path() -> str:
    """Reuses `find_chromium_executable()` (the same browser discovery the
    existing PDF/raster-PPTX pipeline already relies on) instead of
    Playwright's own `channel="msedge"/"chrome"` resolution -- avoids
    establishing a second, potentially divergent browser-discovery logic
    for the same purpose."""

    from .blatt_kern_io_pdf import find_chromium_executable

    executable = find_chromium_executable()
    if not executable:
        raise EditableExportUnavailable(
            "Kein Chromium-Browser gefunden (Microsoft Edge oder Google Chrome installieren)."
        )
    return executable


def _fetch_image_src(src: str, page) -> bytes | None:
    """Reads the ORIGINAL bytes of a real `<img>` source instead of
    rasterizing a screenshot of it -- `data:`/`file:` URIs are read
    directly (both natively supported by `urllib.request.urlopen`, no
    manual base64/path parsing needed); `http(s):` URIs are fetched via
    Playwright's own request API (reuses the browser's context rather than
    a separate, unauthenticated HTTP client). `None` for any other/
    unrecognised scheme, letting the caller fall back to a screenshot --
    geometry/positioning is unaffected either way, `add_picture(...,
    width=, height=)` sets display size independent of source pixels.
    """

    scheme = urlparse(src).scheme.lower()
    if scheme in {"data", "file"}:
        with urllib.request.urlopen(src) as response:  # noqa: S310 -- scheme allow-listed above
            return response.read()
    if scheme in {"http", "https"}:
        response = page.request.get(src)
        return response.body() if response.ok else None
    return None


def _resolve_image_bytes(built: dict, page) -> bytes | None:
    """Prefers the original asset (`_fetch_image_src`) for entries that
    carry a `src` (real `<img>` elements, see `_CLASSIFY_JS::mark()`),
    falling back to an element-handle screenshot -- both for entries
    without `src` (MathJax/SVG/canvas/chrome/table) and when fetching the
    original hits an EXPECTED, infrastructure-level failure (broken/
    unreadable local reference, network error). Only those specific,
    known exception types are caught here; anything else propagates as a
    real bug, per this module's fallback philosophy.
    """

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    src = built.get("src")
    if src:
        try:
            image_bytes = _fetch_image_src(src, page)
            if image_bytes:
                return image_bytes
        except (OSError, ValueError, PlaywrightError, PlaywrightTimeoutError):
            pass  # falls through to the screenshot fallback below

    handle = page.query_selector(f'[data-pptx-index="{built["index"]}"]')
    return handle.screenshot() if handle is not None else None


def _renderable_elements_from_built(built_entries: list[dict], page) -> list[RenderableElement]:
    """Turns `build_slide_elements()`'s plain dicts into `RenderableElement`s,
    filling in `image_bytes` for `kind="image"` entries -- preferring the
    original asset bytes over a screenshot where possible
    (`_resolve_image_bytes`), the one piece `build_slide_elements` itself
    cannot do, since it has no `page`."""

    elements: list[RenderableElement] = []
    for built in built_entries:
        if built["kind"] == "image":
            image_bytes = _resolve_image_bytes(built, page)
            if not image_bytes:
                continue
            elements.append(
                RenderableElement(
                    kind="image",
                    left_emu=built["left_emu"],
                    top_emu=built["top_emu"],
                    width_emu=built["width_emu"],
                    height_emu=built["height_emu"],
                    image_bytes=image_bytes,
                )
            )
        else:
            elements.append(
                RenderableElement(
                    kind="text",
                    left_emu=built["left_emu"],
                    top_emu=built["top_emu"],
                    width_emu=built["width_emu"],
                    height_emu=built["height_emu"],
                    align=built["align"],
                    runs=[
                        TextRun(
                            text=run["text"],
                            font_size_pt=run["font_size_pt"],
                            bold=run["bold"],
                            italic=run["italic"],
                            color_rgb=run["color_rgb"],
                        )
                        for run in built["runs"]
                    ],
                )
            )
    return elements


def extract_slide_elements(
    html_path: Path,
    slide_width_emu: int,
    slide_height_emu: int,
    viewport_width_px: int = 1920,
    mathjax_wait_ms: int = 5000,
) -> list[SlideExtractionResult]:
    """Renders `html_path` (the full multi-slide presentation HTML -- the
    same file `write_pdf_from_html` would otherwise print to PDF) with
    Playwright and returns one `SlideExtractionResult` per `.ab-slide`
    section, in document order.

    `.ab-slide` sizes itself via `min-height:100vh`/`width:100%`
    (`assets/worksheet.css`), not a fixed cm box -- so the Playwright
    viewport is set to the target page format's aspect ratio, and every
    element's measured CSS-px rect is scaled proportionally to
    `slide_width_emu`/`slide_height_emu` afterward
    (`build_slide_elements`) rather than assuming a fixed px-per-cm
    constant. `emulate_media("print")` matches the CSS the real PDF/
    raster export renders under.

    Raises `EditableExportUnavailable` if the pipeline can't even start
    (missing Playwright, no browser found, launch/navigation failure) --
    callers should treat that as a Stage C trigger (full raster fallback).
    A single slide's extraction failure never aborts the run: it's caught
    here and turned into that slide's `raster_image_bytes`/`raster_reason`
    (Stage B), via a `page.screenshot(clip=...)` scoped to just that
    slide's bounding box, without restarting the browser.
    """

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise EditableExportUnavailable(
            "playwright ist nicht installiert (siehe requirements-editable-pptx.txt)."
        ) from exc

    executable_path = _resolve_playwright_executable_path()
    aspect_ratio = slide_height_emu / slide_width_emu
    viewport_height_px = max(1, round(viewport_width_px * aspect_ratio))

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=executable_path, headless=True)
            try:
                page = browser.new_page(
                    viewport={"width": viewport_width_px, "height": viewport_height_px}
                )
                page.emulate_media(media="print")
                page.goto(html_path.resolve().as_uri())
                page.wait_for_timeout(mathjax_wait_ms)

                raw_slides = page.evaluate(_CLASSIFY_JS, sorted(_IMAGE_ONLY_BLOCK_TYPES))
                slide_handles = page.query_selector_all(".ab-slide")

                results: list[SlideExtractionResult] = []
                for slide_index, raw_slide in enumerate(raw_slides):
                    try:
                        built_entries = build_slide_elements(raw_slide, slide_width_emu, slide_height_emu)
                        elements = _renderable_elements_from_built(built_entries, page)
                        results.append(SlideExtractionResult(elements=elements))
                    except (PlaywrightError, PlaywrightTimeoutError) as exc:
                        raster_bytes = None
                        if slide_index < len(slide_handles):
                            try:
                                box = slide_handles[slide_index].bounding_box()
                            except (PlaywrightError, PlaywrightTimeoutError):
                                box = None
                            if box:
                                raster_bytes = page.screenshot(clip=box)
                        if raster_bytes is None:
                            raster_bytes = page.screenshot()
                        results.append(
                            SlideExtractionResult(
                                elements=None,
                                raster_image_bytes=raster_bytes,
                                raster_reason=str(exc),
                            )
                        )
                return results
            finally:
                browser.close()
    except (PlaywrightError, PlaywrightTimeoutError) as exc:
        raise EditableExportUnavailable(f"Playwright/Browser-Start fehlgeschlagen: {exc}") from exc
