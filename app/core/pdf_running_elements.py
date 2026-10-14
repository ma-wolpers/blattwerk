"""Laufende PDF-Elemente: Kopf-/Fusszeile, Seitenzahlen und Copyright nachtraeglich per
PyMuPDF in die von Chromium gedruckte PDF stempeln, inklusive Wiederholung bei
kurzzeitig gesperrten Dateien und einer Pruefung des Ergebnisses.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from ..styles.blatt_styles import resolve_pdf_running_colors
from .blatt_kern_shared import get_current_school_year_label

try:
    import fitz
except ImportError:
    fitz = None


LARGE_PAGE_MIN_LONG_SIDE_PT = 700
"""Ab dieser laengeren Seitenkante (pt) gilt das grosse Laufelement-Layout (A4 hoch/quer,
Folien); darunter das kompakte (A5 quer: 595 pt)."""


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
    return max(width_pt, height_pt) > LARGE_PAGE_MIN_LONG_SIDE_PT


def wait_for_file_stable(path, checks=8, delay_seconds=0.15):
    """Wartet, bis sich Dateigröße/mtime über zwei Messungen nicht mehr ändern."""

    path = Path(path)
    last_signature = None
    stable_hits = 0

    for _ in range(checks):
        if not path.exists():
            time.sleep(delay_seconds)
            continue

        stat = path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)

        if signature == last_signature:
            stable_hits += 1
            if stable_hits >= 1:
                return
        else:
            stable_hits = 0

        last_signature = signature
        time.sleep(delay_seconds)


def annotate_pdf_running_elements(
    pdf_path, title, copyright_text, print_profile="standard", include_solutions=False
):
    """
    Ergänzt Seitenzahlen und wiederholt den Titel auf Folgeseiten.

    - Footer: Seitenzahl auf jeder Seite unten rechts
    - Header (ab Seite 2): Titel oben links zur Zuordbarkeit
    """

    if fitz is None:
        return

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return

    running_colors = resolve_pdf_running_colors(print_profile)

    normalized_title = (title or "").replace("–", "-").replace("—", "-").strip()
    right_header_label = (
        "Lösungsversion" if include_solutions else get_current_school_year_label()
    )
    with fitz.open(pdf_path) as doc:
        page_count = doc.page_count
        if page_count <= 0:
            raise RuntimeError("PDF enthält noch keine Seiten.")

        side_inset = 22

        for index in range(page_count):
            page = doc.load_page(index)
            rect = page.rect

            is_a4_like = is_large_running_layout(rect.width, rect.height)

            if is_a4_like:
                side_inset = 32
                footer_top = rect.height - 34
                footer_bottom = rect.height - 16
                header_top = 16
                header_bottom = 36
                header_font_size = 11
                page_number_font_size = 15
                page_number_vertical_shift = 20
            else:
                side_inset = 22
                footer_top = rect.height - 24
                footer_bottom = rect.height - 10
                header_top = 10
                header_bottom = 30
                header_font_size = 9
                page_number_font_size = 12
                page_number_vertical_shift = 3

            footer_rect_left = fitz.Rect(
                side_inset,
                footer_top,
                rect.width - side_inset,
                footer_bottom,
            )
            page.insert_textbox(
                footer_rect_left,
                copyright_text,
                fontname="helv",
                fontsize=8,
                color=running_colors["footer_color"],
                align=fitz.TEXT_ALIGN_LEFT,
            )

            footer_rect_right = fitz.Rect(
                side_inset,
                footer_top,
                rect.width - side_inset,
                footer_bottom,
            )
            if page_count > 1:
                page_number_text = f"Seite {index + 1} von {page_count}"
                number_width = fitz.get_text_length(
                    page_number_text,
                    fontname="helv",
                    fontsize=page_number_font_size,
                )
                number_x = max(side_inset, rect.width - side_inset - number_width)
                number_y = footer_bottom - 1 - page_number_vertical_shift
                page.insert_text(
                    fitz.Point(number_x, number_y),
                    page_number_text,
                    fontname="helv",
                    fontsize=page_number_font_size,
                    color=(0.0, 0.0, 0.0),
                )

            if index > 0 and normalized_title:
                header_rect = fitz.Rect(
                    side_inset, header_top, rect.width - side_inset, header_bottom
                )
                page.insert_textbox(
                    header_rect,
                    normalized_title,
                    fontname="helv",
                    fontsize=header_font_size,
                    color=running_colors["running_title_color"],
                    align=fitz.TEXT_ALIGN_LEFT,
                )

            if index > 0 and right_header_label:
                header_rect = fitz.Rect(
                    side_inset, header_top, rect.width - side_inset, header_bottom
                )

                if include_solutions:
                    badge_text = "Lösungsversion"
                    badge_font_size = max(8, header_font_size - 1)
                    text_width = fitz.get_text_length(
                        badge_text, fontname="helv", fontsize=badge_font_size
                    )
                    horizontal_pad = 6
                    vertical_pad = 2
                    badge_width = text_width + (horizontal_pad * 2)
                    badge_height = max(12, (header_bottom - header_top) - 2)
                    badge_x1 = rect.width - side_inset
                    badge_x0 = max(side_inset, badge_x1 - badge_width)
                    badge_y0 = header_top + vertical_pad
                    badge_y1 = min(header_bottom - 1, badge_y0 + badge_height)
                    badge_rect = fitz.Rect(badge_x0, badge_y0, badge_x1, badge_y1)

                    page.draw_rect(
                        badge_rect,
                        color=(0.16, 0.38, 0.27),
                        fill=(0.92, 0.97, 0.93),
                        width=0.9,
                    )
                    page.insert_textbox(
                        badge_rect,
                        badge_text,
                        fontname="helv",
                        fontsize=badge_font_size,
                        color=(0.16, 0.38, 0.27),
                        align=fitz.TEXT_ALIGN_CENTER,
                    )
                else:
                    page.insert_textbox(
                        header_rect,
                        right_header_label,
                        fontname="helv",
                        fontsize=header_font_size,
                        color=running_colors["running_title_color"],
                        align=fitz.TEXT_ALIGN_RIGHT,
                    )

        fd, temp_name = tempfile.mkstemp(suffix=".pdf", dir=pdf_path.parent)
        temp_output = Path(temp_name)
        try:
            import os

            os.close(fd)
            doc.save(temp_output, garbage=4, deflate=True)
        except Exception:
            temp_output.unlink(missing_ok=True)
            raise

    temp_output.replace(pdf_path)


def annotate_pdf_running_elements_with_retry(
    pdf_path,
    title,
    copyright_text,
    print_profile="standard",
    include_solutions=False,
    attempts=6,
    delay_seconds=0.2,
):
    """Annotiert PDF-Laufelemente mit begrenztem Retry nur bei transienten I/O-Fehlern."""

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
            last_error = None
            break
        except Exception as error:
            last_error = error
            if not _is_transient_annotation_error(error):
                raise RuntimeError(
                    f"PDF-Annotation fehlgeschlagen (nicht transient): {error}"
                ) from error

            if attempt >= max(1, attempts):
                break

            wait_for_file_stable(pdf_path, checks=2, delay_seconds=delay_seconds)
    else:
        raise RuntimeError(f"PDF-Annotation fehlgeschlagen: {last_error}")

    for _ in range(max(1, attempts)):
        if verify_pdf_running_elements(pdf_path, title, copyright_text):
            return
        wait_for_file_stable(pdf_path, checks=2, delay_seconds=delay_seconds)

    raise RuntimeError("PDF-Annotation konnte nicht verifiziert werden.")


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


def verify_pdf_running_elements(pdf_path, title, copyright_text):
    """Prüft, ob Seitenzahlen (und optional der Lauf-Titel) im PDF nachweisbar sind."""

    if fitz is None:
        return True

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return False

    normalized_title = (title or "").replace("–", "-").replace("—", "-").strip()

    def simplify(text):
        return " ".join(
            (text or "").replace("–", "-").replace("—", "-").replace("-", " ").split()
        ).lower()

    with fitz.open(pdf_path) as doc:
        page_count = doc.page_count
        if page_count <= 0:
            return False

        if page_count > 1:
            first_text = doc[0].get_text()
            page_text_markers = {
                f"Seite 1 von {page_count}",
                f"1/{page_count}",
            }
            if not any(marker in first_text for marker in page_text_markers):
                return False

        if page_count > 1 and normalized_title:
            second_text = doc[1].get_text()
            if simplify(normalized_title) not in simplify(second_text):
                return False

    return True
