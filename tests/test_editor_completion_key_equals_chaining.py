from app.ui.blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin
from app.ui.blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin


class _FakeEditorWidget:
    def __init__(self):
        self.deleted = []
        self.inserted = []
        self.marks = []
        self.focused = False

    def delete(self, start, end):
        self.deleted.append((start, end))

    def insert(self, index, text):
        self.inserted.append((index, text))

    def mark_set(self, name, index):
        self.marks.append((name, index))

    def focus_set(self):
        self.focused = True

    def index(self, _index):
        return "1.0"


class _FakeListbox:
    def __init__(self, selected_index):
        self._selected_index = selected_index

    def curselection(self):
        return (self._selected_index,) if self._selected_index is not None else ()


class _DummyAcceptEditor(BlattwerkAppEditorCompletionPopupMixin):
    def __init__(self, items, selected_index=0):
        self.editor_widget = _FakeEditorWidget()
        self._editor_completion_listbox = _FakeListbox(selected_index)
        self._editor_completion_items = items
        self._editor_completion_replace_start = "1.0"
        self._editor_completion_replace_end = "1.0"
        self._editor_completion_context_kind = None
        self._editor_completion_context_meta = {}
        self._editor_completion_popup = None
        self.open_calls = []
        self.close_calls = []

    def _record_editor_completion_usage(self, candidate):
        pass

    def _queue_editor_highlighting(self, immediate=False):
        pass

    def _queue_editor_diagnostics(self, immediate=False):
        pass

    def _queue_editor_outline(self, immediate=False):
        pass

    def _open_editor_completion(self, auto):
        self.open_calls.append(auto)

    def _close_editor_completion(self):
        self.close_calls.append(True)


def test_accepting_block_option_key_reopens_completion_for_value():
    editor = _DummyAcceptEditor([{"label": "rows", "insert_text": "rows=", "kind": "block_option"}])

    editor._on_editor_completion_accept()

    assert editor.editor_widget.inserted == [("1.0", "rows=")]
    assert editor.open_calls == [True]
    assert editor.close_calls == []


def test_accepting_block_type_does_not_reopen_completion():
    editor = _DummyAcceptEditor(
        [{"label": "lines", "insert_text": "lines", "kind": "block_type", "block_type": "lines"}]
    )

    editor._on_editor_completion_accept()

    assert editor.open_calls == []
    assert editor.close_calls == [True]


def test_accepting_option_value_does_not_reopen_completion():
    editor = _DummyAcceptEditor(
        [{"label": "worksheet", "insert_text": "worksheet", "kind": "option_value"}]
    )

    editor._on_editor_completion_accept()

    assert editor.open_calls == []
    assert editor.close_calls == [True]


def test_should_chain_completion_after_accept_true_for_key_equals():
    assert BlattwerkAppEditorCompletionPopupMixin._should_chain_completion_after_accept(
        {"kind": "block_option"}, "rows="
    )


def test_should_chain_completion_after_accept_false_when_insert_text_lacks_equals():
    assert not BlattwerkAppEditorCompletionPopupMixin._should_chain_completion_after_accept(
        {"kind": "block_option"}, "rows"
    )


def test_should_chain_completion_after_accept_false_for_other_kinds():
    assert not BlattwerkAppEditorCompletionPopupMixin._should_chain_completion_after_accept(
        {"kind": "block_type"}, "lines="
    )


class _DummyContextEditor(BlattwerkAppEditorCompletionContextMixin):
    def __init__(self, text, cursor_line, cursor_col):
        self.editor_widget = _ContextFakeEditorWidget(text, cursor_line, cursor_col)
        self.user_preferences = {}


class _ContextFakeEditorWidget:
    def __init__(self, text, cursor_line, cursor_col):
        self._lines = text.splitlines()
        self._cursor_line = cursor_line
        self._cursor_col = cursor_col

    def index(self, _index):
        return f"{self._cursor_line}.{self._cursor_col}"

    def get(self, start, end):
        line_no = int(start.split(".")[0])
        return self._lines[line_no - 1] if 0 < line_no <= len(self._lines) else ""


def test_block_option_key_suggestions_include_trailing_equals_sign():
    # Direkt nach ":::grid " (Leerzeichen) sollen alle Optionen von grid
    # bereits mit angehaengtem "=" vorgeschlagen werden.
    editor = _DummyContextEditor(":::grid ", cursor_line=1, cursor_col=8)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["suggestions"]
    for item in context["suggestions"]:
        assert item["insert_text"] == f"{item['label']}="


def test_block_option_key_suggestions_carry_detail_right_after_block_header():
    editor = _DummyContextEditor(":::task ", cursor_line=1, cursor_col=8)

    context = editor._collect_editor_completion_context(auto=False)

    work_item = next(item for item in context["suggestions"] if item["label"] == "work")
    assert work_item["detail"] is not None
    assert work_item["detail"]["title"] == "work"


def test_block_option_key_suggestions_carry_detail_for_partial_key():
    editor = _DummyContextEditor(":::task wo", cursor_line=1, cursor_col=10)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    labels = {item["label"] for item in context["suggestions"]}
    assert "work" in labels
    work_item = next(item for item in context["suggestions"] if item["label"] == "work")
    assert work_item["detail"] is not None


def test_block_option_key_suggestions_exclude_already_used_keys_on_the_line():
    editor = _DummyContextEditor(":::task work=einzel ", cursor_line=1, cursor_col=21)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    labels = {item["label"] for item in context["suggestions"]}
    assert "work" not in labels
    assert "points" in labels  # a still-unused task option stays offered


def _all_task_option_names():
    from app.core.completion_catalogs import get_completion_options_for_block

    return set(get_completion_options_for_block("task"))


def test_block_option_key_suggestions_fall_back_to_full_list_when_all_keys_used():
    all_options = _all_task_option_names()
    used_up_line = ":::task " + " ".join(f"{name}=x" for name in all_options) + " "
    editor = _DummyContextEditor(used_up_line, cursor_line=1, cursor_col=len(used_up_line))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    labels = {item["label"] for item in context["suggestions"]}
    assert labels == all_options  # fallback: re-offer everything instead of an empty popup


def test_option_value_suggestions_carry_detail():
    editor = _DummyContextEditor(":::info type=", cursor_line=1, cursor_col=13)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["kind"] == "option_value"
    default_item = next(item for item in context["suggestions"] if item["insert_text"] == "default")
    assert default_item["detail"] is not None
    assert default_item["detail"]["value_hint"] == "Standard: default"


def test_frontmatter_value_suggestions_carry_detail():
    text = "---\nTitel: T\nmode: "
    editor = _DummyContextEditor(text, cursor_line=3, cursor_col=len("mode: "))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["kind"] == "frontmatter_value"
    worksheet_item = next(item for item in context["suggestions"] if item["insert_text"] == "worksheet")
    assert worksheet_item["detail"] is not None
    assert worksheet_item["detail"]["value_hint"] == "Standard: worksheet"
