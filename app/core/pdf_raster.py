"""PDF-Seiten als Bilder und temporäre PDF-Arbeitsdateien.

Einzige Stelle für das Rastern: Vorschau, Kurzentwurf, Lernhilfen und PPTX nutzen diese
Funktionen, damit Seiten-Fortschritt und Abbruch-Prüfpunkt überall gleich wirken. Neue
PyMuPDF-Aufrufe zum Rastern gehören hierher.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from PIL import Image

from .render_job import stage, stage_progress
from .render_stages import STAGE_RASTER

PREVIEW_DPI = 150
"""Vorschau von Arbeitsblatt, Präsentation, Klausur, Schild, Markdown, Erwartungshorizont."""

KURZENTWURF_PREVIEW_DPI = 145
HELP_CARD_EXPORT_DPI = 200


def page_to_image(page, dpi: int) -> Image.Image:
    """Rastert eine PyMuPDF-Seite als RGB-Bild.

    Args:
        page: Geladene `fitz.Page`.
        dpi: Auflösung.
    """
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def rasterize_document(document, dpi: int) -> list[Image.Image]:
    """Rastert alle Seiten eines geöffneten Dokuments, mit Fortschritt je Seite.

    Args:
        document: Offenes `fitz.Document`, auch ein rein im Speicher gebautes.
        dpi: Auflösung.
    """
    total = document.page_count
    pages: list[Image.Image] = []
    with stage(STAGE_RASTER):
        for index in range(total):
            stage_progress(index, total)
            pages.append(page_to_image(document.load_page(index), dpi))
        stage_progress(total, total)
    return pages


def rasterize_pdf(pdf_path, dpi: int = PREVIEW_DPI) -> list[Image.Image]:
    """Öffnet eine PDF-Datei und rastert alle Seiten.

    Args:
        pdf_path: Pfad der PDF.
        dpi: Auflösung, Standard ist die der Vorschau.
    """
    import fitz  # erst hier: der Kurzentwurf behandelt fehlendes PyMuPDF selbst (KZF200)

    with fitz.open(Path(pdf_path)) as document:
        return rasterize_document(document, dpi)


@contextmanager
def temp_pdf_path() -> Iterator[Path]:
    """Liefert den Pfad einer leeren temporären PDF-Datei und löscht sie danach.

    Das Löschen ist best-effort: Eine kurz gesperrte Datei darf das Ergebnis oder einen
    Abbruch nicht überdecken.

    Example:
        >>> with temp_pdf_path() as path:
        ...     path.suffix
        '.pdf'
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        path = Path(handle.name)
    try:
        yield path
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
