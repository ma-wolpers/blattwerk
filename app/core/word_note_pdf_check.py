"""Nachrender-Plausibilitätsprüfung für Worterklärungen im fertigen PDF (Diagnose `IM003`).

Blattwerk hat keinen Seitenumbruch-Schätzer vor dem Rendern (der Umbruch
passiert im Browser). Wie `PT002` für Präsentationen (siehe
`blatt_kern_io_build.py`) wird daher NACH dem Rendern gemessen: PyMuPDF sucht
die Erklärung in der rechten Randspalte des PDFs.

Prüfregeln pro Worterklärung (nicht-blockierende Warnung, kein Fehler):
- Erster und letzter Textbestandteil der Erklärung müssen in der Randspalte
  gefunden werden. Fehlt einer, steht die Erklärung nicht am Rand (z. B. in
  einer Tabellenzelle oder in `:::columns`) oder wurde nicht gerendert.
- Beide müssen auf derselben Seite stehen. Beginnt die Erklärung auf einer
  Seite und endet auf der nächsten, passte sie nicht mehr vollständig an
  ihre Stelle. Sie wird dabei weder abgeschnitten noch erzwingt sie einen
  Seitenumbruch (Browser-Druck setzt sie auf der Folgeseite fort); die
  Warnung macht den Autor darauf aufmerksam.

Bewusst eine Best-Effort-Prüfung, kein Beweis für "sieht perfekt aus": sie
erkennt nicht, wenn eine Erklärung auf derselben Seite optisch weit vom
Begriff entfernt steht. Ändert sich das Spaltenlayout (`page_geometry.py`),
passt die Randspalten-Grenze automatisch mit.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from ..styles.blatt_styles import (
    PAGE_LAYOUTS,
    _css_length_to_cm,
    _layout_page_width_cm,
    resolve_page_side_margins_cm,
)
from ..styles.page_geometry import WORD_NOTE_GUTTER_CM
from .blatt_validator_types import BuildDiagnostic
from .inline_markup.runs import IM003_WORD_NOTE_PLACEMENT

_POINTS_PER_CM = 72.0 / 2.54
_TOKEN_STRIP_CHARS = ".,;:!?()[]\"'„“”‚‘’»«"
_GUTTER_EDGE_TOLERANCE_CM = 0.1


def _normalize_token(token: str) -> str:
    return token.strip(_TOKEN_STRIP_CHARS).casefold()


def _explanation_tokens(explanation: str) -> tuple[str, str] | None:
    """Erstes und letztes Wort der Erklärung (normalisiert), oder `None` ohne Wort."""
    tokens = [_normalize_token(part) for part in explanation.split()]
    tokens = [token for token in tokens if token]
    if not tokens:
        return None
    return tokens[0], tokens[-1]


def _gutter_words_per_page(doc, gutter_x0_pt: float, top_pt: float, bottom_pt: float) -> list[set[str]]:
    """Normalisierte Wörter je Seite, die rechts von `gutter_x0_pt` im Inhaltsbereich stehen."""
    pages: list[set[str]] = []
    for page in doc:
        words = set()
        for x0, y0, _x1, y1, text, *_rest in page.get_text("words"):
            if x0 >= gutter_x0_pt and y0 >= top_pt and y1 <= page.rect.height - bottom_pt:
                normalized = _normalize_token(text)
                if normalized:
                    words.add(normalized)
        pages.append(words)
    return pages


def _dedupe(word_notes) -> list:
    seen = set()
    unique = []
    for note in word_notes:
        key = (note.term, note.explanation)
        if key not in seen:
            seen.add(key)
            unique.append(note)
    return unique


def append_word_note_placement_warnings(
    *,
    diagnostics_out,
    pdf_path,
    word_notes,
    page_format: str,
    hole_punch_enabled: bool,
) -> None:
    """Hängt je auffälliger Worterklärung eine `IM003`-Warnung an `diagnostics_out` an."""
    if diagnostics_out is None or not word_notes:
        return

    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    _left_cm, right_cm = resolve_page_side_margins_cm(page_format, hole_punch_enabled)
    gutter_x0_pt = (
        _layout_page_width_cm(layout) - right_cm - WORD_NOTE_GUTTER_CM + _GUTTER_EDGE_TOLERANCE_CM
    ) * _POINTS_PER_CM
    top_pt = _css_length_to_cm(layout["page_margin_top_css"], 2.0) * _POINTS_PER_CM
    bottom_pt = _css_length_to_cm(layout["page_margin_bottom_css"], 1.5) * _POINTS_PER_CM

    try:
        with fitz.open(Path(pdf_path)) as doc:
            gutter_words = _gutter_words_per_page(doc, gutter_x0_pt, top_pt, bottom_pt)
    except Exception:
        return

    for note in _dedupe(word_notes):
        tokens = _explanation_tokens(note.explanation)
        if tokens is None:
            continue
        first_token, last_token = tokens
        first_pages = {i for i, words in enumerate(gutter_words) if first_token in words}
        last_pages = {i for i, words in enumerate(gutter_words) if last_token in words}

        if not first_pages or not last_pages:
            message = (
                f"Die Erklärung zu \"{note.term}\" wurde nicht in der rechten Randspalte des PDFs "
                "gefunden (in Tabellenzellen und `:::columns` erscheint sie nicht am Seitenrand). "
                "Bitte im PDF prüfen."
            )
        elif not (first_pages & last_pages):
            message = (
                f"Die Erklärung zu \"{note.term}\" passt nicht vollständig auf die Seite ihres "
                "Absatzes und läuft auf der nächsten Seite weiter. Kürzere Erklärung oder ein "
                "anderer Begriff/Absatz vermeidet das."
            )
        else:
            continue

        diagnostics_out.append(
            BuildDiagnostic(
                code=IM003_WORD_NOTE_PLACEMENT,
                message=message,
                severity="warning",
                anchor="word_note_placement",
            )
        )
