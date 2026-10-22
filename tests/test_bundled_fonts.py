"""Mitgelieferte OFL-Schriften (Wunschliste Schritt 5a).

Katalog, Dateien und Lizenzen muessen uebereinstimmen; `@font-face` deklariert nur
vorhandene Schnitte, nur fuer benutzte Familien und jede hoechstens einmal; im PDF
landet die konkrete Familie.
"""

from __future__ import annotations

import pytest

from app.styles.blatt_styles import FONT_PROFILE_PRESETS, build_font_profile_css
from app.styles.bundled_fonts import BUNDLED_FONTS, FONTS_DIR, font_face_css


def test_every_catalog_face_and_license_exists_and_nothing_is_uncatalogued():
    """Jede Datei im Katalog existiert, jede Familie hat ihre Lizenz, keine Datei ist unkatalogisiert."""
    catalogued = set()
    for font in BUNDLED_FONTS:
        assert font.license_path.is_file(), font.key
        assert "SIL Open Font License" in font.license_path.read_text(encoding="utf-8")
        for face in font.faces:
            path = FONTS_DIR / face.path
            assert path.is_file(), face.path
            assert path.resolve().is_relative_to(FONTS_DIR.resolve())
            catalogued.add(path.resolve())
    on_disk = {p.resolve() for p in FONTS_DIR.rglob("*.ttf")}
    assert on_disk == catalogued


def test_faces_declare_exactly_one_weight_kind():
    """Statische Schnitte haben ein Gewicht, nur der Variable Font einen Bereich."""
    for font in BUNDLED_FONTS:
        for face in font.faces:
            assert (face.weight is None) != (face.weight_range is None), face.path
            assert face.style in {"normal", "italic"}


def test_font_face_css_only_for_requested_families_once_each():
    """Nur angefragte Familien, jede Datei genau einmal; unbekannte Schluessel werden ignoriert."""
    css = font_face_css(["patrick_hand", "patrick_hand", "unbekannt"])
    assert css.count("@font-face") == 1
    assert "font-family: 'Patrick Hand'" in css
    assert "Comic Neue" not in css
    assert font_face_css([]) == ""


def test_comic_neue_declares_its_real_faces_only():
    """Comic Neue: Light/Regular/Bold je normal und kursiv -- sechs Regeln mit passenden Gewichten."""
    css = font_face_css(["comic_neue"])
    assert css.count("@font-face") == 6
    for weight in ("300", "400", "700"):
        assert f"font-weight: {weight};" in css
    assert css.count("font-style: italic;") == 3


def test_fredoka_is_declared_as_weight_range():
    """Der Variable Font deklariert den Gewichtsbereich statt Einzelschnitten."""
    css = font_face_css(["fredoka"])
    assert css.count("@font-face") == 1
    assert "font-weight: 300 700;" in css


def test_bundled_fonts_are_selectable_profiles_and_embedded_when_selected():
    """Die Fonts sind Schriftprofile; das Profil-CSS bettet nur den gewaehlten Font ein."""
    for font in BUNDLED_FONTS:
        assert font.key in FONT_PROFILE_PRESETS
    css = build_font_profile_css("andika")
    assert "--font-family-base: 'Andika'" in css
    assert css.count("@font-face") == 4
    assert "@font-face" not in build_font_profile_css("segoe")


def _render_pdf_fonts(tmp_path, font_profile):
    fitz = pytest.importorskip("fitz")
    from app.core.blatt_kern_io_build import build_worksheet
    from app.core.blatt_kern_io_pdf import find_chromium_executable

    if find_chromium_executable() is None:
        pytest.skip("kein Chromium-Browser fuer den PDF-Druck")
    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: Schrift\nFach: M\nThema: T\n---\n:::task\nAufgabe mit Text\n:::\n", encoding="utf-8")
    out = tmp_path / f"{font_profile}.pdf"
    build_worksheet(source, out, font_profile=font_profile, document_type="worksheet", block_on_critical=False)
    with fitz.open(out) as doc:
        return doc[0].get_fonts(full=True)


def test_pdf_embeds_the_bundled_family(tmp_path):
    """Im PDF steht die konkrete Familie (nicht irgendeine eingebettete Schrift)."""
    names = {entry[3] for entry in _render_pdf_fonts(tmp_path, "comic_neue")}
    assert any(name.endswith("ComicNeue-Regular") for name in names), names


def test_pdf_embeds_fredoka_instances(tmp_path):
    """Fredoka (Variable Font) landet als eigene Type3-Instanz im PDF (siehe GRENZE in bundled_fonts)."""
    fonts = _render_pdf_fonts(tmp_path, "fredoka")
    assert any(entry[2] == "Type3" for entry in fonts), fonts
