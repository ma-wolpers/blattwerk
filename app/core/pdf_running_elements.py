"""Laufende PDF-Elemente: Kopf-/Fusszeile, Seitenzahlen und Copyright nachtraeglich in
die von Chromium gedruckte PDF stempeln.

Fachliche Regeln (was wo steht) leben hier; Geometrie und Schrift sind Daten in
`app/styles/blatt_styles_data.py` (`RUNNING_ELEMENT_LAYOUTS`, `RUNNING_ELEMENT_FONT_KEY`,
`RUNNING_BADGE_STYLE`), alle PyMuPDF-Aufrufe im Adapter `pdf_text_stamp_adapter.py`.

Alle Laufelemente nutzen *eine* mitgelieferte Unicode-Schrift. Zeichen ohne Glyphe
(Emoji) entfallen, zu lange Texte werden auf eine Zeile gekuerzt, und ein Element, das
trotzdem nicht passt, wirft `StampError` - es fehlt nie still.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..styles.blatt_styles import (
    RUNNING_BADGE_STYLE,
    RUNNING_ELEMENT_FONT_KEY,
    RUNNING_ELEMENT_GAP_PT,
    RUNNING_ELEMENT_LAYOUTS,
    RUNNING_LARGE_MIN_LONG_SIDE_PT,
    resolve_pdf_running_colors,
)
from ..styles.bundled_fonts import bundled_font_file
from .blatt_kern_shared import get_current_school_year_label
from .pdf_text_stamp_adapter import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    PYMUPDF_AVAILABLE,
    draw_box,
    open_pdf_pages,
    stamp_line,
    stamp_text_at,
    text_width,
)

PAGE_NUMBER_COLOR = (0.0, 0.0, 0.0)


def is_large_running_layout(width_pt: float, height_pt: float) -> bool:
    """Decide whether a page gets the large running-elements layout.

    The longer page edge decides, so A4 landscape (842 x 595 pt) is treated like A4
    portrait. Checking only the height (the former rule) put A4 landscape into the
    compact A5 layout with small header/footer fonts.

    Args:
        width_pt: Page width in PDF points.
        height_pt: Page height in PDF points.

    Example:
        >>> is_large_running_layout(842, 595), is_large_running_layout(595, 420)
        (True, False)
    """
    return max(width_pt, height_pt) > RUNNING_LARGE_MIN_LONG_SIDE_PT


def running_layout(width_pt: float, height_pt: float) -> dict:
    """Absolute Geometrie (pt) der Laufelemente fuer eine Seite.

    Rechnet die seitenunabhaengigen Daten aus `RUNNING_ELEMENT_LAYOUTS` (Abstaende ab
    Unterkante) in absolute Koordinaten um.

    Example:
        >>> running_layout(595, 842)["footer_bottom"]
        826
    """
    data = RUNNING_ELEMENT_LAYOUTS["large" if is_large_running_layout(width_pt, height_pt) else "compact"]
    layout = dict(data)
    layout["width"] = width_pt
    layout["footer_top"] = height_pt - data["footer_top_from_bottom"]
    layout["footer_bottom"] = height_pt - data["footer_bottom_from_bottom"]
    return layout


def running_font_file() -> str:
    """Schriftdatei aller Laufelemente (Katalog `bundled_fonts`, Schluessel aus den Daten)."""
    return str(bundled_font_file(RUNNING_ELEMENT_FONT_KEY))


def normalize_running_title(title) -> str:
    """Titel fuer die Kopfzeile: Gedankenstriche zu ``-``, Rand-Leerraum weg.

    Example:
        >>> normalize_running_title("  A – B ")
        'A - B'
    """
    return (title or "").replace("–", "-").replace("—", "-").strip()


def wait_for_file_stable(path, checks=8, delay_seconds=0.15):
    """Wartet, bis sich Dateigröße/mtime über zwei Messungen nicht mehr ändern."""

    path = Path(path)
    last_signature = None

    for _ in range(checks):
        if not path.exists():
            time.sleep(delay_seconds)
            continue

        stat = path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        if signature == last_signature:
            return
        last_signature = signature
        time.sleep(delay_seconds)


def annotate_pdf_running_elements(
    pdf_path, title, copyright_text, print_profile="standard", include_solutions=False
):
    """Stempelt Copyright, Seitenzahlen und (ab Seite 2) Titel und Kopf-Label in die PDF.

    - Fusszeile: Copyright links, "Seite i von n" rechts (nur bei mehreren Seiten).
    - Kopfzeile ab Seite 2: Titel links zur Zuordbarkeit; rechts das Schuljahr oder
      in der Loesungsfassung ein Badge "Lösungsversion".

    Ohne PyMuPDF oder ohne Datei passiert nichts (bisheriges Verhalten).

    Raises:
        StampError: Ein Element passt trotz Kuerzung nicht oder die PDF ist leer.
    """
    pdf_path = Path(pdf_path)
    if not PYMUPDF_AVAILABLE or not pdf_path.exists():
        return

    colors = resolve_pdf_running_colors(print_profile)
    font_file = running_font_file()
    title_text = normalize_running_title(title)
    right_label = RUNNING_BADGE_STYLE["text"] if include_solutions else get_current_school_year_label()

    with open_pdf_pages(pdf_path) as pages:
        page_count = len(pages)
        for index, (page, (width, height)) in enumerate(pages):
            layout = running_layout(width, height)
            _stamp_footer(page, layout, font_file, copyright_text or "", index, page_count, colors)
            if index > 0:
                _stamp_header(page, layout, font_file, title_text, right_label, include_solutions, colors)


def _stamp_footer(page, layout, font_file, copyright_text, index, page_count, colors):
    """Fusszeile einer Seite: Seitenzahl rechts, Copyright links im verbleibenden Platz.

    Die Seitenzahl kommt zuerst, damit das Copyright um ihre Breite plus Abstand
    gekuerzt werden kann, statt sie zu ueberlappen.
    """
    reserved = 0.0
    if page_count > 1:
        number_text = f"Seite {index + 1} von {page_count}"
        size = layout["page_number_font_size"]
        number_width = text_width(font_file, number_text, size)
        x = max(layout["side_inset"], layout["width"] - layout["side_inset"] - number_width)
        y = layout["footer_bottom"] - layout["page_number_baseline_lift"]
        stamp_text_at(page, x, y, number_text, font_file=font_file, size=size, color=PAGE_NUMBER_COLOR)
        reserved = number_width + RUNNING_ELEMENT_GAP_PT

    box = (
        layout["side_inset"],
        layout["footer_top"],
        max(layout["side_inset"] + 1, layout["width"] - layout["side_inset"] - reserved),
        layout["footer_bottom"],
    )
    stamp_line(
        page, box, copyright_text,
        font_file=font_file, size=layout["footer_font_size"], color=colors["footer_color"], align=ALIGN_LEFT,
    )


def _stamp_header(page, layout, font_file, title_text, right_label, include_solutions, colors):
    """Kopfzeile ab Seite 2: rechtes Label/Badge zuerst, dann der Titel im Restplatz."""
    left = layout["side_inset"]
    right = layout["width"] - layout["side_inset"]
    top, bottom = layout["header_top"], layout["header_bottom"]
    size = layout["header_font_size"]

    label_width = 0.0
    if include_solutions:
        label_width = _stamp_solution_badge(page, layout, font_file)
    elif right_label:
        label_width = text_width(font_file, right_label, size)
        stamp_line(
            page, (left, top, right, bottom), right_label,
            font_file=font_file, size=size, color=colors["running_title_color"], align=ALIGN_RIGHT,
        )

    if title_text:
        reserved = label_width + RUNNING_ELEMENT_GAP_PT if label_width else 0.0
        stamp_line(
            page, (left, top, max(left + 1, right - reserved), bottom), title_text,
            font_file=font_file, size=size, color=colors["running_title_color"], align=ALIGN_LEFT,
        )


def _stamp_solution_badge(page, layout, font_file) -> float:
    """Zeichnet das Badge "Lösungsversion" rechts in die Kopfzeile.

    Returns:
        Die Badge-Breite in pt, damit der Titel links davor Platz laesst.
    """
    style = RUNNING_BADGE_STYLE
    size = max(8, layout["header_font_size"] - 1)
    width = text_width(font_file, style["text"], size) + 2 * style["horizontal_pad"]
    top, bottom = layout["header_top"], layout["header_bottom"]
    x1 = layout["width"] - layout["side_inset"]
    x0 = max(layout["side_inset"], x1 - width)
    y0 = top + style["vertical_pad"]
    y1 = min(bottom - 1, y0 + max(style["min_height"], (bottom - top) - 2))

    draw_box(page, (x0, y0, x1, y1), stroke=style["stroke"], fill=style["fill"], width=style["stroke_width"])
    stamp_line(
        page, (x0, y0, x1, y1), style["text"],
        font_file=font_file, size=size, color=style["stroke"], align=ALIGN_CENTER,
    )
    return width


def annotate_pdf_running_elements_with_retry(
    pdf_path,
    title,
    copyright_text,
    print_profile="standard",
    include_solutions=False,
    attempts=6,
    delay_seconds=0.2,
):
    """Annotiert PDF-Laufelemente mit begrenztem Retry nur bei transienten I/O-Fehlern.

    Bleibt die Datei gesperrt (z. B. im Viewer offen), kommt eine Klartext-Meldung statt
    eines Folgefehlers. Frueher fiel dieser Fall durch bis zu einer nachgelagerten
    Pruefung und meldete irrefuehrend "nicht verifiziert".
    """
    last_error = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            annotate_pdf_running_elements(
                pdf_path,
                title,
                copyright_text,
                print_profile=print_profile,
                include_solutions=include_solutions,
            )
            return
        except Exception as error:
            if not _is_transient_annotation_error(error):
                raise RuntimeError(
                    f"PDF-Annotation fehlgeschlagen (nicht transient): {error}"
                ) from error
            last_error = error
            if attempt < max(1, attempts):
                wait_for_file_stable(pdf_path, checks=2, delay_seconds=delay_seconds)

    raise RuntimeError(
        "PDF konnte nicht überschrieben werden – ist sie noch in einem anderen "
        f"Programm geöffnet? ({last_error})"
    ) from last_error


def _is_transient_annotation_error(error):
    """Erkennt typische temporäre Dateizugriffsfehler beim Schreiben/Ersetzen."""

    if isinstance(error, PermissionError):
        return True

    if isinstance(error, OSError):
        winerror = getattr(error, "winerror", None)
        if winerror in {5, 32, 33}:
            return True

    message = str(error).lower()
    transient_markers = (
        "access is denied",
        "permission denied",
        "being used by another process",
        "resource busy",
        "device or resource busy",
    )
    return any(marker in message for marker in transient_markers)
