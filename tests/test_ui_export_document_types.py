from app.ui.blatt_ui_document_type import BlattwerkDocumentTypeMixin
from pathlib import Path

from app.core.document_type_registry import DOCUMENT_TYPE_KURZENTWURF, DOCUMENT_TYPE_WORKSHEET
from app.ui.blatt_ui_export import BlattwerkAppExportMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _DummyExportApp(BlattwerkDocumentTypeMixin, BlattwerkAppExportMixin):
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
        "app.ui.blatt_ui_export_support.build_warning_payload",
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
        "app.ui.blatt_ui_export_support.messagebox.showwarning",
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

    monkeypatch.setattr("app.ui.blatt_ui_export_dialogs.WorksheetExportDialog", _FakeDialog)

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

    monkeypatch.setattr("app.ui.blatt_ui_export_dialogs.WorksheetExportDialog", _FakeDialog)

    app.open_worksheet_export_dialog(input_path=tmp_path / "blatt.md")

    assert seen["allow_mode_selection"] is True
    assert seen["default_mode"] == "solution"


class _DummyDesignOptions:
    color_profile = "indigo"
    font_profile = "segoe"
    font_size_profile = "normal"


def test_render_lernhilfe_card_images_uses_per_card_page_fitting(monkeypatch, tmp_path):
    """PNG-Einzelkarten laufen über die gemeinsame Formatwahl (A6/A5/A4), nicht fest A6 + nur Seite 1."""
    input_path = tmp_path / "doc.md"
    input_path.write_text(
        "---\nTitel: T\nFach: M\nThema: X\n---\n:::help title='Hilfe'\nInhalt\n:::\n",
        encoding="utf-8",
    )
    seen = {}

    def _fake_render_help_card_images(path, **kwargs):
        seen["path"] = path
        seen.update(kwargs)
        return ["bild"]

    monkeypatch.setattr("app.ui.blatt_ui_export_help_cards.render_help_card_images", _fake_render_help_card_images)

    app = _DummyExportApp(DOCUMENT_TYPE_WORKSHEET)
    app._worksheet_design_options = lambda: _DummyDesignOptions()

    images = app._render_lernhilfe_card_images(input_path=input_path, contrast_profile="standard")

    assert images == ["bild"]
    assert seen["path"] == input_path
    assert seen["dpi"] == 200
    assert seen["include_solutions"] is False
    assert seen["contrast_profile"] == "standard"