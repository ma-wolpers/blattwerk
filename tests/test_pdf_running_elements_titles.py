"""Lauf-Titel in der PDF-Kopfzeile ueberstehen schwierige Titel.

Frueher brach der Export mit "PDF-Annotation konnte nicht verifiziert werden." ab, weil
``insert_textbox`` zu lange (zweizeilige) Titel still verwarf und Emoji bzw. Zeichen
ausserhalb von WinAnsi als ``.notdef``/``?`` gestempelt wurden. Abgesichert wird, dass
lesbarer Text gestempelt wird und ein trotzdem nicht passendes Element laut scheitert.
"""

from __future__ import annotations

import pytest

fitz = pytest.importorskip("fitz")

from app.core.pdf_running_elements import (  # noqa: E402
    annotate_pdf_running_elements,
    running_font_file,
)
from app.core.pdf_text_stamp_adapter import (  # noqa: E402
    StampError,
    open_pdf_pages,
    renderable_text,
    stamp_line,
)

PAGE_SIZES = {"a4": (595, 842), "a4_quer": (842, 595), "a5_quer": (595, 420)}
TITLES = {
    "emoji": ("☀️ Expertengruppe Phishing", "Expertengruppe Phishing"),
    "greek": ("Kräfte – Δx und α-Strahlung", "Δx und α-Strahlung"),
    "long": ("Photosynthese und Zellatmung im Vergleich – " * 4, "..."),
}


def _two_page_pdf(path, width, height):
    """Write an empty two-page PDF of the given size."""
    doc = fitz.open()
    doc.new_page(width=width, height=height)
    doc.new_page(width=width, height=height)
    doc.save(path)
    doc.close()


def _page_text(path, index):
    """Extract the text of one page."""
    with fitz.open(path) as doc:
        return doc[index].get_text()


@pytest.mark.parametrize("size", PAGE_SIZES)
@pytest.mark.parametrize("kind", TITLES)
def test_difficult_titles_are_stamped_readably(tmp_path, size, kind):
    """Page 2 carries the readable title fragment, no .notdef or '?' boxes."""
    pdf = tmp_path / "blatt.pdf"
    _two_page_pdf(pdf, *PAGE_SIZES[size])
    title, expected_fragment = TITLES[kind]

    annotate_pdf_running_elements(pdf, title, "© Test")

    header_text = _page_text(pdf, 1)
    assert expected_fragment in header_text
    assert "\x00" not in header_text and "?" not in header_text
    assert "Seite 1 von 2" in _page_text(pdf, 0)


def test_solution_badge_and_long_title_share_the_header(tmp_path):
    """The badge is stamped and a long title is shortened instead of dropped."""
    pdf = tmp_path / "loesung.pdf"
    _two_page_pdf(pdf, 595, 842)

    annotate_pdf_running_elements(pdf, "Sehr langer Titel " * 10, "© Test", include_solutions=True)

    header_text = _page_text(pdf, 1)
    assert "Lösungsversion" in header_text
    assert "Sehr langer Titel" in header_text and "..." in header_text


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("☀️ Phishing", "Phishing"),
        ("👨‍👩‍👧 Familie", "Familie"),
        ("👍🏽 Daumen", "Daumen"),
        ("Café Δ", "Café Δ"),
    ],
)
def test_renderable_text_drops_whole_emoji_clusters(raw, expected):
    """Variation selectors, ZWJ and skin-tone modifiers vanish with their emoji."""
    assert renderable_text(running_font_file(), raw) == expected


def test_stamp_line_raises_instead_of_dropping_silently(tmp_path):
    """A box too low for one line raises StampError (formerly: text silently missing)."""
    pdf = tmp_path / "eng.pdf"
    _two_page_pdf(pdf, 595, 842)

    with pytest.raises(StampError):
        with open_pdf_pages(pdf) as pages:
            page, _ = pages[0]
            stamp_line(page, (20, 20, 300, 22), "Zu niedrige Box", font_file=running_font_file(), size=11, color=(0, 0, 0))
