"""Vorschau-Optionsleiste startet immer eingeklappt (Wunschliste Schritt 3).

Ein frueher gespeichertes `preview_controls_collapsed: false` darf den eingeklappten
Start nicht aushebeln, und der Schluessel wird beim Speichern nicht mehr geschrieben
(auch aus alten Einstellungen entfernt).
"""

from __future__ import annotations

import app.ui.blatt_ui_persistence_settings as settings_module
from app.ui.blatt_ui_persistence_settings import BlattwerkAppPersistenceSettingsMixin


class _Var:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Host(BlattwerkAppPersistenceSettingsMixin):
    """Just enough state for `_load_ui_settings`/`_save_ui_settings`."""

    def __init__(self):
        self.preview_controls_collapsed_var = _Var(False)
        self.theme_var = _Var("light")
        self.preview_contrast_var = _Var("standard")
        self.design_color_profile_var = _Var("indigo")
        self.design_font_profile_var = _Var("segoe")
        self.design_font_size_profile_var = _Var("normal")
        self.user_preferences = {}

    def _restore_window_geometry_if_enabled(self, _preferences):
        pass

    def _apply_user_preferences_live(self, _preferences):
        pass

    def _build_current_user_preferences_payload(self):
        return {}


def test_stored_expanded_state_is_ignored_on_load(monkeypatch):
    """Selbst bei gespeichertem `false` startet die Leiste eingeklappt."""
    monkeypatch.setattr(settings_module, "migrate_legacy_config", lambda **_k: None)
    monkeypatch.setattr(settings_module, "load_system_settings", lambda: {})
    monkeypatch.setattr(settings_module, "load_ui_settings", lambda: {"preview_controls_collapsed": False})
    monkeypatch.setattr(settings_module, "load_user_preferences", lambda: {})
    host = _Host()

    host._load_ui_settings()

    assert host.preview_controls_collapsed_var.get() is True


def test_save_drops_the_obsolete_key(monkeypatch):
    """Der alte Schluessel wird nicht geschrieben und aus vorhandenen Einstellungen entfernt."""
    written = {}
    monkeypatch.setattr(settings_module, "save_ui_settings", lambda settings: written.update(settings))
    monkeypatch.setattr(settings_module, "save_user_preferences", lambda _preferences: None)
    host = _Host()
    host.ui_settings = {"preview_controls_collapsed": False, "theme": "light"}

    host._save_ui_settings()

    assert written, "save_ui_settings was not called"
    assert "preview_controls_collapsed" not in written
    assert "preview_controls_collapsed" not in host.ui_settings
