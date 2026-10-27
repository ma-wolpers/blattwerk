"""Lernhilfen als Einzelbilder: eine Karte = ein beschnittenes Bild.

Gemeinsame Quelle für den PNG-/PNG-ZIP-Export der Lernhilfen und das
Lernhilfen-Vorschaufenster. Beide brauchen *eine Karte pro Bild*; die Seiten
dafür liefert `help_card_pages.build_help_card_single_pages` (je Karte das
kleinste passende Format A6/A5/A4), sodass auch lange Karten vollständig
erscheinen statt nach der ersten A6-Seite abgeschnitten zu werden.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..core.blatt_kern_io_build import load_help_card_source
from ..core.help_card_pages import build_help_card_single_pages
from .help_card_image_trim import trim_lernhilfe_image


def render_help_card_images(
    input_path: Path,
    *,
    include_solutions: bool,
    contrast_profile: str,
    design,
    dpi: int,
    metadata_defaults: dict[str, str] | None = None,
    block_on_critical: bool = False,
) -> list[Image.Image]:
    """Rendert jede sichtbare Lernhilfe als eigenes, auf die Karte beschnittenes Bild.

    Args:
        input_path: Quelldatei.
        include_solutions: Kartensichtbarkeit wie in der Lösungsfassung.
        contrast_profile: Druck-/Kontrastprofil (`print_profile`).
        design: `WorksheetDesignOptions` der aktuellen Ansicht.
        dpi: Rasterauflösung (Export 200, Vorschaufenster 150).
        metadata_defaults: App-Vorgaben für fehlende Frontmatter-Felder.
        block_on_critical: blockierende Diagnosen werfen `ValueError`; das
            Vorschaufenster zeigt trotz Fehlern an (``False``).

    Returns:
        Bilder in Dokumentreihenfolge; leer ohne sichtbare Karte. Eine Karte,
        die selbst auf A4 mehr als eine Seite braucht (GRENZE in
        `help_card_pages`), wird aus ihren Seiten untereinander zusammengesetzt.
    """
    md_file, meta, blocks = load_help_card_source(
        input_path,
        metadata_defaults=metadata_defaults,
        block_on_critical=block_on_critical,
    )
    pages = build_help_card_single_pages(
        md_file.parent,
        meta,
        blocks,
        include_solutions=include_solutions,
        print_profile=contrast_profile,
        color_profile=design.color_profile,
        font_profile=design.font_profile,
        font_size_profile=design.font_size_profile,
    )
    if pages is None:
        return []
    try:
        images = []
        for placement in pages.placements:
            card_pages = [
                _page_to_image(pages.document[number], dpi)
                for number in range(placement.first_page, placement.first_page + placement.page_count)
            ]
            images.append(trim_lernhilfe_image(_stack_vertically(card_pages)))
        return images
    finally:
        pages.document.close()


def _page_to_image(page, dpi: int) -> Image.Image:
    """Rastert eine PDF-Seite (`fitz.Page`) zu einem RGB-Bild."""
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _stack_vertically(images: list[Image.Image]) -> Image.Image:
    """Setzt Bilder linksbündig untereinander auf weißen Grund (ein Bild bleibt unverändert)."""
    if len(images) == 1:
        return images[0]
    width = max(image.width for image in images)
    stacked = Image.new("RGB", (width, sum(image.height for image in images)), "white")
    top = 0
    for image in images:
        stacked.paste(image, (0, top))
        top += image.height
    return stacked
