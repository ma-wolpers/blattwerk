from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin
from app.ui.ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
)


class _FakeVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakePane:
    def winfo_exists(self):
        return True


class _FakeFocusableWidget:
    def __init__(self):
        self.focus_calls = 0

    def focus_set(self):
        self.focus_calls += 1

    def winfo_exists(self):
        return True


class _FakePanedWindow:
    def __init__(self):
        self.added = []

    def forget(self, _pane):
        pass

    def add(self, pane):
        self.added.append(pane)


class _FakeRoot:
    def __init__(self):
        self.focus_calls = 0

    def after_idle(self, _callback):
        pass

    def focus_set(self):
        self.focus_calls += 1


class _DummyViewModeEditor(BlattwerkAppEditorMixin):
    def __init__(self, mode):
        self.editor_preview_paned = _FakePanedWindow()
        self.editor_container = _FakePane()
        self.preview_container = _FakePane()
        self.editor_view_mode_var = _FakeVar(mode)
        self.editor_widget = _FakeFocusableWidget()
        self.preview_canvas = _FakeFocusableWidget()
        self.root = _FakeRoot()
        self._editor_search_visible = False
        self._equal_split_attempts = 0
        self._reduce_motion = True
        self.close_completion_calls = 0
        self.close_search_calls = 0

    def _close_editor_completion(self):
        self.close_completion_calls += 1

    def _close_editor_search_bar(self, _event=None):
        self.close_search_calls += 1

    def _set_equal_split(self):
        pass


def test_editor_only_mode_focuses_editor_widget():
    editor = _DummyViewModeEditor(EDITOR_VIEW_EDITOR_ONLY)

    editor._apply_editor_view_mode()

    assert editor.editor_widget.focus_calls == 1
    assert editor.preview_canvas.focus_calls == 0


def test_both_mode_focuses_editor_widget():
    editor = _DummyViewModeEditor(EDITOR_VIEW_BOTH)

    editor._apply_editor_view_mode()

    assert editor.editor_widget.focus_calls == 1
    assert editor.preview_canvas.focus_calls == 0


def test_preview_only_mode_focuses_preview_canvas_not_editor():
    editor = _DummyViewModeEditor(EDITOR_VIEW_PREVIEW_ONLY)

    editor._apply_editor_view_mode()

    assert editor.preview_canvas.focus_calls == 1
    assert editor.editor_widget.focus_calls == 0


def test_preview_only_mode_closes_completion_popup():
    editor = _DummyViewModeEditor(EDITOR_VIEW_PREVIEW_ONLY)

    editor._apply_editor_view_mode()

    assert editor.close_completion_calls == 1


def test_preview_only_mode_closes_open_search_bar():
    editor = _DummyViewModeEditor(EDITOR_VIEW_PREVIEW_ONLY)
    editor._editor_search_visible = True

    editor._apply_editor_view_mode()

    assert editor.close_search_calls == 1


def test_preview_only_mode_does_not_close_search_bar_when_already_closed():
    editor = _DummyViewModeEditor(EDITOR_VIEW_PREVIEW_ONLY)
    editor._editor_search_visible = False

    editor._apply_editor_view_mode()

    assert editor.close_search_calls == 0


def test_preview_only_falls_back_to_root_focus_when_canvas_missing():
    editor = _DummyViewModeEditor(EDITOR_VIEW_PREVIEW_ONLY)
    editor.preview_canvas = None

    editor._apply_editor_view_mode()

    assert editor.root.focus_calls == 1


def test_focus_editor_widget_if_available_noop_when_editor_widget_is_none():
    editor = _DummyViewModeEditor(EDITOR_VIEW_EDITOR_ONLY)
    editor.editor_widget = None

    # Darf nicht abstuerzen, obwohl kein editor_widget existiert.
    editor._apply_editor_view_mode()
