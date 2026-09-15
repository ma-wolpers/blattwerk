"""Tests that `_export_pptx()` (the UI-layer PPTX export orchestration)
forwards the "Editierbare Text-/Bildelemente"-checkbox value through to
`build_presentation_pptx(..., editable=...)` -- the wiring between the
export dialog's `editable_pptx` result field and the core export call.
"""

from pathlib import Path

import pytest

from app.core.build_requests import WorksheetDesignOptions
from app.ui.blatt_ui_export import BlattwerkAppExportMixin


class _StopAfterCall(Exception):
    pass


def _make_exporter():
    exporter = object.__new__(BlattwerkAppExportMixin)
    exporter._worksheet_design_options = lambda: WorksheetDesignOptions("indigo", "segoe", "normal")
    exporter._current_presentation_footer_export_options = lambda: ("dot", False)
    return exporter


@pytest.mark.parametrize("editable_flag", [True, False])
def test_export_pptx_forwards_editable_flag(monkeypatch, tmp_path, editable_flag):
    captured = {}

    def _fake_build_presentation_pptx(**kwargs):
        captured.update(kwargs)
        raise _StopAfterCall()

    monkeypatch.setattr(
        "app.ui.blatt_ui_export.build_presentation_pptx", _fake_build_presentation_pptx
    )
    exporter = _make_exporter()

    with pytest.raises(_StopAfterCall):
        exporter._export_pptx(
            tmp_path / "praesentation.md",
            tmp_path / "out.pptx",
            "presentation_16_9",
            "worksheet",
            "indigo",
            editable_pptx=editable_flag,
        )

    assert captured["editable"] is editable_flag


def test_export_pptx_defaults_editable_to_false_when_not_passed(monkeypatch, tmp_path):
    captured = {}

    def _fake_build_presentation_pptx(**kwargs):
        captured.update(kwargs)
        raise _StopAfterCall()

    monkeypatch.setattr(
        "app.ui.blatt_ui_export.build_presentation_pptx", _fake_build_presentation_pptx
    )
    exporter = _make_exporter()

    with pytest.raises(_StopAfterCall):
        exporter._export_pptx(
            tmp_path / "praesentation.md", tmp_path / "out.pptx", "presentation_16_9", "worksheet", "indigo",
        )

    assert captured["editable"] is False
