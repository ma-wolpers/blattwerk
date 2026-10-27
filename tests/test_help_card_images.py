"""Lernhilfen als Einzelbilder: eine Karte = ein Bild, mehrseitige Karte gestapelt."""

from __future__ import annotations

import fitz

import app.ui.help_card_images as images_module
from app.core.help_card_pages import HelpCardPages, HelpCardPlacement


class _Design:
    color_profile = "indigo"
    font_profile = "segoe"
    font_size_profile = "normal"


def _fake_pages(*_args, **_kwargs):
    doc = fitz.open()
    for _ in range(3):
        page = doc.new_page(width=100, height=140)
        page.draw_rect(fitz.Rect(5, 5, 95, 135), color=(0, 0, 0), fill=(0.2, 0.2, 0.2))
    placements = (
        HelpCardPlacement(index=1, label="A", page_format="a6_portrait", first_page=0, page_count=1),
        HelpCardPlacement(index=2, label="B", page_format="a4_portrait", first_page=1, page_count=2),
    )
    return HelpCardPages(document=doc, placements=placements)


def test_one_image_per_card_and_multi_page_card_is_stacked(monkeypatch, tmp_path):
    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: T\n---\n:::help\nx\n:::\n", encoding="utf-8")
    monkeypatch.setattr(images_module, "build_help_card_single_pages", _fake_pages)

    images = images_module.render_help_card_images(
        source, include_solutions=False, contrast_profile="standard", design=_Design(), dpi=72
    )

    assert len(images) == 2
    assert images[1].height > 1.8 * images[0].height


def test_no_cards_gives_no_images(monkeypatch, tmp_path):
    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: T\n---\n:::task\nx\n:::\n", encoding="utf-8")

    assert images_module.render_help_card_images(
        source, include_solutions=False, contrast_profile="standard", design=_Design(), dpi=72
    ) == []
