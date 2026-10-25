"""Vorschau-Ansichten in der UI: Toolbar, Tab-Taste, Cache-Key, Exportdialog-Vorauswahl.

Die Ansichten selbst kommen aus `document_type_registry.preview_variants`
(getestet in `test_document_types.py`); hier wird nur geprüft, dass die UI
diese eine Quelle nutzt. Keine echten Tk-Widgets: Fake-Variablen und -Buttons.
"""

from __future__ import annotations

import pytest

from app.core.document_type_registry import (
    DOCUMENT_TYPE_EXAM,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    preview_variants,
)
from app.ui.blatt_ui_document_tabs import BlattwerkDocumentTabsMixin
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeButton:
    """Merkt sich, ob und in welcher Reihenfolge gepackt wurde."""

    def __init__(self, name, log):
        self.name = name
        self.log = log
        self.packed = False
        self.state = None

    def winfo_manager(self):
        return "pack" if self.packed else ""

    def pack(self, **_kwargs):
        self.packed = True
        self.log.append(self.name)

    def pack_forget(self):
        self.packed = False

    def configure(self, **kwargs):
        self.state = kwargs.get("state", self.state)


def test_expectation_view_hides_page_format_and_design():
    caps = BlattwerkAppPreviewMixin._preview_toolbar_capabilities(DOCUMENT_TYPE_EXAM, "expectation")

    assert caps["show_solution_toggle"] is True
    assert caps["show_page_format"] is False
    assert caps["show_design_controls"] is False


def test_expectation_request_on_worksheet_keeps_page_format():
    """Ein für den Typ unbekannter Wunsch zählt wie `worksheet` (Registry-Coercion)."""
    caps = BlattwerkAppPreviewMixin._preview_toolbar_capabilities(DOCUMENT_TYPE_WORKSHEET, "expectation")

    assert caps["show_page_format"] is True
    assert caps["show_design_controls"] is True


@pytest.mark.parametrize(
    ("document_type", "expected_order"),
    [
        (DOCUMENT_TYPE_EXAM, ["worksheet", "solution", "expectation"]),
        (DOCUMENT_TYPE_WORKSHEET, ["worksheet", "solution"]),
        (DOCUMENT_TYPE_PRESENTATION, []),
    ],
)
def test_view_radios_follow_registry_order(document_type, expected_order):
    log = []
    host = BlattwerkAppPreviewMixin.__new__(BlattwerkAppPreviewMixin)
    host.preview_mode_btn_worksheet = _FakeButton("worksheet", log)
    host.preview_mode_btn_solution = _FakeButton("solution", log)
    host.preview_mode_btn_expectation = _FakeButton("expectation", log)
    host.preview_mode_btn_expectation.packed = True  # Rest vom vorigen Klausur-Tab

    caps = host._preview_toolbar_capabilities(document_type)
    host._apply_preview_variant_buttons(preview_variants(document_type) if caps["show_solution_toggle"] else ())

    assert log == expected_order
    assert host.preview_mode_btn_expectation.packed is ("expectation" in expected_order)
    assert host.preview_mode_btn_expectation.state == ("normal" if "expectation" in expected_order else "disabled")


class _ToggleHost(BlattwerkDocumentTabsMixin):
    def __init__(self, path, mode):
        self.input_var = _Var(path)
        self.preview_mode_var = _Var(mode)
        self.refresh_count = 0

    @staticmethod
    def _clean_path_text(text):
        return str(text or "").strip()

    def _read_document_type(self, input_path):
        from app.core.document_semantics import type_for_tab

        return type_for_tab(input_path, None)

    def refresh_preview(self, force_rebuild=False):
        self.refresh_count += 1


def test_tab_cycles_through_all_exam_views():
    host = _ToggleHost("klausur.kbw", "worksheet")
    seen = []
    for _ in range(3):
        host._toggle_preview_mode()
        seen.append(host.preview_mode_var.get())

    assert seen == ["solution", "expectation", "worksheet"]
    assert host.refresh_count == 3


def test_tab_does_nothing_for_single_view_types():
    host = _ToggleHost("folien.pbw", "worksheet")
    host._toggle_preview_mode()

    assert host.preview_mode_var.get() == "worksheet"
    assert host.refresh_count == 0


def test_cache_key_separates_solution_and_expectation(tmp_path):
    document = tmp_path / "klausur.kbw"
    document.write_text("x", encoding="utf-8")
    host = BlattwerkAppPreviewMixin.__new__(BlattwerkAppPreviewMixin)
    host.preview_black_screen_var = _Var("none")
    host.preview_section_separator_var = _Var("dot")
    host.preview_hide_future_sections_var = _Var(False)
    host.design_color_profile_var = _Var("indigo")
    host.design_font_profile_var = _Var("segoe")
    host.design_font_size_profile_var = _Var("normal")

    def key(include_solutions, variant):
        return host._build_preview_cache_key(
            document, include_solutions, "a4_portrait", "standard",
            document_type=DOCUMENT_TYPE_EXAM, preview_variant=variant,
        )

    assert key(True, "solution") != key(False, "expectation")
    assert key(False, "worksheet") != key(False, "expectation")
    assert key(True, None) == key(True, "solution")  # ohne Ansicht aus dem alten Flag abgeleitet


def test_export_dialog_preselected_expectation_restricts_format():
    from app.ui.export_dialog_worksheet import WorksheetExportDialog

    dialog = WorksheetExportDialog.__new__(WorksheetExportDialog)
    dialog.mode_var = _Var("expectation")
    dialog.format_var = _Var("pngzip")
    dialog._refresh_output_suggestion = lambda force=False: None

    dialog._on_mode_changed()

    assert dialog.format_var.get() == "pdf"
