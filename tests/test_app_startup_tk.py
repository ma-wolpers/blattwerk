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

import tkinter

import pytest

from bw_gui.runtime.key_router import router_for
from bw_gui.testing.keys import press_key

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
    for attempt in range(3):
        try:
            instance = BlattwerkApp()
            break
        except tkinter.TclError as exc:
            # Bekannte Tcl-Init-Race beim wiederholten Erzeugen von Tk-Interpretern unter Windows.
            if not any(m in str(exc) for m in ("usable", "tcl_findLibrary", "init.tcl")) or attempt == 2:
                raise
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
