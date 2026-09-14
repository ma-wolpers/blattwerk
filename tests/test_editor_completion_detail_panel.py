"""Tests for the autocomplete popup's explanation-overlay column
(`_update_editor_completion_detail_panel` and its wiring into
`_on_editor_completion_move_up`/`_down`/`_on_editor_completion_selection_changed`,
`blatt_ui_editor_completion_popup.py`).

Uses lightweight fakes for the Tk widgets involved (listbox selection,
frame `pack`/`pack_forget`, label `configure`) -- the same style as
`test_editor_completion_key_equals_chaining.py`'s `_FakeListbox` -- so this
stays a fast, headless unit test of the panel-update logic itself, not a
Tk integration test.
"""

from __future__ import annotations

from app.ui.blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin


class _FakeListbox:
    def __init__(self, selected_index=0):
        self._selected_index = selected_index
        self.selection_clear_calls = []
        self.selection_set_calls = []
        self.activate_calls = []
        self.see_calls = []

    def curselection(self):
        return (self._selected_index,) if self._selected_index is not None else ()

    def selection_clear(self, start, end):
        self.selection_clear_calls.append((start, end))

    def selection_set(self, index):
        self._selected_index = index
        self.selection_set_calls.append(index)

    def activate(self, index):
        self.activate_calls.append(index)

    def see(self, index):
        self.see_calls.append(index)


class _FakeWidget:
    """Records `pack`/`pack_forget`/`configure` calls without needing a real Tk root."""

    def __init__(self):
        self.packed = False
        self.pack_calls = []
        self.configure_calls = []

    def pack(self, **kwargs):
        self.packed = True
        self.pack_calls.append(kwargs)

    def pack_forget(self):
        self.packed = False

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)


class _DummyDetailPanelEditor(BlattwerkAppEditorCompletionPopupMixin):
    def __init__(self, items, selected_index=0):
        self._editor_completion_listbox = _FakeListbox(selected_index)
        self._editor_completion_items = items
        self._editor_completion_detail_frame = _FakeWidget()
        self._editor_completion_detail_title_label = _FakeWidget()
        self._editor_completion_detail_body_label = _FakeWidget()

    def _is_editor_completion_visible(self) -> bool:
        # Stubbed out -- these tests exercise the detail-panel update logic
        # `_on_editor_completion_move_up`/`_down` trigger, not the popup
        # visibility computation itself (covered elsewhere).
        return True


_DETAIL_WITH_HINT = {"title": "mode", "description": "Steuert das Ausgabeverhalten.", "value_hint": "Standard: worksheet"}
_DETAIL_WITHOUT_HINT = {"title": "Bestimmen", "description": "Den Wert ermitteln.", "value_hint": None}


def test_detail_panel_shows_title_and_description_for_candidate_with_detail():
    editor = _DummyDetailPanelEditor([{"label": "mode", "detail": _DETAIL_WITH_HINT}])

    editor._update_editor_completion_detail_panel()

    assert editor._editor_completion_detail_frame.packed is True
    assert editor._editor_completion_detail_title_label.configure_calls[-1] == {"text": "mode"}
    body_text = editor._editor_completion_detail_body_label.configure_calls[-1]["text"]
    assert "Steuert das Ausgabeverhalten." in body_text
    assert "Standard: worksheet" in body_text


def test_detail_panel_omits_value_hint_line_when_none():
    editor = _DummyDetailPanelEditor([{"label": "Bestimmen", "detail": _DETAIL_WITHOUT_HINT}])

    editor._update_editor_completion_detail_panel()

    body_text = editor._editor_completion_detail_body_label.configure_calls[-1]["text"]
    assert body_text == "Den Wert ermitteln."


def test_detail_panel_hides_column_when_candidate_has_no_detail():
    editor = _DummyDetailPanelEditor([{"label": "rows", "detail": None}])
    editor._editor_completion_detail_frame.packed = True  # simulate previously shown

    editor._update_editor_completion_detail_panel()

    assert editor._editor_completion_detail_frame.packed is False


def test_detail_panel_hides_column_when_candidate_has_no_detail_key_at_all():
    # block_option/option_value/frontmatter_value suggestions don't set
    # "detail" at all (scope decision: no data source yet) -- must be
    # treated identically to an explicit `None`.
    editor = _DummyDetailPanelEditor([{"label": "rows", "insert_text": "rows="}])
    editor._editor_completion_detail_frame.packed = True

    editor._update_editor_completion_detail_panel()

    assert editor._editor_completion_detail_frame.packed is False


def test_detail_panel_hides_column_when_nothing_is_selected():
    editor = _DummyDetailPanelEditor([{"label": "mode", "detail": _DETAIL_WITH_HINT}], selected_index=None)
    editor._editor_completion_detail_frame.packed = True

    editor._update_editor_completion_detail_panel()

    assert editor._editor_completion_detail_frame.packed is False


def test_detail_panel_update_is_a_no_op_before_popup_creation():
    editor = _DummyDetailPanelEditor([])
    editor._editor_completion_detail_frame = None
    editor._editor_completion_listbox = None

    editor._update_editor_completion_detail_panel()  # must not raise


def test_move_down_updates_detail_panel_for_newly_highlighted_candidate():
    editor = _DummyDetailPanelEditor(
        [
            {"label": "rows", "detail": None},
            {"label": "mode", "detail": _DETAIL_WITH_HINT},
        ],
        selected_index=0,
    )

    editor._on_editor_completion_move_down()

    assert editor._editor_completion_detail_frame.packed is True
    assert editor._editor_completion_detail_title_label.configure_calls[-1] == {"text": "mode"}


def test_move_up_updates_detail_panel_for_newly_highlighted_candidate():
    editor = _DummyDetailPanelEditor(
        [
            {"label": "mode", "detail": _DETAIL_WITH_HINT},
            {"label": "rows", "detail": None},
        ],
        selected_index=1,
    )

    editor._on_editor_completion_move_up()

    assert editor._editor_completion_detail_frame.packed is True
    assert editor._editor_completion_detail_title_label.configure_calls[-1] == {"text": "mode"}


def test_selection_changed_handler_updates_detail_panel_for_mouse_click():
    editor = _DummyDetailPanelEditor([{"label": "mode", "detail": _DETAIL_WITH_HINT}])

    editor._on_editor_completion_selection_changed()

    assert editor._editor_completion_detail_frame.packed is True
