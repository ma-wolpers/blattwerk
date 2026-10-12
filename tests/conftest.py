from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

# Tk-Testfenster geben den OS-Vordergrund sofort an das Fenster des Entwicklers
# zurück (keine "geklauten" Tastendrücke während eines Testlaufs); mit
# TK_FOCUS_TESTS=1 deaktiviert. Siehe bw-gui docs/KEYBINDING_CONTRACT.md.
from bw_gui.testing.background_windows import pytest_configure, pytest_unconfigure  # noqa: E402,F401


import pytest  # noqa: E402

from app.storage import local_config_store as _local_config_store  # noqa: E402

_CONFIG_PATH_NAMES = (
    "STORAGE_STATE_DIR",
    "LOCAL_CONFIG_PATH",
    "LEGACY_RECENT_FILES_PATH",
    "LEGACY_UI_SETTINGS_PATH",
    "ROOT_LEGACY_RECENT_FILES_PATH",
    "ROOT_LEGACY_UI_SETTINGS_PATH",
)


@pytest.fixture(autouse=True)
def _isolate_local_config(tmp_path, monkeypatch):
    """Leitet die lokale Blattwerk-Konfiguration fuer jeden Test in ein Temp-Verzeichnis um.

    Ohne diese Fixture schreibt jeder Test, der (auch indirekt) `save_user_preferences`,
    `save_ui_settings` oder die Legacy-Migration aufruft, in die echte
    `app/storage/.state/blattwerk_local_config.json` und ueberschreibt die Einstellungen
    der Entwicklerin bzw. loescht Legacy-Dateien. Tests, die eigene Pfade brauchen,
    koennen diese Attribute weiterhin selbst per `monkeypatch` setzen.
    """
    state_dir = tmp_path / "blattwerk_state"
    state_dir.mkdir()
    replacements = {
        "STORAGE_STATE_DIR": state_dir,
        "LOCAL_CONFIG_PATH": state_dir / "blattwerk_local_config.json",
        "LEGACY_RECENT_FILES_PATH": state_dir / "blattwerk_recent.json",
        "LEGACY_UI_SETTINGS_PATH": state_dir / "blattwerk_ui_settings.json",
        "ROOT_LEGACY_RECENT_FILES_PATH": state_dir / "root.blattwerk_recent.json",
        "ROOT_LEGACY_UI_SETTINGS_PATH": state_dir / "root.blattwerk_ui_settings.json",
    }
    for name in _CONFIG_PATH_NAMES:
        monkeypatch.setattr(_local_config_store, name, replacements[name])
