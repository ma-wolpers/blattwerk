"""Exportdialog „Lernhilfen mit exportieren“: Auswahl-Logik, Vorauswahl aus der Vorschau, Durchreichung.

Die Dialog-Logik wird ohne Tk geprüft (`WorksheetExportDialog.__new__` mit
Fake-Variablen, wie `test_expectation_horizon.py`), die Orchestrierung mit
einem Fake-Dialog (wie `test_page_format_a4_landscape.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import app.ui.blatt_ui_export_dialogs as dialogs_module
from app.core.help_cards_appendix import HELP_APPENDIX_NONE, HELP_APPENDIX_SHEET, HELP_APPENDIX_SINGLE
from app.ui.blatt_ui_export import BlattwerkAppExportMixin
from app.ui.export_dialog import WorksheetExportDialog


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def _dialog(fmt="pdf", mode="worksheet", enabled=True, variant=HELP_APPENDIX_SINGLE, allow=True):
    dialog = WorksheetExportDialog.__new__(WorksheetExportDialog)
    dialog.allow_help_appendix = allow
    dialog.format_var = _Var(fmt)
    dialog.mode_var = _Var(mode)
    dialog.help_appendix_enabled_var = _Var(enabled)
    dialog.help_appendix_variant_var = _Var(variant)
    return dialog


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, HELP_APPENDIX_SINGLE),
        ({"variant": HELP_APPENDIX_SHEET}, HELP_APPENDIX_SHEET),
        ({"fmt": "png"}, HELP_APPENDIX_SINGLE),
        ({"enabled": False}, HELP_APPENDIX_NONE),
        ({"fmt": "html"}, HELP_APPENDIX_NONE),
        ({"mode": "expectation"}, HELP_APPENDIX_NONE),
        ({"allow": False}, HELP_APPENDIX_NONE),
    ],
)
def test_selected_appendix_respects_checkbox_format_and_mode(kwargs, expected):
    assert _dialog(**kwargs)._selected_help_appendix() == expected


def test_g_cycles_off_sheet_single_off():
    dialog = _dialog(enabled=False, variant=HELP_APPENDIX_SHEET)
    seen = []
    for _ in range(3):
        dialog._cycle_help_appendix()
        seen.append(dialog._selected_help_appendix())

    assert seen == [HELP_APPENDIX_SHEET, HELP_APPENDIX_SINGLE, HELP_APPENDIX_NONE]


def test_g_does_nothing_for_html():
    dialog = _dialog(fmt="html", enabled=False)
    dialog._cycle_help_appendix()

    assert dialog.help_appendix_enabled_var.get() is False


def test_shortcut_help_mentions_g_only_when_row_is_shown():
    assert "G" in WorksheetExportDialog._build_shortcuts_help_text(True, True)
    assert "Lernhilfen" not in WorksheetExportDialog._build_shortcuts_help_text(True, False)
    assert "Lernhilfen" in WorksheetExportDialog._build_shortcuts_help_text(False, True)


def _host(tmp_path, effective, document_type="worksheet", cards=1):
    class _Host(BlattwerkAppExportMixin):
        def _effective_help_appendix(self):
            return effective

        def _count_visible_lernhilfen(self, _path, include_solutions=False):
            return cards

    host = _Host()
    host.user_preferences = {}
    host.root = type("_Root", (), {"update_idletasks": lambda self: None})()
    host.theme_var = _Var("light")
    host.status_var = _Var("")
    host.preview_mode_var = _Var("worksheet")
    host.preview_page_format_var = _Var("a4_portrait")
    host.preview_contrast_var = _Var("standard")
    host._get_initial_dialog_dir = lambda _purpose: None
    host._set_last_dialog_dir = lambda *_args: None
    host._detect_document_type = lambda _path: document_type
    host._solutions_renderable_for_type = lambda _type: True
    host._show_export_diagnostics = lambda _path: None
    return host


def _run(monkeypatch, tmp_path, host, result_appendix):
    seen = {}

    class FakeDialog:
        def __init__(self, *_args, **kwargs):
            seen["dialog"] = kwargs
            self.result = {
                "format": "pdf",
                "mode": "worksheet",
                "output_path": str(tmp_path / "out.pdf"),
                "help_appendix": result_appendix,
            }

    def fake_export_pdf(*_args, **kwargs):
        seen["export"] = kwargs
        raise RuntimeError("stop after capture")

    monkeypatch.setattr(dialogs_module, "WorksheetExportDialog", FakeDialog)
    monkeypatch.setattr(dialogs_module.messagebox, "showerror", lambda *_a, **_k: None)
    host._export_pdf = fake_export_pdf
    host.open_worksheet_export_dialog(input_path=Path("blatt.abw"))
    return seen


def test_dialog_preselects_the_variant_visible_in_the_preview(monkeypatch, tmp_path):
    seen = _run(monkeypatch, tmp_path, _host(tmp_path, HELP_APPENDIX_SINGLE), HELP_APPENDIX_SINGLE)

    assert seen["dialog"]["default_help_appendix"] == HELP_APPENDIX_SINGLE
    assert seen["dialog"]["allow_help_appendix"] is True
    assert seen["export"]["help_appendix"] == HELP_APPENDIX_SINGLE


def test_no_lernhilfen_hides_the_option(monkeypatch, tmp_path):
    seen = _run(monkeypatch, tmp_path, _host(tmp_path, HELP_APPENDIX_NONE, cards=0), HELP_APPENDIX_NONE)

    assert seen["dialog"]["allow_help_appendix"] is False
    assert seen["export"]["help_appendix"] == HELP_APPENDIX_NONE


def test_request_builder_carries_the_appendix():
    class _Host(BlattwerkAppExportMixin):
        pass

    host = _Host()
    host._current_presentation_footer_export_options = lambda: ("dot", False)
    host._worksheet_design_options = lambda: None
    host._metadata_defaults_from_preferences = lambda: {}
    host._copyright_text_from_preferences = lambda: ""
    host._computation_cache_for = lambda _path: None
    host._export_target_policy = lambda: None

    request = host._worksheet_build_request(
        input_path=Path("a.abw"), output_path=Path("a.pdf"), include_solutions=False,
        page_format="a4_portrait", contrast_profile="standard", help_appendix=HELP_APPENDIX_SHEET,
    )

    assert request.help_appendix == HELP_APPENDIX_SHEET
