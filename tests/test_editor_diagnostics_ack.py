"""Tests for the "als gelesen markieren" Treeview checkbox/context-menu wiring
(Step 3 of the acknowledge-warnings feature) -- using a fake Treeview, same
style as `test_editor_document_diagnostics.py`, rather than a real Tk widget.
"""

import tempfile
from pathlib import Path

import pytest

from app.storage import local_config_store as lcs
from app.ui.blatt_ui_editor_diagnostics import BlattwerkAppEditorDiagnosticsMixin
from app.ui.blatt_ui_editor_diagnostics_ack import BlattwerkAppEditorDiagnosticsAckMixin


class _FakeTreeview:
    """Minimal `ttk.Treeview` fake covering only what the mixin calls."""

    def __init__(self):
        self._rows: dict[str, dict] = {}
        self._order: list[str] = []
        self._tags: dict[str, str] = {}

    def delete(self, *iids):
        self._rows.clear()
        self._order.clear()

    def get_children(self):
        return tuple(self._order)

    def insert(self, _parent, _index, iid=None, values=(), tags=()):
        row_id = iid or f"auto-{len(self._order)}"
        self._rows[row_id] = {"values": list(values), "tags": tuple(tags)}
        self._order.append(row_id)
        return row_id

    def item(self, row_id, key=None, **kwargs):
        if kwargs:
            self._rows[row_id].update({k: (list(v) if k == "values" else v) for k, v in kwargs.items()})
            return None
        if key is not None:
            return self._rows[row_id][key]
        return self._rows[row_id]

    def selection(self):
        return tuple(self._selection) if hasattr(self, "_selection") else ()

    def selection_set(self, row_id):
        self._selection = (row_id,)

    def tag_configure(self, *_args, **_kwargs):
        return None

    def identify_row(self, _y):
        return getattr(self, "_next_identify_row", "")

    def identify_column(self, _x):
        return getattr(self, "_next_identify_column", "")


class _DummyDiagnosticsApp(BlattwerkAppEditorDiagnosticsAckMixin, BlattwerkAppEditorDiagnosticsMixin):
    def __init__(self, document_path):
        self.editor_widget = None
        self.editor_diagnostics_listbox = _FakeTreeview()
        self.user_preferences = {}
        self._document_path = document_path

    def _active_document_tab_state(self):
        return {"path": self._document_path}


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    monkeypatch.setattr(lcs, "LOCAL_CONFIG_PATH", tmp_path / "config.json")
    from app.storage import acknowledged_warnings_store as store

    doc_path = tmp_path / "doc.md"
    doc_path.write_text("x", encoding="utf-8")
    lcs.save_recent_files([store.normalize_recent_path(str(doc_path))])
    return doc_path


def _warning_item(identity="ident-1"):
    return {"line": 5, "code": "OP002", "severity": "warning", "message": "bad value", "identity": identity}


def _error_item():
    return {"line": 1, "code": "BL004", "severity": "error", "message": "nested block", "identity": None}


def test_unacknowledged_warning_shows_unchecked_glyph(temp_config):
    app = _DummyDiagnosticsApp(str(temp_config))
    app._set_editor_diagnostics([_warning_item()])

    tree = app.editor_diagnostics_listbox
    values = tree.item("row-0", "values")
    assert values[0] == "☐"


def test_checkbox_click_toggles_and_persists(temp_config):
    from app.storage import acknowledged_warnings_store as store

    app = _DummyDiagnosticsApp(str(temp_config))
    app._set_editor_diagnostics([_warning_item("ident-1")])

    tree = app.editor_diagnostics_listbox
    tree._next_identify_row = "row-0"
    tree._next_identify_column = "#1"

    class _Event:
        x = 5
        y = 5

    result = app._on_editor_diagnostics_ack_column_click(_Event())
    assert result == "break"
    assert tree.item("row-0", "values")[0] == "☑"
    assert tree.item("row-0", "tags") == ("ack_done",)
    assert store.get_acknowledged(str(temp_config)) == {"ident-1"}

    # Toggle back off.
    result = app._on_editor_diagnostics_ack_column_click(_Event())
    assert tree.item("row-0", "values")[0] == "☐"
    assert store.get_acknowledged(str(temp_config)) == set()


def test_click_outside_ack_column_does_not_toggle(temp_config):
    app = _DummyDiagnosticsApp(str(temp_config))
    app._set_editor_diagnostics([_warning_item("ident-1")])

    tree = app.editor_diagnostics_listbox
    tree._next_identify_row = "row-0"
    tree._next_identify_column = "#4"  # the "message" column, not the checkbox

    class _Event:
        x = 200
        y = 5

    app._on_editor_diagnostics_ack_column_click(_Event())
    assert tree.item("row-0", "values")[0] == "☐"


def test_error_row_is_never_ackable(temp_config):
    app = _DummyDiagnosticsApp(str(temp_config))
    app._set_editor_diagnostics([_error_item()])

    tree = app.editor_diagnostics_listbox
    assert tree.item("row-0", "values")[0] == ""

    tree._next_identify_row = "row-0"
    tree._next_identify_column = "#1"

    class _Event:
        x = 5
        y = 5

    result = app._on_editor_diagnostics_ack_column_click(_Event())
    assert result == "break"
    assert tree.item("row-0", "values")[0] == ""  # unchanged, still not ackable


def test_previously_acknowledged_warning_renders_checked_after_refresh(temp_config):
    from app.storage import acknowledged_warnings_store as store

    store.set_acknowledged(str(temp_config), "ident-1", True)

    app = _DummyDiagnosticsApp(str(temp_config))
    app._set_editor_diagnostics([_warning_item("ident-1")])

    tree = app.editor_diagnostics_listbox
    assert tree.item("row-0", "values")[0] == "☑"
    assert tree.item("row-0", "tags") == ("ack_done",)


def test_clear_acknowledged_resets_only_current_document(temp_config, tmp_path):
    from app.storage import acknowledged_warnings_store as store

    other_doc = tmp_path / "other.md"
    other_doc.write_text("y", encoding="utf-8")
    lcs.save_recent_files([store.normalize_recent_path(str(temp_config)), store.normalize_recent_path(str(other_doc))])

    store.set_acknowledged(str(temp_config), "ident-1", True)
    store.set_acknowledged(str(other_doc), "ident-2", True)

    app = _DummyDiagnosticsApp(str(temp_config))
    app._set_editor_diagnostics([_warning_item("ident-1")])
    app._clear_editor_diagnostics_acknowledged()

    assert store.get_acknowledged(str(temp_config)) == set()
    assert store.get_acknowledged(str(other_doc)) == {"ident-2"}
