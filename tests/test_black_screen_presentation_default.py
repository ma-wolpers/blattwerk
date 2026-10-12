"""Black-Screen default for presentations (Wunschliste Schritt 2).

The user preference `default_black_screen_presentation` (default ``both``) seeds the
preview variable, which feeds the preview build and the presentation export dialog.
The core build functions and the worksheet export keep ``none``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import app.ui.blatt_ui_export as export_module
import app.ui.blatt_ui_preview_render as render_module
from app.core.blatt_kern_layout_render import render_html
from app.storage.user_preferences_adapter import normalize_user_preferences
from app.ui.blatt_ui_export import BlattwerkAppExportMixin
from app.ui.blatt_ui_persistence_settings import BlattwerkAppPersistenceSettingsMixin
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def _host_with_preferences(preferences):
    """A host whose black-screen variable was initialised from the given preferences."""

    class _Host(BlattwerkAppPersistenceSettingsMixin, BlattwerkAppPreviewMixin, BlattwerkAppExportMixin):
        pass

    host = _Host()
    host.preview_black_screen_var = _Var("none")
    host.user_preferences = normalize_user_preferences(preferences)
    host._apply_presentation_preview_defaults(host.user_preferences)
    return host


def test_preference_defaults_to_both_and_rejects_unknown_values():
    """Default is 'both'; an unknown stored value falls back to the default."""
    assert normalize_user_preferences({})["default_black_screen_presentation"] == "both"
    assert normalize_user_preferences({"default_black_screen_presentation": "xyz"})[
        "default_black_screen_presentation"
    ] == "both"
    assert normalize_user_preferences({"default_black_screen_presentation": "before"})[
        "default_black_screen_presentation"
    ] == "before"


def test_preview_build_receives_the_preference(monkeypatch):
    """The preview passes the preference-initialised value to the document build."""
    captured = {}

    def fake_build(input_path, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(render_module, "build_preview_images_for_document", fake_build)
    host = _host_with_preferences({})
    host.preview_section_separator_var = _Var("dot")
    host.preview_hide_future_sections_var = _Var(False)
    host._worksheet_design_options = lambda: {}
    host._read_document_type = lambda _path: "presentation"
    host._resolve_computation_cache = lambda _path: None

    host._render_pdf_pages(Path("deck.pbw"), False, "presentation_16_9", "standard")

    assert captured["black_screen_mode"] == "both"


def test_both_produces_black_slides_at_start_and_end():
    """'both' renders one black slide before and one after the deck."""
    html = render_html(
        {"Titel": "T", "Fach": "M", "Thema": "X"},
        [("task", {}, "Inhalt")],
        include_solutions=False,
        black_screen_mode="both",
        document_type="presentation",
    )
    sections = [part for part in html.split("<section class='")[1:]]
    assert sections[0].startswith("ab-slide ab-slide-black'")
    assert sections[-1].startswith("ab-slide ab-slide-black'")
    assert html.count("class='ab-slide ab-slide-black'") == 2


def test_core_default_stays_none():
    """Without an explicit mode the core inserts no black slides."""
    html = render_html(
        {"Titel": "T", "Fach": "M", "Thema": "X"},
        [("task", {}, "Inhalt")],
        include_solutions=False,
        document_type="presentation",
    )
    assert "ab-slide-black'" not in html


@pytest.mark.parametrize("preference", ["both", "after", "none"])
def test_presentation_export_dialog_starts_from_the_preference(monkeypatch, preference):
    """The presentation export dialog's default is the preference-initialised preview value."""
    captured = {}

    class FakeDialog:
        def __init__(self, *_args, **kwargs):
            captured.update(kwargs)
            self.result = None

    monkeypatch.setattr(export_module, "PresentationExportDialog", FakeDialog)
    host = _host_with_preferences({"default_black_screen_presentation": preference})
    host.root = None
    host.theme_var = _Var("light")
    host._get_initial_dialog_dir = lambda _purpose: None

    host.open_presentation_export_dialog(input_path=Path("deck.pbw"))

    assert captured["black_screen_default"] == preference


def test_worksheet_export_keeps_black_screen_off(monkeypatch, tmp_path):
    """Worksheet exports never insert black slides, whatever the preference says."""
    captured = {}

    class FakeDialog:
        def __init__(self, *_args, **_kwargs):
            self.result = {"format": "pdf", "mode": "worksheet", "output_path": str(tmp_path / "out.pdf")}

    def fake_export_pdf(*_args, **kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop after capture")

    monkeypatch.setattr(export_module, "WorksheetExportDialog", FakeDialog)
    monkeypatch.setattr(export_module.messagebox, "showerror", lambda *_a, **_k: None)
    host = _host_with_preferences({"default_black_screen_presentation": "both"})
    host.root = type("_Root", (), {"update_idletasks": lambda self: None})()
    host.theme_var = _Var("light")
    host.status_var = _Var("")
    host.preview_mode_var = _Var("worksheet")
    host.preview_page_format_var = _Var("a4_portrait")
    host.preview_contrast_var = _Var("standard")
    host._get_initial_dialog_dir = lambda _purpose: None
    host._set_last_dialog_dir = lambda *_args: None
    host._detect_document_type = lambda _path: "worksheet"
    host._solutions_renderable_for_type = lambda _type: True
    host._show_export_diagnostics = lambda _path: None
    host._export_pdf = fake_export_pdf

    host.open_worksheet_export_dialog(input_path=Path("blatt.abw"))

    assert captured["black_screen_mode"] == "none"
