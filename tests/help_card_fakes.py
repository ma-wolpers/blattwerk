"""Fake-Druck für Lernhilfen-Tests ohne Chromium (gemeinsam genutzt).

`fake_help_card_render` ersetzt `write_pdf_from_html`: Es liest das letzte
`@page`-Format (wie der Browser: der Format-Override folgt dem Basis-CSS) und
„druckt“ je Karte (`data-help-index`) eine vorgegebene Seitenzahl, die erste
Seite mit dem Marker-Text wie im echten Einzelseiten-Druck.
"""

from __future__ import annotations

import re

import fitz

from app.core.blatt_kern_help_render import help_card_marker
from app.styles.blatt_styles import PAGE_LAYOUTS

_PAGE_SIZE_RE = re.compile(r"@page\s*\{[^}]*?\bsize:\s*([^;]+);")
_SIZE_TO_FORMAT = {layout["page_size_css"]: name for name, layout in PAGE_LAYOUTS.items()}
_SIZE_TO_FORMAT["A4 portrait"] = "a4_portrait"
_POINTS = {"a4_portrait": (595, 842), "a5_portrait": (420, 595), "a6_portrait": (298, 420)}


def fake_help_card_render(pages_needed=None, calls=None):
    """Liefert eine Render-Funktion ``(html, out_path) -> out_path``.

    Args:
        pages_needed: ``{kartennummer: {format: seitenzahl}}``; fehlt ein
            Eintrag, braucht die Karte eine Seite.
        calls: optionale Liste, in die jedes gedruckte Format geschrieben wird.
    """

    def render(html, out_path):
        size_css = _PAGE_SIZE_RE.findall(html)[-1].strip()
        page_format = _SIZE_TO_FORMAT.get(size_css, "a4_portrait")
        if calls is not None:
            calls.append(page_format)
        width, height = _POINTS.get(page_format, (595, 842))
        doc = fitz.open()
        for index in [int(value) for value in re.findall(r'data-help-index="(\d+)"', html)]:
            for page_number in range((pages_needed or {}).get(index, {}).get(page_format, 1)):
                page = doc.new_page(width=width, height=height)
                if page_number == 0:
                    page.insert_text((2, 4), help_card_marker(index), fontsize=2)
                page.insert_text((20, 40), f"Kartentext {index}", fontsize=8)
        doc.save(out_path)
        doc.close()
        return out_path

    return render
