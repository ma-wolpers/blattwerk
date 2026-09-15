"""Tests for `_show_compile_overflow_warnings`'s diagnostic-code filter.

Extended for the experimental editable PPTX export: `PPTX001` (a single
slide had to be rasterized) and `PPTX002` (the whole editable pipeline
fell back to the raster export) must reach the user through the same
warning dialog `PT002` already used -- a fallback that never surfaces is
exactly what the implementation plan explicitly ruled out.
"""

from app.core.blatt_validator_types import BuildDiagnostic
from app.ui.blatt_ui_export import BlattwerkAppExportMixin


def _make_exporter():
    return object.__new__(BlattwerkAppExportMixin)


def _diag(code, message="msg"):
    return BuildDiagnostic(code=code, message=message, severity="warning")


def test_pt002_still_surfaces(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_export.messagebox.showwarning",
        lambda title, text, **kwargs: calls.append((title, text)),
    )
    exporter = _make_exporter()

    exporter._show_compile_overflow_warnings([_diag("PT002", "Overflow")], "Export")

    assert len(calls) == 1
    assert "PT002" in calls[0][1]


def test_pptx001_surfaces(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_export.messagebox.showwarning",
        lambda title, text, **kwargs: calls.append((title, text)),
    )
    exporter = _make_exporter()

    exporter._show_compile_overflow_warnings(
        [_diag("PPTX001", "Folie 2 als Bild eingebettet")], "Export"
    )

    assert len(calls) == 1
    assert "Folie 2 als Bild eingebettet" in calls[0][1]


def test_pptx002_surfaces(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_export.messagebox.showwarning",
        lambda title, text, **kwargs: calls.append((title, text)),
    )
    exporter = _make_exporter()

    exporter._show_compile_overflow_warnings(
        [_diag("PPTX002", "Editierbarer Export nicht moeglich")], "Export"
    )

    assert len(calls) == 1
    assert "Editierbarer Export nicht moeglich" in calls[0][1]


def test_unrelated_codes_stay_filtered_out(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_export.messagebox.showwarning",
        lambda title, text, **kwargs: calls.append((title, text)),
    )
    exporter = _make_exporter()

    exporter._show_compile_overflow_warnings([_diag("MJ001", "unrelated")], "Export")

    assert calls == []


def test_multiple_pptx_and_pt_diagnostics_all_appear_together(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.ui.blatt_ui_export.messagebox.showwarning",
        lambda title, text, **kwargs: calls.append((title, text)),
    )
    exporter = _make_exporter()

    exporter._show_compile_overflow_warnings(
        [_diag("PT002", "a"), _diag("PPTX001", "b"), _diag("MJ001", "c"), _diag("PPTX002", "d")],
        "Export",
    )

    assert len(calls) == 1
    text = calls[0][1]
    assert "a" in text and "b" in text and "d" in text
    assert "c" not in text
