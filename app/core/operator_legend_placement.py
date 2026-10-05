"""Operatorenliste im fertigen PDF ans Ende des Inhaltsbereichs ihrer Seite schieben.

Chromium kennt kein CSS „unten auf der Seite platzieren“. Deshalb wird nach dem
Rendern gemessen (gleiches Muster wie `word_note_pdf_check`):

1. Pass 1 drucken.
2. Je Liste die beiden Messmarken (`operator_legend_parts`, Link-Rechtecke) suchen.
3. Steht die Liste allein auf ihrer Seite (kein Inhalt darüber im Satzspiegel),
   bleibt sie oben. Sonst wird sie per ``padding-top`` auf ihrem Wrapper so weit
   nach unten geschoben, dass ihre Unterkante am Ende des Inhaltsbereichs liegt.
   Passt sie gar nicht auf die Restseite, hat Chromium sie schon unaufgeteilt auf
   die nächste Seite gesetzt (``break-inside: avoid-page``) -- dann steht sie dort
   allein und bleibt oben.
4. Pass 2 nur bei mindestens einer Verschiebung.
5. Pass 2 wird nur übernommen, wenn Seitenzahl und Seite jeder Liste unverändert
   sind und keine Liste über den Inhaltsbereich ragt.

**Sicherheitsregel:** Best-effort, nie ein Fehler für Nutzer:innen. Jede
Unsicherheit -- Marke fehlt oder ist doppelt, obere und untere Marke auf
verschiedenen Seiten (mehrseitige Liste), Ausnahme beim Messen, Pass 2 weicht
ab -- lässt Pass 1 unverändert (nur ein internes Log). Danach werden nur die
eigenen Messlinks (Präfix `LEGEND_PROBE_URI_PREFIX`) entfernt.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import fitz

from ..styles.blatt_styles import PAGE_LAYOUTS, _css_length_to_cm, resolve_page_side_margins_cm
from .blatt_kern_io_pdf import write_pdf_from_html
from .operator_legend_parts import LEGEND_ELEMENT_ID_PREFIX, LEGEND_PROBE_URI_PREFIX

_LOG = logging.getLogger(__name__)
_POINTS_PER_CM = 72.0 / 2.54
TOLERANCE_PT = 0.5
"""Messtoleranz (Chromium rastert auf 0,75 pt = 1 px)."""
SAFETY_PT = 1.0
"""Abstand zur Inhaltsunterkante, damit Rundung die Liste nie auf die nächste Seite schiebt."""
MIN_SHIFT_PT = 1.0


@dataclass(frozen=True)
class LegendPosition:
    """Gemessene Lage einer Liste: Seite (0-basiert), Oberkante, Unterkante in pt."""

    page: int
    top: float
    bottom: float


@dataclass(frozen=True)
class ContentArea:
    """Satzspiegel einer Seite in pt (aus `PAGE_LAYOUTS`, wie im `@page`-CSS)."""

    left: float
    top: float
    right: float
    bottom: float


def content_area(page_rect, page_format: str, hole_punch_enabled: bool) -> ContentArea:
    """Satzspiegel aus Seitenrechteck und denselben Rändern wie das Stylesheet."""
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    left_cm, right_cm = resolve_page_side_margins_cm(page_format, hole_punch_enabled)
    top_pt = _css_length_to_cm(layout["page_margin_top_css"], 2.0) * _POINTS_PER_CM
    bottom_pt = _css_length_to_cm(layout["page_margin_bottom_css"], 1.5) * _POINTS_PER_CM
    return ContentArea(
        left=left_cm * _POINTS_PER_CM,
        top=top_pt,
        right=page_rect.width - right_cm * _POINTS_PER_CM,
        bottom=page_rect.height - bottom_pt,
    )


def measure_legends(doc) -> dict[int, LegendPosition | None]:
    """Sucht je Liste die Messmarken; ``None`` = nicht eindeutig messbar.

    Nicht eindeutig: eine Marke fehlt oder kommt mehrfach vor, oder obere und
    untere Marke liegen auf verschiedenen Seiten (mehrseitige Liste).
    """
    found: dict[tuple[int, str], list[tuple[int, fitz.Rect]]] = {}
    for page_number, page in enumerate(doc):
        for link in page.get_links():
            uri = str(link.get("uri") or "")
            if not uri.startswith(LEGEND_PROBE_URI_PREFIX):
                continue
            index_text, _sep, edge = uri[len(LEGEND_PROBE_URI_PREFIX):].partition("/")
            if index_text.isdigit() and edge in {"top", "bottom"}:
                found.setdefault((int(index_text), edge), []).append((page_number, link["from"]))
    result: dict[int, LegendPosition | None] = {}
    for index in sorted({key[0] for key in found}):
        tops, bottoms = found.get((index, "top"), []), found.get((index, "bottom"), [])
        if len(tops) != 1 or len(bottoms) != 1 or tops[0][0] != bottoms[0][0]:
            result[index] = None
            continue
        result[index] = LegendPosition(tops[0][0], tops[0][1].y0, bottoms[0][1].y1)
    return result


def has_content_above(page, top_y: float, area: ContentArea) -> bool:
    """Ob auf der Seite im Satzspiegel Inhalt oberhalb von ``top_y`` endet.

    Berücksichtigt Text-, Bild- und Zeichenblöcke, deren Rechteck den Satzspiegel
    schneidet (Elemente nur im Rand, z. B. Lochmarken, zählen nicht).
    """
    rects = [fitz.Rect(block[:4]) for block in page.get_text("blocks")]
    rects += [fitz.Rect(info["bbox"]) for info in page.get_image_info()]
    rects += [fitz.Rect(drawing["rect"]) for drawing in page.get_drawings()]
    area_rect = fitz.Rect(area.left, area.top, area.right, area.bottom)
    return any(rect.intersects(area_rect) and rect.y1 <= top_y - TOLERANCE_PT for rect in rects)


def compute_shifts(doc, page_format: str, hole_punch_enabled: bool) -> dict[int, float]:
    """Verschiebung je Liste in pt (nur positive, sinnvolle Werte)."""
    shifts: dict[int, float] = {}
    for index, position in measure_legends(doc).items():
        if position is None:
            _LOG.info("Operatorenliste %s nicht eindeutig messbar (fehlend/mehrseitig) -- keine Verschiebung", index)
            continue
        page = doc[position.page]
        area = content_area(page.rect, page_format, hole_punch_enabled)
        if not has_content_above(page, position.top, area):
            continue
        shift = area.bottom - position.bottom - SAFETY_PT
        if shift > MIN_SHIFT_PT:
            shifts[index] = round(shift, 2)
    return shifts


def shift_style(shifts: dict[int, float]) -> str:
    """CSS, das die Wrapper der Listen per ``padding-top`` nach unten schiebt."""
    rules = "".join(f"#{LEGEND_ELEMENT_ID_PREFIX}{index}{{padding-top:{shift}pt;}}" for index, shift in sorted(shifts.items()))
    return f"<style>{rules}</style>"


def _inject_style(html: str, style: str) -> str:
    return html.replace("</head>", style + "</head>", 1) if "</head>" in html else style + html


def _pass2_is_safe(before, after, shifts, page_format, hole_punch_enabled) -> bool:
    if after.page_count != before.page_count:
        return False
    old_positions, new_positions = measure_legends(before), measure_legends(after)
    for index, old in old_positions.items():
        new = new_positions.get(index)
        if old is None or new is None or new.page != old.page:
            return False
        if index in shifts:
            area = content_area(after[new.page].rect, page_format, hole_punch_enabled)
            if new.bottom > area.bottom + TOLERANCE_PT:
                return False
    return True


def strip_probe_links(pdf_path: Path) -> None:
    """Entfernt nur die eigenen Messlinks aus dem PDF (andere Links bleiben)."""
    temp_path = pdf_path.with_name(pdf_path.stem + ".probe-strip.pdf")
    with fitz.open(pdf_path) as doc:
        removed = False
        for page in doc:
            for link in page.get_links():
                if str(link.get("uri") or "").startswith(LEGEND_PROBE_URI_PREFIX):
                    page.delete_link(link)
                    removed = True
        if not removed:
            return
        doc.save(temp_path, garbage=3, deflate=True)
    os.replace(temp_path, pdf_path)


def write_pdf_with_bottom_legends(html: str, out_pdf_path, *, page_format: str, hole_punch_enabled: bool, render=write_pdf_from_html) -> Path:
    """Druckt ``html`` als PDF und schiebt Operatorenlisten ans Seitenende (best-effort).

    Ohne Operatorenliste: identisch zu ``render`` (kein zweiter Druck).
    """
    pdf_path = Path(render(html, out_pdf_path))
    if LEGEND_PROBE_URI_PREFIX not in html:
        return pdf_path
    pass2_path = pdf_path.with_name(pdf_path.stem + ".legend-pass2.pdf")
    try:
        with fitz.open(pdf_path) as first:
            shifts = compute_shifts(first, page_format, hole_punch_enabled)
        if shifts:
            render(_inject_style(html, shift_style(shifts)), pass2_path)
            with fitz.open(pdf_path) as first, fitz.open(pass2_path) as second:
                safe = _pass2_is_safe(first, second, shifts, page_format, hole_punch_enabled)
            if safe:
                os.replace(pass2_path, pdf_path)
            else:
                _LOG.info("Operatorenliste: Pass 2 weicht ab (Seiten/Lage) -- Pass 1 bleibt")
    except Exception:  # Platzierung ist Komfort; Pass 1 bleibt in jedem Fehlerfall gültig
        _LOG.warning("Operatorenliste: Platzierung am Seitenende fehlgeschlagen -- Pass 1 bleibt", exc_info=True)
    finally:
        pass2_path.unlink(missing_ok=True)
    try:
        strip_probe_links(pdf_path)
    except Exception:
        _LOG.warning("Operatorenliste: Messlinks konnten nicht entfernt werden", exc_info=True)
    return pdf_path
