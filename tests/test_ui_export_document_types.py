from pathlib import Path

from app.core.document_types import DOCUMENT_TYPE_KURZENTWURF, DOCUMENT_TYPE_WORKSHEET
from app.ui.blatt_ui_export import BlattwerkAppExportMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _DummyExportApp(BlattwerkAppExportMixin):
    def __init__(self, document_type):
        self.user_preferences = {"pre_export_diagnostics_enabled": True}
        self.preview_mode_var = _Var("solution")
        self.theme_var = _Var("default")
        self.root = object()
        self._document_type = document_type

    def _get_initial_dialog_dir(self, _key):
        return None

    def _detect_document_type(self, _input_path: Path) -> str:
        return self._document_type


def test_show_export_diagnostics_skips_kurzentwurf(monkeypatch, tmp_path):
    app = _DummyExportApp(DOCUMENT_TYPE_KURZENTWURF)
    called = {"warning_payload": 0, "messagebox": 0}

    monkeypatch.setattr(
        "app.ui.blatt_ui_export.build_warning_payload",
        lambda *args, **kwargs: (
            called.__setitem__("warning_payload", called["warning_payload"] + 1)
            or {
                "count": 1,
                "title": "Kurzentwurf-Warnungen (Export)",
                "message": "- KZF101 [Zeile 6]: Marker mit Doppelpunkt sind ungueltig.",
            }
        ),
    )
    monkeypatch.setattr(
        "app.ui.blatt_ui_export.messagebox.showwarning",
        lambda *args, **kwargs: called.__setitem__("messagebox", called["messagebox"] + 1),
    )

    app._show_export_diagnostics(tmp_path / "kurzentwurf.md")

    assert called["warning_payload"] == 1
    assert called["messagebox"] == 1


def test_open_worksheet_export_dialog_disables_mode_selection_for_kurzentwurf(monkeypatch, tmp_path):
    app = _DummyExportApp(DOCUMENT_TYPE_KURZENTWURF)
    seen = {}

    class _FakeDialog:
        def __init__(self, *args, **kwargs):
            seen.update(kwargs)
            self.result = None

    monkeypatch.setattr("app.ui.blatt_ui_export.WorksheetExportDialog", _FakeDialog)

    app.open_worksheet_export_dialog(input_path=tmp_path / "kurzentwurf.md")

    assert seen["allow_mode_selection"] is False
    assert seen["default_mode"] == "worksheet"


def test_open_worksheet_export_dialog_keeps_mode_selection_for_worksheet(monkeypatch, tmp_path):
    app = _DummyExportApp(DOCUMENT_TYPE_WORKSHEET)
    seen = {}

    class _FakeDialog:
        def __init__(self, *args, **kwargs):
            seen.update(kwargs)
            self.result = None

    monkeypatch.setattr("app.ui.blatt_ui_export.WorksheetExportDialog", _FakeDialog)

    app.open_worksheet_export_dialog(input_path=tmp_path / "blatt.md")

    assert seen["allow_mode_selection"] is True
    assert seen["default_mode"] == "solution"