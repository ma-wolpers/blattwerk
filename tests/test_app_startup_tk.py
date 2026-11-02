"""Starttest: echtes Blattwerk-Hauptfenster (isolierte Konfiguration, kein Dokument), Tasten ohne OS-Fokus.

Baut ``BlattwerkApp`` ohne Startdatei; die lokale Konfiguration liegt (wie in der
autouse-Fixture von ``conftest.py``, hier modulweit) im Temp-Verzeichnis -- keine
echten Einstellungen.
Tastendrücke laufen über ``bw_gui.testing.keys.press_key`` durch die bw-gui-
Dispatcher; das ``background_windows``-Plugin gibt den OS-Vordergrund sofort zurück.

Abgesichert: Start über ``BwBaseWindow`` mit installiertem Router ohne fremde
``all``-Tastaturbindungen, die Hauptfenster-Kürzel hängen am Window-Binder
(``Ctrl+Shift+D`` öffnet das Debug-Overlay ohne Feststelltaste), und die
Menü-Hinweistexte kommen aus der Registry.
"""

from __future__ import annotations

import pytest

from bw_gui.runtime.key_router import router_for
from bw_gui.testing.keys import press_key
from bw_gui.testing.tk_root import create_tk_root

SHIFT, CONTROL = 0x0001, 0x0004


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    """Ein Hauptfenster für das Modul (ein Tk-Interpreter; isolierte Konfiguration)."""
    from app.storage import local_config_store
    from app.ui.blatt_ui import BlattwerkApp

    state_dir = tmp_path_factory.mktemp("blattwerk_start_state")
    patcher = pytest.MonkeyPatch()
    for name in ("STORAGE_STATE_DIR", "LOCAL_CONFIG_PATH", "LEGACY_RECENT_FILES_PATH", "LEGACY_UI_SETTINGS_PATH",
                 "ROOT_LEGACY_RECENT_FILES_PATH", "ROOT_LEGACY_UI_SETTINGS_PATH"):
        target = state_dir if name == "STORAGE_STATE_DIR" else state_dir / f"{name.lower()}.json"
        patcher.setattr(local_config_store, name, target)
    instance = create_tk_root(BlattwerkApp)
    instance.root.update()
    yield instance
    instance.root.destroy()
    patcher.undo()


def test_start_installs_router_and_window_shortcuts(app):
    assert router_for(app.root).verify() == []
    assert app._window_shortcut_binder.registry.all()
    assert "Strg+E   Exportieren" in list(app._iter_shortcut_menu_labels())


def test_ctrl_shift_d_toggles_the_debug_overlay(app):
    before = bool(app.shortcut_debug_enabled_var.get())
    assert press_key(app.root, "D", state=CONTROL | SHIFT) is True
    app.root.update()
    assert bool(app.shortcut_debug_enabled_var.get()) is not before


def test_editor_keys_run_on_the_editor_widget_binder(app):
    """Strg+F im Schreibbereich öffnet die Suchleiste, Esc in der Suche schließt sie wieder."""
    assert press_key(app.editor_widget, "f", state=CONTROL) is True
    assert app._editor_search_visible is True
    assert press_key(app._editor_search_query_entry, "Escape") is True
    assert app._editor_search_visible is False


def test_several_cursors_work_in_the_real_app(app, tmp_path):
    """Durchlauf im echten Fenster: Cursor setzen, tippen, Undo mit Cursorn, Esc, Dokumentwechsel."""
    doc = tmp_path / "doc.abw"
    doc.write_text("Zeile eins\nZeile zwei\nZeile drei\n", encoding="utf-8")
    app._load_editor_content(doc)
    app.root.update()
    text, controller = app.editor_widget, app.editor_multicursor
    ctrl_alt = CONTROL | 0x20000

    text.mark_set("insert", "1.0")
    assert press_key(text, "Down", state=ctrl_alt) is True
    assert press_key(text, "Down", state=ctrl_alt) is True
    assert controller.is_active()
    assert press_key(text, "x", char="x") is True
    assert text.get("1.0", "end-1c") == "xZeile eins\nxZeile zwei\nxZeile drei\n"

    assert press_key(text, "z", state=CONTROL) is True
    assert text.get("1.0", "end-1c") == "Zeile eins\nZeile zwei\nZeile drei\n" and controller.is_active()

    assert press_key(text, "Escape") is True
    assert not controller.is_active()

    other = tmp_path / "other.abw"
    other.write_text("Anderer Text\n", encoding="utf-8")
    app._load_editor_content(other)
    press_key(text, "z", state=CONTROL)
    assert text.get("1.0", "end-1c") == "Anderer Text\n"
