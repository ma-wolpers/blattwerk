"""Lernhilfen als Einzelseiten: Layout-HTML und Formatwahl A6 → A5 → A4.

Die Formatwahl wird ohne Chromium über einen Fake-Renderer geprüft, der je
Karte und Format eine vorgegebene Seitenzahl „druckt“ (inklusive Marker-Text,
wie der echte Druck). Ein End-to-End-Test mit echtem Chromium läuft nur, wenn
ein Browser vorhanden ist.
"""

from __future__ import annotations

import pytest

from app.core.blatt_kern_help_render import (
    HELP_CARD_LAYOUT_SINGLE,
    help_card_marker,
    render_help_cards_html,
)
from app.core.help_card_pages import HELP_CARD_SINGLE_PAGE_FORMATS, build_help_card_single_pages
from help_card_fakes import fake_help_card_render

META = {"Titel": "T", "Fach": "M", "Thema": "X"}


def _blocks(count):
    return [("help", {"title": f"Karte {index}"}, f"Inhalt {index}") for index in range(1, count + 1)]


def test_single_layout_html_has_container_and_marker_per_card():
    html = render_help_cards_html(META, _blocks(2), layout=HELP_CARD_LAYOUT_SINGLE, page_format="a6_portrait")

    assert '<div class="help-cards-single">' in html
    assert help_card_marker(1) in html and help_card_marker(2) in html
    assert "break-before: page" in html


def test_sheet_layout_has_no_markers():
    html = render_help_cards_html(META, _blocks(2), page_format="a4_portrait")

    assert "BWHC-" not in html.split("<body>", 1)[1]


def test_card_subset_keeps_labels_of_full_set():
    html = render_help_cards_html(META, _blocks(3), layout=HELP_CARD_LAYOUT_SINGLE, card_indices={2})

    assert "B - Karte 2" in html
    assert "Karte 1" not in html and "Karte 3" not in html
    assert help_card_marker(2) in html


def test_unknown_layout_is_rejected():
    with pytest.raises(ValueError):
        render_help_cards_html(META, _blocks(1), layout="grid")


def test_each_card_gets_smallest_fitting_format_in_document_order(tmp_path):
    pages_needed = {
        1: {"a6_portrait": 1, "a5_portrait": 1, "a4_portrait": 1},
        2: {"a6_portrait": 2, "a5_portrait": 1, "a4_portrait": 1},
        3: {"a6_portrait": 3, "a5_portrait": 2, "a4_portrait": 1},
    }
    calls = []

    result = build_help_card_single_pages(tmp_path, META, _blocks(3), render=fake_help_card_render(pages_needed, calls))

    try:
        assert [p.page_format for p in result.placements] == ["a6_portrait", "a5_portrait", "a4_portrait"]
        assert [p.first_page for p in result.placements] == [0, 1, 2]
        assert result.document.page_count == 3
        assert calls == list(HELP_CARD_SINGLE_PAGE_FORMATS)
        text = "".join(page.get_text() for page in result.document)
        assert "BWHC-" not in text
        assert text.index("Kartentext 1") < text.index("Kartentext 2") < text.index("Kartentext 3")
    finally:
        result.document.close()


def test_stops_after_first_format_when_everything_fits(tmp_path):
    pages_needed = {index: {fmt: 1 for fmt in HELP_CARD_SINGLE_PAGE_FORMATS} for index in (1, 2)}
    calls = []

    result = build_help_card_single_pages(tmp_path, META, _blocks(2), render=fake_help_card_render(pages_needed, calls))

    result.document.close()
    assert calls == ["a6_portrait"]


def test_card_too_long_even_for_a4_keeps_all_pages(tmp_path):
    pages_needed = {1: {"a6_portrait": 5, "a5_portrait": 4, "a4_portrait": 2}}

    result = build_help_card_single_pages(tmp_path, META, _blocks(1), render=fake_help_card_render(pages_needed, []))

    try:
        (placement,) = result.placements
        assert placement.page_format == "a4_portrait"
        assert placement.page_count == 2
    finally:
        result.document.close()


def test_no_visible_cards_returns_none(tmp_path):
    assert build_help_card_single_pages(tmp_path, META, [("task", {}, "Aufgabe")]) is None


def test_real_chromium_picks_a6_for_short_and_larger_for_long_card(tmp_path):
    """End-to-end mit echtem Druck: kurze Karte auf A6, sehr lange Karte größer."""
    from app.core.blatt_kern_io_pdf import find_chromium_executable

    if find_chromium_executable() is None:
        pytest.skip("kein Chromium-Browser fuer den PDF-Druck")
    long_text = "\n\n".join(f"Absatz {k}: Lorem ipsum dolor sit amet, consectetur adipiscing elit." for k in range(25))
    blocks = [("help", {"title": "Kurz"}, "Ein Satz."), ("help", {"title": "Lang"}, long_text)]

    result = build_help_card_single_pages(tmp_path, META, blocks)

    try:
        short, long_card = result.placements
        assert short.page_format == "a6_portrait"
        assert long_card.page_format != "a6_portrait"
        assert result.document[0].rect.width == pytest.approx(298, abs=2)
        assert "BWHC-" not in "".join(page.get_text() for page in result.document)
    finally:
        result.document.close()
