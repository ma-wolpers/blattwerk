from app.ui.blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin


class _FakeEditorWidget:
    def __init__(self):
        self.inserted = []
        self.seen = []

    def insert(self, index, text):
        self.inserted.append((index, text))

    def see(self, index):
        self.seen.append(index)


class _DummyEditor(BlattwerkAppEditorCompletionPopupMixin):
    def __init__(self):
        self.editor_widget = _FakeEditorWidget()
        self._editor_completion_popup = None
        self._editor_completion_listbox = None
        self._editor_completion_items = ["stale-suggestion"]
        self._editor_completion_replace_start = "3.0"
        self._editor_completion_replace_end = "3.5"
        self._editor_completion_context_kind = "block_type"
        self._editor_completion_context_meta = {"block_type": "info"}
        self.highlight_calls = []
        self.diagnostics_calls = []
        self.outline_calls = []

    def _queue_editor_highlighting(self, immediate=False):
        self.highlight_calls.append(immediate)

    def _queue_editor_diagnostics(self, immediate=False):
        self.diagnostics_calls.append(immediate)

    def _queue_editor_outline(self, immediate=False):
        self.outline_calls.append(immediate)


def test_reject_and_newline_closes_open_popup_state():
    editor = _DummyEditor()

    editor._on_editor_completion_reject_and_newline()

    assert editor._editor_completion_items == []
    assert editor._editor_completion_replace_start is None
    assert editor._editor_completion_replace_end is None
    assert editor._editor_completion_context_kind is None
    assert editor._editor_completion_context_meta == {}


def test_reject_and_newline_inserts_plain_newline_at_cursor():
    editor = _DummyEditor()

    editor._on_editor_completion_reject_and_newline()

    assert editor.editor_widget.inserted == [("insert", "\n")]
    assert editor.editor_widget.seen == ["insert"]


def test_reject_and_newline_refreshes_highlighting_diagnostics_outline_immediately():
    editor = _DummyEditor()

    editor._on_editor_completion_reject_and_newline()

    assert editor.highlight_calls == [True]
    assert editor.diagnostics_calls == [True]
    assert editor.outline_calls == [True]


def test_reject_and_newline_returns_break_to_stop_further_event_propagation():
    editor = _DummyEditor()

    result = editor._on_editor_completion_reject_and_newline()

    assert result == "break"


def test_reject_and_newline_also_works_without_an_open_popup():
    editor = _DummyEditor()
    editor._editor_completion_items = []

    result = editor._on_editor_completion_reject_and_newline()

    assert result == "break"
    assert editor.editor_widget.inserted == [("insert", "\n")]
