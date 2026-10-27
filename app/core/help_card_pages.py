"""Lernhilfen als Einzelseiten: jede Karte auf einer Seite im kleinsten passenden Format.

Chromium druckt ein HTML-Dokument immer in *einem* Seitenformat
(`write_pdf_from_html`). Statt jede Karte einzeln und je Format neu zu drucken
(bis zu 3 × Kartenzahl Druckläufe), rendert `build_help_card_single_pages`
alle noch offenen Karten gemeinsam in einem Lauf je Format
(`HELP_CARD_SINGLE_PAGE_FORMATS`, kleinstes zuerst) und findet die
Seitenspanne jeder Karte über einen unsichtbaren Marker am Kartenanfang
wieder (`help_card_marker`). Eine Karte passt, wenn sie genau eine Seite
belegt; die übrigen gehen in den nächsten Lauf. Höchstens drei Druckläufe.

GRENZE: Eine Karte, die selbst auf DIN A4 nicht auf eine Seite passt, wird
über mehrere A4-Seiten übernommen (kein Verkleinern der Schrift, damit sie
gut lesbar bleibt).
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import fitz

from .blatt_kern_help_render import (
    HELP_CARD_LAYOUT_SINGLE,
    HELP_CARD_MARKER_PREFIX,
    collect_labeled_help_blocks,
    help_card_marker,
    render_help_cards_html,
)
from .blatt_kern_io_html import absolutize_local_image_sources, apply_image_size_options
from .blatt_kern_io_pdf import write_pdf_from_html

HELP_CARD_SINGLE_PAGE_FORMATS = ("a6_portrait", "a5_portrait", "a4_portrait")
"""Kandidatenformate für „Jede Lernhilfe auf eigener Seite“, kleinstes zuerst.
Einzige Quelle dieser Reihenfolge; das letzte Format nimmt jede verbliebene
Karte auf, auch wenn sie darauf mehrere Seiten braucht."""

_MARKER_PATTERN = re.compile(re.escape(HELP_CARD_MARKER_PREFIX) + r"(\d{4})")


@dataclass(frozen=True)
class HelpCardPlacement:
    """Wo eine Karte im Ergebnis-PDF liegt.

    Attributes:
        index: 1-basierte Kartennummer in Dokumentreihenfolge.
        label: sichtbares Kartenlabel (z. B. ``"A"``) oder ``None``.
        page_format: gewähltes Format aus `HELP_CARD_SINGLE_PAGE_FORMATS`.
        first_page: 0-basierte erste Seite der Karte in `HelpCardPages.document`.
        page_count: Seitenzahl der Karte (1, außer im GRENZE-Fall auf A4).
    """

    index: int
    label: str | None
    page_format: str
    first_page: int
    page_count: int


@dataclass
class HelpCardPages:
    """Ergebnis von `build_help_card_single_pages`.

    `document` enthält die Kartenseiten in Dokumentreihenfolge (Seiten
    unterschiedlicher Größe); der Aufrufer besitzt es und schließt es.
    """

    document: fitz.Document
    placements: tuple[HelpCardPlacement, ...]


def render_help_cards_print_html(md_dir, meta, blocks, **render_kwargs):
    """Karten-HTML fertig zum Druck: Rendern plus Bildpfade/Bildgrößen auflösen.

    Gemeinsamer Schritt für den Sammelseiten-Export (`build_help_cards`) und
    die Einzelseiten (`build_help_card_single_pages`), damit beide lokale
    Bilder gleich behandeln.

    Args:
        md_dir: Ordner der Quelldatei; relative Bildpfade werden darauf bezogen.
        meta, blocks: geparstes Dokument (siehe `load_help_card_source`).
        **render_kwargs: werden an `render_help_cards_html` durchgereicht
            (`include_solutions`, `page_format`, Profile, `layout`, `card_indices`).
    """
    html = render_help_cards_html(meta, blocks, **render_kwargs)
    html = absolutize_local_image_sources(html, Path(md_dir))
    return apply_image_size_options(html)


def build_help_card_single_pages(
    md_dir,
    meta,
    blocks,
    *,
    include_solutions=False,
    print_profile="standard",
    color_profile="indigo",
    font_profile="segoe",
    font_size_profile="normal",
    render=write_pdf_from_html,
):
    """Druckt jede sichtbare Karte auf eine eigene Seite im kleinsten passenden Format.

    Args:
        md_dir: Ordner der Quelldatei (für relative Bildpfade).
        meta, blocks: geparstes Dokument, z. B. aus `load_help_card_source`
            oder direkt aus dem laufenden Arbeitsblatt-Build.
        include_solutions: Kartensichtbarkeit wie in der Lösungsfassung.
        print_profile, color_profile, font_profile, font_size_profile: Design
            wie beim Arbeitsblatt.
        render: HTML→PDF-Funktion ``(html, out_path) -> Path``; Tests können
            einen Fake einsetzen.

    Returns:
        `HelpCardPages`; ``None``, wenn keine Karte sichtbar ist.
    """
    labeled = collect_labeled_help_blocks(meta, blocks, include_solutions=include_solutions)
    if not labeled:
        return None

    pending = list(range(1, len(labeled) + 1))
    chosen: dict[int, tuple[str, fitz.Document, int, int]] = {}
    printed: list[fitz.Document] = []
    try:
        for position, page_format in enumerate(HELP_CARD_SINGLE_PAGE_FORMATS):
            is_last_format = position == len(HELP_CARD_SINGLE_PAGE_FORMATS) - 1
            html = render_help_cards_print_html(
                md_dir,
                meta,
                blocks,
                include_solutions=include_solutions,
                page_format=page_format,
                print_profile=print_profile,
                color_profile=color_profile,
                font_profile=font_profile,
                font_size_profile=font_size_profile,
                layout=HELP_CARD_LAYOUT_SINGLE,
                card_indices=set(pending),
            )
            document = _print_to_document(html, render)
            printed.append(document)
            spans = _card_page_spans(document, pending)
            _remove_markers(document)
            still_pending = []
            for index in pending:
                first, last = spans[index]
                if first == last or is_last_format:
                    chosen[index] = (page_format, document, first, last)
                else:
                    still_pending.append(index)
            pending = still_pending
            if not pending:
                break
        return _assemble(labeled, chosen)
    finally:
        for document in printed:
            document.close()


def _print_to_document(html, render):
    """Druckt `html` in eine Temp-PDF und lädt sie als In-Memory-`fitz.Document`."""
    with tempfile.TemporaryDirectory(prefix="blattwerk-help-") as tmp_dir:
        pdf_path = Path(tmp_dir) / "help-cards.pdf"
        render(html, pdf_path)
        return fitz.open(stream=pdf_path.read_bytes(), filetype="pdf")


def _card_page_spans(document, indices):
    """Ordnet jeder Kartennummer ihre Seitenspanne ``(erste, letzte)`` (0-basiert) zu.

    Eine Karte reicht von der Seite ihres Markers bis vor die Seite des
    nächsten Markers bzw. bis zur letzten Seite. Fehlt ein erwarteter Marker,
    ist das ein Renderfehler (z. B. verschluckter Text) und wird nicht still
    übergangen.
    """
    starts: dict[int, int] = {}
    for page in document:
        for match in _MARKER_PATTERN.finditer(page.get_text()):
            starts.setdefault(int(match.group(1)), page.number)
    missing = [index for index in indices if index not in starts]
    if missing:
        raise RuntimeError(f"Lernhilfen-Seitenmarker fehlen im PDF: {missing}")

    ordered = sorted(indices, key=lambda index: starts[index])
    spans = {}
    for position, index in enumerate(ordered):
        following = ordered[position + 1] if position + 1 < len(ordered) else None
        last = starts[following] - 1 if following is not None else document.page_count - 1
        spans[index] = (starts[index], max(starts[index], last))
    return spans


def _remove_markers(document):
    """Schwärzt die Marker rückstandslos weg; Bilder und Linien bleiben unberührt."""
    for page in document:
        hits = []
        for match in _MARKER_PATTERN.finditer(page.get_text()):
            hits.extend(page.search_for(help_card_marker(int(match.group(1)))))
        if not hits:
            continue
        for rect in hits:
            page.add_redact_annot(rect)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)


def _assemble(labeled, chosen):
    """Setzt die gewählten Seiten in Dokumentreihenfolge zu einem neuen PDF zusammen."""
    result = fitz.open()
    placements = []
    for index in sorted(chosen):
        page_format, source, first, last = chosen[index]
        first_page = result.page_count
        result.insert_pdf(source, from_page=first, to_page=last)
        placements.append(
            HelpCardPlacement(
                index=index,
                label=labeled[index - 1].get("label"),
                page_format=page_format,
                first_page=first_page,
                page_count=last - first + 1,
            )
        )
    return HelpCardPages(document=result, placements=tuple(placements))


__all__ = [
    "HELP_CARD_SINGLE_PAGE_FORMATS",
    "HelpCardPages",
    "HelpCardPlacement",
    "build_help_card_single_pages",
    "render_help_cards_print_html",
]
