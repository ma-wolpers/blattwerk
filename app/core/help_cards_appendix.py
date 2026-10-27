"""Lernhilfen-Anhang: Karten hinter den Arbeitsblattseiten derselben PDF.

Einzige Quelle für die Anhang-Varianten (Tokens, Anzeigetexte, für welche
Dokumenttypen es den Anhang gibt) und für das Anhängen selbst. Der Anhang
wird in `build_worksheet` auf der Staging-Arbeitsdatei angehängt, *nach* den
Laufelementen -- damit wirkt er in PDF-Export, PNG-Export und Vorschau
gleich (alle drei rastern bzw. veröffentlichen dieselbe PDF).

GRENZE: Anhangsseiten tragen keine Kopf-/Fußzeile; „Seite X von Y“ auf dem
Arbeitsblatt zählt nur die Arbeitsblattseiten.
GRENZE: Die Sammelseite läuft bei vielen oder langen Karten auf weitere
Seiten über.
GRENZE: Der HTML-Export hat keinen Anhang (kein Seitenmodell).
GRENZE: Eine PDF mit gemischten Papierformaten (A4 + A6/A5) wird je nach
Druckdialog skaliert oder auf das eingelegte Papier gedruckt.
"""

from __future__ import annotations

import os
from pathlib import Path

import fitz

from .blatt_kern_help_render import HELP_CARD_LAYOUT_SHEET, collect_labeled_help_blocks
from .blatt_kern_io_pdf import write_pdf_from_html
from .document_type_registry import PIPELINE_WORKSHEET, spec_for_type
from .help_card_pages import (
    build_help_card_single_pages,
    print_html_to_document,
    render_help_cards_print_html,
)

HELP_APPENDIX_NONE = "none"
HELP_APPENDIX_SHEET = "sheet"
"""„Alle Lernhilfen auf einer Seite“: Sammelseite im Arbeitsblattformat."""
HELP_APPENDIX_SINGLE = "single"
"""„Jede Lernhilfe auf eigener Seite“: je Karte das kleinste passende Format."""
HELP_APPENDIX_MODES = (HELP_APPENDIX_NONE, HELP_APPENDIX_SHEET, HELP_APPENDIX_SINGLE)

HELP_APPENDIX_LABELS = {
    HELP_APPENDIX_NONE: ("Aus", "Keine Lernhilfen"),
    HELP_APPENDIX_SHEET: ("Eine Seite", "Alle Lernhilfen auf einer Seite"),
    HELP_APPENDIX_SINGLE: ("Einzeln", "Jede Lernhilfe auf eigener Seite"),
}
"""Anzeigetexte je Variante: ``(kurz für die Vorschau-Leiste, lang für den Exportdialog)``."""


def help_appendix_label(mode: str, *, short: bool) -> str:
    """Anzeigetext einer Variante (`short=True` für die Vorschau-Leiste)."""
    short_label, long_label = HELP_APPENDIX_LABELS[mode]
    return short_label if short else long_label


def coerce_help_appendix(mode) -> str:
    """Gültiges Token oder `HELP_APPENDIX_NONE` (z. B. für alten Tab-Zustand)."""
    return mode if mode in HELP_APPENDIX_MODES else HELP_APPENDIX_NONE


def help_appendix_supported(document_type: str | None) -> bool:
    """Ob ein Dokumenttyp den Lernhilfen-Anhang anbietet.

    Arbeitsblatt-Pipeline ohne Folien-Layout, also Arbeitsblatt und Klausur.
    Präsentationen nicht: Lernhilfen sind dort veraltet (`BL012`).
    """
    try:
        spec = spec_for_type(document_type)
    except KeyError:
        return False
    return spec.pipeline == PIPELINE_WORKSHEET and not spec.slide_layout


def ensure_help_appendix_request(mode: str, *, document_type: str, output_suffix: str) -> None:
    """Prüft den Vertrag *vor* dem Build; die UI bietet ungültige Kombinationen gar nicht an.

    Raises:
        ValueError: unbekannte Variante, Anhang an einem Typ ohne Anhang
            (`help_appendix_supported`) oder an einer HTML-Ausgabe.
    """
    if mode not in HELP_APPENDIX_MODES:
        raise ValueError(f"Unbekannte Lernhilfen-Anhang-Variante: {mode!r}")
    if mode == HELP_APPENDIX_NONE:
        return
    if not help_appendix_supported(document_type):
        raise ValueError(f"Lernhilfen-Anhang gibt es für den Dokumenttyp {document_type!r} nicht.")
    if output_suffix.lower() != ".pdf":
        raise ValueError("Lernhilfen-Anhang gibt es nur für PDF-Ausgaben.")


def append_help_cards_appendix(
    pdf_path,
    *,
    mode: str,
    md_dir,
    meta,
    blocks,
    include_solutions: bool,
    page_format: str,
    print_profile: str,
    color_profile: str,
    font_profile: str,
    font_size_profile: str,
    render=write_pdf_from_html,
) -> int:
    """Hängt die sichtbaren Lernhilfen in Dokumentreihenfolge an `pdf_path` an.

    Args:
        pdf_path: fertige Arbeitsblatt-PDF (Staging-Arbeitsdatei); wird ersetzt.
        mode: `HELP_APPENDIX_SHEET` oder `HELP_APPENDIX_SINGLE`
            (`HELP_APPENDIX_NONE` hängt nichts an).
        md_dir, meta, blocks: das bereits geparste Dokument des Builds -- kein
            zweites Lesen/Validieren.
        include_solutions: Kartensichtbarkeit wie in der jeweiligen Fassung.
        page_format: Format des Arbeitsblatts; nur die Sammelseite nutzt es.
        print_profile, color_profile, font_profile, font_size_profile: Design.
        render: HTML→PDF-Funktion (Tests).

    Returns:
        Anzahl angehängter Seiten (0 ohne sichtbare Karte).
    """
    if mode == HELP_APPENDIX_NONE:
        return 0
    if not collect_labeled_help_blocks(meta, blocks, include_solutions=include_solutions):
        return 0
    design = {
        "print_profile": print_profile,
        "color_profile": color_profile,
        "font_profile": font_profile,
        "font_size_profile": font_size_profile,
    }
    if mode == HELP_APPENDIX_SINGLE:
        pages = build_help_card_single_pages(
            md_dir, meta, blocks, include_solutions=include_solutions, render=render, **design
        )
        appendix = pages.document
    else:
        html = render_help_cards_print_html(
            md_dir,
            meta,
            blocks,
            include_solutions=include_solutions,
            page_format=page_format,
            layout=HELP_CARD_LAYOUT_SHEET,
            **design,
        )
        appendix = print_html_to_document(html, render)
    try:
        return _append_document(Path(pdf_path), appendix)
    finally:
        appendix.close()


def _append_document(pdf_path: Path, appendix) -> int:
    """Hängt `appendix` an `pdf_path` an und ersetzt die Datei atomar.

    PyMuPDF kann eine geöffnete Datei nicht nicht-inkrementell auf sich selbst
    speichern; deshalb Geschwisterdatei + `os.replace` (die Arbeitsdatei liegt
    im privaten Staging-Ordner, siehe `export_staging`).
    """
    temp_path = pdf_path.with_name(pdf_path.stem + ".appendix.pdf")
    with fitz.open(pdf_path) as document:
        document.insert_pdf(appendix)
        document.save(temp_path, garbage=3, deflate=True)
    os.replace(temp_path, pdf_path)
    return appendix.page_count
