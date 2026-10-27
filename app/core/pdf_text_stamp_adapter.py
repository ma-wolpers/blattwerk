"""PyMuPDF-Adapter fuer die PDF-Laufelemente (Kopf-/Fusszeile, Seitenzahl, Badge).

Einzige Stelle, die fuer die Laufelemente PyMuPDF-APIs benennt (`fitz.open`,
`Font.text_length`/`has_glyph`, `insert_textbox`, `insert_text`, `draw_rect`, `save`).
`pdf_running_elements.py` kennt nur diese Funktionen; aendert sich das Verhalten einer
PyMuPDF-Version, ist nur diese Datei betroffen.

Verifizierte PyMuPDF-Eigenheiten (1.27), auf denen die Funktionen hier aufbauen:

- ``insert_textbox`` fuegt *nichts* ein, wenn der Text nicht in die Box passt, und
  meldet das nur ueber einen negativen Rueckgabewert. `stamp_line` kuerzt deshalb vorab
  auf eine Zeile und wirft bei ``rc < 0`` statt still zu verschlucken.
- Die Font-Bbox von TTF-Dateien (z. B. Andika) ist hoeher als die Kopfzeilenbox; ohne
  feste ``lineheight`` verwirft ``insert_textbox`` den Text ebenfalls.
- Zeichen ohne Glyphe (Emoji) werden als ``.notdef`` gestempelt (Textextraktion: ``\\x00``).
"""

from __future__ import annotations

import os
import tempfile
import unicodedata
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

try:
    import fitz
except ImportError:
    fitz = None

PYMUPDF_AVAILABLE = fitz is not None
TRUNCATION_MARK = "..."
STAMP_LINE_HEIGHT = 1.2
"""Feste Zeilenhoehe (Vielfaches der Schriftgroesse) statt der zu hohen TTF-Bbox."""

ALIGN_LEFT = "left"
ALIGN_CENTER = "center"
ALIGN_RIGHT = "right"
_FITZ_ALIGN = {ALIGN_LEFT: 0, ALIGN_CENTER: 1, ALIGN_RIGHT: 2}  # fitz.TEXT_ALIGN_*

_CLUSTER_EXTENDERS = {"Mn", "Me", "Cf", "Sk"}
"""Unicode-Kategorien, die an ein vorangehendes Basiszeichen gebunden sind (Kombinations-
zeichen, Variation Selector U+FE0F, ZWJ U+200D, Hautton-Modifikatoren)."""


class StampError(RuntimeError):
    """Ein Laufelement konnte nicht gestempelt werden (statt still zu fehlen)."""


@lru_cache(maxsize=None)
def load_stamp_font(font_file: str):
    """Laedt eine Schriftdatei einmal als PyMuPDF-Font (gecacht je Pfad).

    Args:
        font_file: Absoluter Pfad einer TTF-Datei als String (hashbar fuer den Cache).
    """
    return fitz.Font(fontfile=font_file)


def text_width(font_file: str, text: str, size: float) -> float:
    """Breite von ``text`` in pt fuer die Schrift ``font_file`` in Groesse ``size``."""
    return load_stamp_font(font_file).text_length(text, fontsize=size)


def renderable_text(font_file: str, text: str) -> str:
    """Entfernt Zeichencluster, fuer die die Schrift keine Glyphe hat, und glaettet Leerraum.

    Ein Cluster ist ein Basiszeichen plus direkt folgende Erweiterungszeichen
    (`_CLUSTER_EXTENDERS`). Fehlt die Glyphe des Basiszeichens, faellt der ganze Cluster
    weg - sonst bliebe z. B. der Variation Selector hinter einem Emoji stehen, fuer den
    manche Schriften eine (unsichtbare) Glyphe haben. ZWJ-Sequenzen (👨‍👩‍👧) zerfallen in
    Basiszeichen + ZWJ-Erweiterungen und verschwinden damit vollstaendig.

    Example:
        >>> from app.styles.bundled_fonts import bundled_font_file
        >>> renderable_text(str(bundled_font_file("andika")), "☀️ Phishing – Δx")
        'Phishing – Δx'
    """
    font = load_stamp_font(font_file)
    kept: list[str] = []
    dropping = False
    for ch in text or "":
        if ch.isspace():
            kept.append(" ")
            dropping = False
        elif unicodedata.category(ch) in _CLUSTER_EXTENDERS and (dropping or not kept):
            dropping = True
        elif font.has_glyph(ord(ch)):
            kept.append(ch)
            dropping = False
        else:
            dropping = True
    return " ".join("".join(kept).split())


def fit_single_line(font_file: str, text: str, max_width: float, size: float) -> str:
    """Kuerzt ``text`` mit ``...``, bis er in einer Zeile in ``max_width`` pt passt.

    Returns:
        Den (ggf. gekuerzten) Text oder ``""``, wenn nicht einmal ``...`` passt.

    Example:
        >>> from app.styles.bundled_fonts import bundled_font_file
        >>> fit_single_line(str(bundled_font_file("andika")), "Kurz", 200, 11)
        'Kurz'
    """
    font = load_stamp_font(font_file)
    if font.text_length(text, fontsize=size) <= max_width:
        return text
    cut = text
    while cut and font.text_length(cut.rstrip() + TRUNCATION_MARK, fontsize=size) > max_width:
        cut = cut[:-1]
    return cut.rstrip() + TRUNCATION_MARK if cut else ""


def stamp_line(page, box, text, *, font_file, size, color, align=ALIGN_LEFT) -> str:
    """Stempelt genau eine Zeile Text in ``box``: Glyphen filtern, kuerzen, einfuegen.

    Args:
        page: PyMuPDF-Seite aus `open_pdf_pages`.
        box: ``(x0, y0, x1, y1)`` in pt.
        text: Rohtext (darf Emoji, Sonderzeichen und Ueberlaenge enthalten).
        font_file: Schriftdatei (String) - eine Schrift fuer alle Laufelemente.
        size: Schriftgroesse in pt.
        color: RGB-Tupel 0..1.
        align: `ALIGN_LEFT`/`ALIGN_CENTER`/`ALIGN_RIGHT`.

    Returns:
        Den tatsaechlich gestempelten Text (``""`` = nichts zu stempeln).

    Raises:
        StampError: PyMuPDF meldet trotz Vorab-Kuerzung, dass der Text nicht passt.
    """
    x0, y0, x1, y1 = box
    fitted = fit_single_line(font_file, renderable_text(font_file, text), x1 - x0, size)
    if not fitted:
        return ""
    rc = page.insert_textbox(
        fitz.Rect(x0, y0, x1, y1),
        fitted,
        fontname=_font_alias(font_file),
        fontfile=font_file,
        fontsize=size,
        lineheight=STAMP_LINE_HEIGHT,
        color=color,
        align=_FITZ_ALIGN[align],
    )
    if rc < 0:
        raise StampError(f"Laufelement passt nicht in die Box ({rc:.1f} pt): {fitted!r}")
    return fitted


def stamp_text_at(page, x, y, text, *, font_file, size, color) -> None:
    """Stempelt ``text`` mit Grundlinie bei ``(x, y)`` (fuer die Seitenzahl)."""
    page.insert_text(
        fitz.Point(x, y),
        text,
        fontname=_font_alias(font_file),
        fontfile=font_file,
        fontsize=size,
        color=color,
    )


def draw_box(page, box, *, stroke, fill, width) -> None:
    """Zeichnet ein gefuelltes Rechteck ``(x0, y0, x1, y1)`` (Loesungs-Badge)."""
    page.draw_rect(fitz.Rect(*box), color=stroke, fill=fill, width=width)


@contextmanager
def open_pdf_pages(pdf_path):
    """Oeffnet eine PDF, liefert ``(pages, page_size)`` und speichert sie danach in-place.

    Gespeichert wird ueber eine Geschwisterdatei plus ``os.replace``, weil PyMuPDF eine
    geoeffnete Datei nicht ueber sich selbst schreiben kann. Bei einem Fehler im Block
    wird nichts gespeichert und die Geschwisterdatei geloescht.

    Yields:
        Liste von ``(page, (width_pt, height_pt))``.

    Raises:
        StampError: Die PDF hat keine Seiten.
    """
    pdf_path = Path(pdf_path)
    with fitz.open(pdf_path) as doc:
        if doc.page_count <= 0:
            raise StampError("PDF enthält noch keine Seiten.")
        yield [(page, (page.rect.width, page.rect.height)) for page in doc]
        fd, temp_name = tempfile.mkstemp(suffix=".pdf", dir=pdf_path.parent)
        os.close(fd)
        temp_output = Path(temp_name)
        try:
            doc.save(temp_output, garbage=4, deflate=True)
        except Exception:
            temp_output.unlink(missing_ok=True)
            raise
    try:
        temp_output.replace(pdf_path)
    except OSError:
        temp_output.unlink(missing_ok=True)
        raise


def _font_alias(font_file: str) -> str:
    """Kurzer, stabiler Fontname je Datei fuer die PDF-Ressourcen der Seite."""
    return "bw-" + Path(font_file).stem.lower()
