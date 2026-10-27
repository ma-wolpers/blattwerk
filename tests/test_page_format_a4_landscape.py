"""Seitenformat "A4 quer" fuer Arbeitsblatt und Klausur (Wunschliste Schritt 4).

Abgesichert werden der Formatkatalog als einzige Quelle, das CSS-Seitenlayout, der
Vertrag Vorschau -> Export (kein stiller Rueckfall auf Hochformat), die
Kopf-/Fusszeilen-Heuristik, die PPTX-Seitengroessen und die Zahlenstrahl-Breite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import app.ui.blatt_ui_export_dialogs as dialogs_module
from app.core.answer_numberline_scale import _resolve_max_width_mm
from app.core.blatt_kern_pptx_export import _PAGE_SIZE_CM, _slide_size_emu
from app.core.pdf_running_elements import is_large_running_layout
from app.storage.user_preferences_adapter import PREFERENCE_SPECS
from app.styles.blatt_styles import (
    PAGE_LAYOUTS,
    PRESENTATION_PAGE_FORMATS,
    WORKSHEET_PAGE_FORMAT_LABELS,
    WORKSHEET_PAGE_FORMATS,
    build_page_layout_css,
    resolve_printable_height_cm,
    resolve_printable_width_cm,
)
from app.ui.blatt_ui_export import BlattwerkAppExportMixin
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin
from app.ui.export_defaults import (
    _ALLOWED_PRESENTATION_PAGE_FORMATS,
    _ALLOWED_WORKSHEET_PAGE_FORMATS,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_catalog_is_the_single_source_for_all_format_lists():
    """Export-Normalisierung, Praeferenzwerte, Layouts und PPTX-Groessen folgen dem Katalog."""
    assert "a4_landscape" in WORKSHEET_PAGE_FORMATS
    assert _ALLOWED_WORKSHEET_PAGE_FORMATS == set(WORKSHEET_PAGE_FORMATS)
    assert _ALLOWED_PRESENTATION_PAGE_FORMATS == set(PRESENTATION_PAGE_FORMATS)
    assert PREFERENCE_SPECS["default_export_page_format_worksheet"]["values"] == list(WORKSHEET_PAGE_FORMATS)
    assert PREFERENCE_SPECS["default_export_page_format_presentation"]["values"] == list(PRESENTATION_PAGE_FORMATS)
    for page_format in (*WORKSHEET_PAGE_FORMATS, *PRESENTATION_PAGE_FORMATS):
        assert page_format in PAGE_LAYOUTS
        assert page_format in _PAGE_SIZE_CM
    assert set(WORKSHEET_PAGE_FORMAT_LABELS) == set(WORKSHEET_PAGE_FORMATS)


def test_a4_landscape_page_css_and_printable_area():
    """`@page` ist A4 quer; die druckbare Flaeche ist breiter als hoch und breiter als A4 hoch."""
    css = build_page_layout_css("a4_landscape")
    assert "A4 landscape" in css
    width = resolve_printable_width_cm("a4_landscape")
    height = resolve_printable_height_cm("a4_landscape")
    assert width > height
    assert width > resolve_printable_width_cm("a4_portrait")
    assert width == pytest.approx(29.7 - 1.5 - 1.5)


@pytest.mark.parametrize(
    ("document_type", "requested", "expected"),
    [
        ("worksheet", "a4_landscape", "a4_landscape"),
        ("exam", "a4_landscape", "a4_landscape"),
        ("presentation", "a4_landscape", "presentation_16_9"),
    ],
)
def test_preview_keeps_a4_landscape_only_for_worksheet_types(document_type, requested, expected):
    """Die Vorschau akzeptiert A4 quer bei Arbeitsblatt/Klausur, Praesentationen fallen auf ein Folienformat."""

    class _Host(BlattwerkAppPreviewMixin):
        pass

    assert _Host()._resolve_preview_page_format_for_document_type(requested, document_type) == expected


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def test_worksheet_export_uses_the_landscape_preview_format(monkeypatch, tmp_path):
    """Steht die Vorschau auf A4 quer, exportiert der PDF-Export in A4 quer (kein Hochformat-Fallback)."""
    captured = {}

    class FakeDialog:
        def __init__(self, *_args, **_kwargs):
            self.result = {"format": "pdf", "mode": "worksheet", "output_path": str(tmp_path / "out.pdf")}

    def fake_export_pdf(_input, _output, page_format, *_args, **_kwargs):
        captured["page_format"] = page_format
        raise RuntimeError("stop after capture")

    monkeypatch.setattr(dialogs_module, "WorksheetExportDialog", FakeDialog)
    monkeypatch.setattr(dialogs_module.messagebox, "showerror", lambda *_a, **_k: None)

    class _Host(BlattwerkAppExportMixin):
        def _effective_help_appendix(self):
            return "none"

    host = _Host()
    host.user_preferences = {}
    host.root = type("_Root", (), {"update_idletasks": lambda self: None})()
    host.theme_var = _Var("light")
    host.status_var = _Var("")
    host.preview_mode_var = _Var("worksheet")
    host.preview_page_format_var = _Var("a4_landscape")
    host.preview_contrast_var = _Var("standard")
    host._get_initial_dialog_dir = lambda _purpose: None
    host._set_last_dialog_dir = lambda *_args: None
    host._detect_document_type = lambda _path: "worksheet"
    host._solutions_renderable_for_type = lambda _type: True
    host._show_export_diagnostics = lambda _path: None
    host._export_pdf = fake_export_pdf

    host.open_worksheet_export_dialog(input_path=Path("blatt.abw"))

    assert captured["page_format"] == "a4_landscape"


@pytest.mark.parametrize(
    ("width_pt", "height_pt", "large"),
    [
        (595, 842, True),  # A4 hoch
        (842, 595, True),  # A4 quer
        (595, 420, False),  # A5 quer
    ],
)
def test_running_elements_layout_follows_the_longer_page_edge(width_pt, height_pt, large):
    """A4 quer bekommt Kopf/Fuss wie A4 hoch, A5 bleibt kompakt."""
    assert is_large_running_layout(width_pt, height_pt) is large


def test_pptx_slide_size_knows_landscape_and_rejects_unknown_formats():
    """A4 quer hat eine Groesse; ein unbekanntes Format faellt nicht still auf 16:9."""
    width, height = _slide_size_emu("a4_landscape")
    assert width > height
    with pytest.raises(ValueError):
        _slide_size_emu("letter")


@pytest.mark.parametrize(
    ("options", "expected_mm"),
    [
        ({"_printable_width_cm": 26.7}, 267.0),  # A4 quer
        ({"_printable_width_cm": 18.0}, 180.0),  # A4 hoch
        ({"_printable_width_cm": 19.8}, 198.0),  # A5 quer
        ({"_printable_width_cm": 26.7, "max_width_cm": "10"}, 100.0),  # explizit gewinnt
        ({}, 165.0),  # ohne Laufzeitkontext: historischer Wert
    ],
)
def test_numberline_max_width_follows_the_printable_width(options, expected_mm):
    """Der Zahlenstrahl nutzt die druckbare Breite statt fest 165 mm."""
    assert _resolve_max_width_mm(options) == pytest.approx(expected_mm)


def test_numberline_never_exceeds_its_column():
    """CSS begrenzt das Feld auf die Breite des umgebenden Containers (z. B. einer Spalte)."""
    css = (REPO_ROOT / "assets" / "worksheet.css").read_text(encoding="utf-8")
    block = css.split(".answer.numberline {", 1)[1].split("}", 1)[0]
    assert "max-width: 100%" in block


def test_landscape_worksheet_pdf_has_landscape_pages(tmp_path):
    """End-to-end: ein Arbeitsblatt in A4 quer ergibt Querformat-Seiten mit A4-Kopf/Fuss."""
    fitz = pytest.importorskip("fitz")
    from app.core.blatt_kern_io_build import build_worksheet
    from app.core.blatt_kern_io_pdf import find_chromium_executable

    if find_chromium_executable() is None:
        pytest.skip("kein Chromium-Browser fuer den PDF-Druck")
    source = tmp_path / "blatt.abw"
    source.write_text(
        "---\nTitel: Quer\nFach: M\nThema: T\n---\n:::task\nAufgabe\n:::\n:::numberline\nmin: 0\nmax: 40\n:::\n",
        encoding="utf-8",
    )
    out = tmp_path / "blatt.pdf"
    build_worksheet(source, out, page_format="a4_landscape", document_type="worksheet", block_on_critical=False)
    with fitz.open(out) as doc:
        rect = doc[0].rect
        assert rect.width > rect.height
        assert rect.width == pytest.approx(842, abs=2)
        assert is_large_running_layout(rect.width, rect.height)
