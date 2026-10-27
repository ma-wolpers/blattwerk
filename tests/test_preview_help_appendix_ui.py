"""Lernhilfen-Anhang in der Vorschau: wirksamer Wert, Cache-Key, Tab-Zustand, Maßstab.

Keine echten Tk-Widgets: Fake-Variablen und -Buttons wie in
`test_preview_variants_ui.py`.
"""

from __future__ import annotations

from PIL import Image

from app.core.document_type_registry import DOCUMENT_TYPE_EXAM, DOCUMENT_TYPE_PRESENTATION, DOCUMENT_TYPE_WORKSHEET
from app.core.help_cards_appendix import HELP_APPENDIX_NONE, HELP_APPENDIX_SHEET, HELP_APPENDIX_SINGLE
from app.ui.blatt_ui_build_preview_help import BlattwerkPreviewHelpAppendixMixin
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin
from app.ui.blatt_ui_style_view import BlattwerkAppStyleViewMixin
from test_tab_font_size_state import _DummyBase


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Host(BlattwerkAppPreviewMixin):
    def __init__(self, document_type, appendix, variant="worksheet"):
        self._current_preview_document_type = document_type
        self.preview_help_appendix_var = _Var(appendix)
        self.preview_mode_var = _Var(variant)
        self.preview_black_screen_var = _Var("none")
        self.preview_section_separator_var = _Var("dot")
        self.preview_hide_future_sections_var = _Var(False)
        self.design_color_profile_var = _Var("indigo")
        self.design_font_profile_var = _Var("segoe")
        self.design_font_size_profile_var = _Var("normal")


def test_effective_value_follows_radios_only_where_the_appendix_exists():
    assert _Host(DOCUMENT_TYPE_WORKSHEET, HELP_APPENDIX_SINGLE)._effective_help_appendix() == HELP_APPENDIX_SINGLE
    assert _Host(DOCUMENT_TYPE_EXAM, HELP_APPENDIX_SHEET)._effective_help_appendix() == HELP_APPENDIX_SHEET
    assert _Host(DOCUMENT_TYPE_PRESENTATION, HELP_APPENDIX_SINGLE)._effective_help_appendix() == HELP_APPENDIX_NONE
    assert _Host(DOCUMENT_TYPE_EXAM, HELP_APPENDIX_SINGLE, "expectation")._effective_help_appendix() == HELP_APPENDIX_NONE
    assert _Host(DOCUMENT_TYPE_WORKSHEET, "kaputt")._effective_help_appendix() == HELP_APPENDIX_NONE
    assert _Host(None, HELP_APPENDIX_SINGLE)._effective_help_appendix() == HELP_APPENDIX_NONE


def test_cache_key_separates_appendix_variants(tmp_path):
    document = tmp_path / "blatt.abw"
    document.write_text("x", encoding="utf-8")

    def key(appendix):
        host = _Host(DOCUMENT_TYPE_WORKSHEET, appendix)
        return host._build_preview_cache_key(document, False, "a4_portrait", "standard", document_type=DOCUMENT_TYPE_WORKSHEET)

    assert len({key(HELP_APPENDIX_NONE), key(HELP_APPENDIX_SHEET), key(HELP_APPENDIX_SINGLE)}) == 3


def test_tab_state_keeps_appendix_per_tab(tmp_path):
    dummy = _DummyBase()
    dummy.preview_help_appendix_var.set(HELP_APPENDIX_SINGLE)
    document = tmp_path / "blatt.abw"
    document.write_text("# x\n", encoding="utf-8")
    dummy.document_tabs["t1"] = dummy._build_document_tab_state(document)
    dummy._active_document_tab_id = "t1"

    dummy.preview_help_appendix_var.set(HELP_APPENDIX_SHEET)
    dummy._persist_active_document_tab_state()
    dummy.preview_help_appendix_var.set(HELP_APPENDIX_NONE)
    dummy._apply_document_tab_state("t1")

    assert dummy.document_tabs["t1"]["help_appendix"] == HELP_APPENDIX_SHEET
    assert dummy.preview_help_appendix_var.get() == HELP_APPENDIX_SHEET


def test_radios_follow_lernhilfen_availability():
    class _Button:
        state = None

        def configure(self, **kwargs):
            self.state = kwargs["state"]

    host = BlattwerkPreviewHelpAppendixMixin()
    host.preview_help_appendix_buttons = [_Button(), _Button()]

    host._set_preview_help_appendix_enabled(False)
    assert {button.state for button in host.preview_help_appendix_buttons} == {"disabled"}
    host._set_preview_help_appendix_enabled(True)
    assert {button.state for button in host.preview_help_appendix_buttons} == {"normal"}


def test_fit_scale_uses_first_page_so_small_pages_stay_small():
    """Maßstabsgetreu: ein A6-Bild bekommt denselben Faktor wie die A4-Seite davor."""

    class _ViewHost(BlattwerkAppStyleViewMixin):
        def _get_preview_frame_size(self):
            return 800, 1000

    host = _ViewHost()
    a4 = Image.new("RGB", (1240, 1754))
    a6 = Image.new("RGB", (620, 874))
    host.preview_images = [a4, a6]

    assert host._get_fit_scales(a6) == host._get_fit_scales(a4)
    host.preview_images = []
    assert host._get_fit_scales(a6) != host._get_fit_scales(a4)
