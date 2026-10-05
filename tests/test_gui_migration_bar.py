"""GUI-Migrationsleiste: Klassifikation des Buffers, Dirty-Buffer-Regel, Retarget, Undo."""

from pathlib import Path

import pytest

from app.core.migration.side_state import InMemorySideStateStore
from app.ui import blatt_ui_migration_bar as bar_module
from app.ui.blatt_ui_migration_bar import BlattwerkMigrationBarMixin

from migration_helpers import WORKSHEET


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Editor:
    def __init__(self, text):
        self.text = text

    def get(self, _a, _b):
        return self.text


class _Dummy(BlattwerkMigrationBarMixin):
    def __init__(self, path: Path, buffer_text: str, dirty: bool = False):
        self.input_var = _Var(str(path))
        self.status_var = _Var()
        self.editor_widget = _Editor(buffer_text)
        self._editor_has_unsaved_changes = dirty
        self.shown = None
        self.opened = []
        self.closed = []
        self.flush_result = True
        self._migration_last_run = None

    # Leiste ohne Tk protokollieren
    def _show_migration_bar(self, text, button_text, action):
        self.shown = (text, button_text)
        self._migration_bar_action = action

    def _hide_migration_bar(self):
        self.shown = None

    @staticmethod
    def _clean_path_text(text):
        return text.strip()

    def _flush_unsaved_editor_changes(self):
        if self.flush_result and self._editor_has_unsaved_changes:
            Path(self.input_var.get()).write_text(self.editor_widget.text, encoding="utf-8")
            self._editor_has_unsaved_changes = False
        return self.flush_result

    def _find_open_tab_id_for_path(self, path):
        return f"tab:{Path(path).name}"

    def _close_document_tab(self, tab_id):
        self.closed.append(tab_id)

    def _open_input_path(self, path, **_kwargs):
        self.opened.append(Path(path))
        self.input_var.set(str(path))
        self.editor_widget.text = Path(path).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    store = InMemorySideStateStore()
    monkeypatch.setattr(bar_module, "default_lock_dir", lambda: tmp_path / "locks")
    monkeypatch.setattr(bar_module, "default_runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(bar_module, "LocalConfigSideStateStore", lambda: store)
    monkeypatch.setattr(bar_module, "current_app_lock", lambda: None)
    monkeypatch.setattr(bar_module.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(bar_module.messagebox, "showwarning", lambda *a, **k: None)
    return store


def _file(tmp_path, text, name="blatt.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_safe_markdown_shows_one_click_bar(tmp_path):
    path = _file(tmp_path, WORKSHEET)
    dummy = _Dummy(path, WORKSHEET)
    dummy._refresh_migration_bar()
    assert dummy.shown[1] == "Jetzt migrieren" and "blatt.abw" in dummy.shown[0]


def test_dirty_buffer_offers_save_and_migrate(tmp_path):
    path = _file(tmp_path, "# leer\n")
    dummy = _Dummy(path, WORKSHEET, dirty=True)  # Buffer klassifiziert, nicht die Platte
    dummy._refresh_migration_bar()
    assert dummy.shown[1] == "Speichern und migrieren"


def test_unclear_conflict_and_plain_markdown(tmp_path):
    unclear = _Dummy(_file(tmp_path, ":::task\nA\n:::\n", "u.md"), ":::task\nA\n:::\n")
    plain = _Dummy(_file(tmp_path, "# Notiz\n", "n.md"), "# Notiz\n")
    declared = _Dummy(_file(tmp_path, "---\ndocument_type: markdown\n---\n:::task\n", "d.md"), "---\ndocument_type: markdown\n---\n:::task\n")
    for dummy in (unclear, plain, declared):
        dummy._refresh_migration_bar()
    assert unclear.shown is not None and unclear.shown[1] is None
    assert plain.shown is None and declared.shown is None


def test_save_and_migrate_migrates_exactly_the_buffer_and_retargets_tab(tmp_path, isolated):
    path = _file(tmp_path, "# alter Plattenstand\n")
    dummy = _Dummy(path, WORKSHEET, dirty=True)

    dummy._migrate_active_markdown(path)

    target = tmp_path / "blatt.abw"
    assert dummy.opened == [target] and dummy.closed == ["tab:blatt.md"]
    assert target.read_text(encoding="utf-8").startswith("---\ndocument_type: worksheet\n")
    assert not path.exists()


def test_failed_save_blocks_migration(tmp_path):
    path = _file(tmp_path, "# alt\n")
    dummy = _Dummy(path, WORKSHEET, dirty=True)
    dummy.flush_result = False

    dummy._migrate_active_markdown(path)

    assert path.exists() and not (tmp_path / "blatt.abw").exists()


def test_buffer_disk_mismatch_blocks_migration(tmp_path):
    path = _file(tmp_path, WORKSHEET)
    dummy = _Dummy(path, WORKSHEET + "\nnoch nicht gespeichert\n", dirty=False)

    dummy._migrate_active_markdown(path)

    assert path.exists() and not (tmp_path / "blatt.abw").exists()


def test_undo_from_bar_restores_and_retargets_back(tmp_path):
    path = _file(tmp_path, WORKSHEET)
    dummy = _Dummy(path, WORKSHEET)
    dummy._migrate_active_markdown(path)
    dummy._refresh_migration_bar()
    assert dummy.shown[1] == "Rückgängig"

    dummy._undo_last_migration()

    assert path.read_text(encoding="utf-8") == WORKSHEET
    assert not (tmp_path / "blatt.abw").exists()
    assert dummy.opened[-1] == path
