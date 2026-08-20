from app.ui.blatt_ui_editor_search import BlattwerkAppEditorSearchMixin


class _FakeVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeEditorWidget:
    def __init__(self, text):
        self._text = text
        self.added_tags = []
        self.removed_tags = []
        self.marks = []
        self.seen = []
        self.deleted = []
        self.inserted = []
        self._cursor_offset = 0
        self._selection = None

    # --- Lesen ---
    def get(self, start, end):
        if start == "1.0" and end == "end-1c":
            return self._text
        if self._selection is not None and (start, end) == self._selection[:2]:
            return self._selection[2]
        return self._text

    def tag_ranges(self, _tag):
        if self._selection is None:
            return ()
        return (self._selection[0], self._selection[1])

    def count(self, _start, _end, _mode):
        return self._cursor_offset

    # --- Schreiben ---
    def tag_add(self, tag_name, start, end):
        self.added_tags.append((tag_name, start, end))

    def tag_remove(self, tag_name, _start, _end):
        self.removed_tags.append(tag_name)

    def mark_set(self, name, index):
        self.marks.append((name, index))
        if name == "insert" and index.startswith("1.0+") and index.endswith("c"):
            self._cursor_offset = int(index[len("1.0+"):-1])

    def see(self, index):
        self.seen.append(index)

    def delete(self, start, end):
        self.deleted.append((start, end))

    def insert(self, index, text):
        self.inserted.append((index, text))
        # Vereinfachtes Modell: nur fuer die einfachen Ersetzen-Tests genutzt,
        # bildet keine vollstaendige Tk-Textbuffer-Semantik nach.

    def focus_set(self):
        pass


class _FakeFrame:
    def __init__(self):
        self.packed = False
        self.pack_calls = []

    def pack(self, **kwargs):
        self.packed = True
        self.pack_calls.append(kwargs)

    def pack_forget(self):
        self.packed = False


class _FakeEntry(_FakeFrame):
    def __init__(self):
        super().__init__()
        self.focused = False
        self.selected_range = None

    def focus_set(self):
        self.focused = True

    def select_range(self, start, end):
        self.selected_range = (start, end)

    def icursor(self, _index):
        pass


class _DummySearchEditor(BlattwerkAppEditorSearchMixin):
    def __init__(self, text, cursor_offset=0, selection=None):
        self.editor_widget = _FakeEditorWidget(text)
        self.editor_widget._cursor_offset = cursor_offset
        self.editor_widget._selection = selection
        self._editor_search_frame = _FakeFrame()
        self._editor_search_replace_row = _FakeFrame()
        self._editor_search_before_widget = object()
        self._editor_search_query_entry = _FakeEntry()
        self._editor_search_replace_entry = _FakeEntry()
        self._editor_search_visible = False
        self._editor_search_replace_visible = False
        self._editor_search_matches = []
        self._editor_search_current_index = None
        self._editor_search_query_var = _FakeVar("")
        self._editor_search_replace_var = _FakeVar("")
        self._editor_search_case_sensitive_var = _FakeVar(False)
        self._editor_search_match_count_var = _FakeVar("0/0")
        self.status_var = _FakeVar("")

    def _queue_editor_highlighting(self, immediate=False):
        pass

    def _queue_editor_diagnostics(self, immediate=False):
        pass

    def _queue_editor_outline(self, immediate=False):
        pass


# --- Grundverhalten: leere Suchanfrage ----------------------------------

def test_empty_query_produces_zero_of_zero_and_no_tags():
    editor = _DummySearchEditor("hello world hello")
    editor._editor_search_query_var.set("")

    editor._run_editor_search(direction=0)

    assert editor._editor_search_match_count_var.get() == "0/0"
    assert editor._editor_search_matches == []
    assert editor._editor_search_current_index is None
    assert editor.editor_widget.added_tags == []


def test_empty_query_replace_current_is_noop():
    editor = _DummySearchEditor("hello world")
    editor._editor_search_query_var.set("")

    result = editor._replace_current_editor_match()

    assert result == "break"
    assert editor.editor_widget.deleted == []


def test_empty_query_replace_all_is_noop():
    editor = _DummySearchEditor("hello world")
    editor._editor_search_query_var.set("")

    result = editor._replace_all_editor_matches()

    assert result == "break"
    assert editor.editor_widget.deleted == []


# --- Grundsuche und Trefferzaehler --------------------------------------

def test_search_starts_from_cursor_and_updates_counter():
    editor = _DummySearchEditor("aa bb aa cc aa", cursor_offset=5)
    editor._editor_search_query_var.set("aa")

    editor._run_editor_search(direction=0)

    # Treffer bei 0, 6, 12 -- ab Cursor 5 ist der naechste Treffer bei Index 1 (6).
    assert editor._editor_search_matches == [(0, 2), (6, 8), (12, 14)]
    assert editor._editor_search_current_index == 1
    assert editor._editor_search_match_count_var.get() == "2/3"


def test_search_no_matches_shows_zero_of_zero():
    editor = _DummySearchEditor("hello world")
    editor._editor_search_query_var.set("xyz")

    editor._run_editor_search(direction=0)

    assert editor._editor_search_match_count_var.get() == "0/0"
    assert editor._editor_search_current_index is None


def test_forward_navigation_wraps_cyclically():
    editor = _DummySearchEditor("aa bb aa cc aa")
    editor._editor_search_query_var.set("aa")
    editor._run_editor_search(direction=0)  # startet bei erstem Treffer (Cursor 0)
    assert editor._editor_search_current_index == 0

    editor._run_editor_search(direction=1)
    assert editor._editor_search_current_index == 1
    editor._run_editor_search(direction=1)
    assert editor._editor_search_current_index == 2
    editor._run_editor_search(direction=1)
    assert editor._editor_search_current_index == 0  # zyklisch zurueck zum Anfang


def test_backward_navigation_wraps_cyclically():
    editor = _DummySearchEditor("aa bb aa cc aa")
    editor._editor_search_query_var.set("aa")
    editor._run_editor_search(direction=0)
    assert editor._editor_search_current_index == 0

    editor._run_editor_search(direction=-1)
    assert editor._editor_search_current_index == 2  # zyklisch zum letzten Treffer


def test_case_sensitivity_toggle_reruns_search_immediately():
    editor = _DummySearchEditor("Hello hello")
    editor._editor_search_query_var.set("hello")
    editor._editor_search_case_sensitive_var.set(False)
    editor._run_editor_search(direction=0)
    assert len(editor._editor_search_matches) == 2

    editor._editor_search_case_sensitive_var.set(True)
    editor._toggle_editor_search_case_sensitive()

    assert editor._editor_search_matches == [(6, 11)]


def test_current_match_gets_distinct_tag_from_other_matches():
    editor = _DummySearchEditor("aa bb aa")
    editor._editor_search_query_var.set("aa")

    editor._run_editor_search(direction=0)

    current_tags = [t for t in editor.editor_widget.added_tags if t[0] == "search_match_current"]
    other_tags = [t for t in editor.editor_widget.added_tags if t[0] == "search_match"]
    assert len(current_tags) == 1
    assert len(other_tags) == 1


# --- Oeffnen der Suchleiste: Selektion uebernehmen ----------------------

def test_opening_find_bar_with_selection_prefills_query():
    editor = _DummySearchEditor(
        "hello world", selection=("1.0", "1.5", "hello")
    )

    editor._open_editor_search_bar(show_replace=False)

    assert editor._editor_search_query_var.get() == "hello"
    assert editor._editor_search_frame.packed is True


def test_opening_find_bar_without_selection_clears_query():
    editor = _DummySearchEditor("hello world")
    editor._editor_search_query_var.set("stale query")

    editor._open_editor_search_bar(show_replace=False)

    assert editor._editor_search_query_var.get() == ""


def test_opening_replace_bar_shows_replace_row():
    editor = _DummySearchEditor("hello world")

    editor._open_editor_search_bar(show_replace=True)

    assert editor._editor_search_replace_row.packed is True


def test_opening_find_only_does_not_show_replace_row():
    editor = _DummySearchEditor("hello world")

    editor._open_editor_search_bar(show_replace=False)

    assert editor._editor_search_replace_row.packed is False


# --- Schliessen ----------------------------------------------------------

def test_closing_search_bar_clears_tags_and_state():
    editor = _DummySearchEditor("aa bb aa")
    editor._open_editor_search_bar(show_replace=False)
    editor._editor_search_query_var.set("aa")
    editor._run_editor_search(direction=0)
    assert editor._editor_search_matches

    editor._close_editor_search_bar()

    assert editor._editor_search_frame.packed is False
    assert editor._editor_search_visible is False
    assert editor._editor_search_matches == []
    assert editor._editor_search_current_index is None
    assert "search_match" in editor.editor_widget.removed_tags
    assert "search_match_current" in editor.editor_widget.removed_tags


# --- Ersetzen -------------------------------------------------------------

def test_replace_current_match_replaces_and_advances():
    editor = _DummySearchEditor("aa bb aa")
    editor._editor_search_query_var.set("aa")
    editor._editor_search_replace_var.set("xx")
    editor._run_editor_search(direction=0)
    assert editor._editor_search_current_index == 0

    editor._replace_current_editor_match()

    assert editor.editor_widget.deleted == [("1.0+0c", "1.0+2c")]
    assert editor.editor_widget.inserted == [("1.0+0c", "xx")]


def test_replace_current_match_without_active_match_is_noop():
    editor = _DummySearchEditor("hello world")
    editor._editor_search_query_var.set("xyz")
    editor._run_editor_search(direction=0)
    assert editor._editor_search_current_index is None

    result = editor._replace_current_editor_match()

    assert result == "break"
    assert editor.editor_widget.deleted == []


def test_replace_all_matches_processes_in_reverse_order():
    editor = _DummySearchEditor("aa bb aa cc aa")
    editor._editor_search_query_var.set("aa")
    editor._editor_search_replace_var.set("xx")

    editor._replace_all_editor_matches()

    assert editor.editor_widget.deleted == [
        ("1.0+12c", "1.0+14c"),
        ("1.0+6c", "1.0+8c"),
        ("1.0+0c", "1.0+2c"),
    ]
    assert editor.editor_widget.inserted == [
        ("1.0+12c", "xx"),
        ("1.0+6c", "xx"),
        ("1.0+0c", "xx"),
    ]
    assert editor.status_var.get() == "3 Ersetzung(en) durchgeführt."


def test_replace_all_matches_with_no_matches_reports_zero_and_no_edits():
    editor = _DummySearchEditor("hello world")
    editor._editor_search_query_var.set("xyz")

    editor._replace_all_editor_matches()

    assert editor.editor_widget.deleted == []
    assert editor._editor_search_match_count_var.get() == "0/0"
