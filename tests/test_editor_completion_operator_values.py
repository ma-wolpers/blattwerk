"""Tests for `!!...!!`-operator autocomplete and `_editor_read_frontmatter_meta`
in `blatt_ui_editor_completion_context.py`.
"""

from app.ui.blatt_ui_editor_completion_context import (
    _FRONTMATTER_SCAN_LINE_LIMIT,
    BlattwerkAppEditorCompletionContextMixin,
)


class _FakeEditorWidget:
    """Supports `.get()`/`.compare()`/`.index()`. `total_line_count` can be much
    larger than the actually-stored `text` lines, to simulate a huge
    document without materializing thousands of lines -- any `.get()` call
    past the stored lines (but within `total_line_count`) returns filler
    text, so a test can assert the frontmatter scan never reaches it.
    """

    def __init__(self, text, cursor_line, cursor_col, total_line_count=None):
        self._lines = text.splitlines()
        self._cursor_line = cursor_line
        self._cursor_col = cursor_col
        self._total_line_count = total_line_count if total_line_count is not None else len(self._lines)
        self.get_calls = []

    def index(self, _index):
        return f"{self._cursor_line}.{self._cursor_col}"

    def get(self, start, end):
        self.get_calls.append((start, end))
        line_no = int(start.split(".")[0])
        if 0 < line_no <= len(self._lines):
            return self._lines[line_no - 1]
        if line_no <= self._total_line_count:
            return "Filler-Zeile ohne Frontmatter-Bezug"
        return ""

    def compare(self, index1, op, index2):
        assert op == ">="
        assert index2 == "end-1c"
        line_no = int(index1.split(".")[0])
        return line_no > self._total_line_count


class _DummyContextEditor(BlattwerkAppEditorCompletionContextMixin):
    def __init__(self, text, cursor_line, cursor_col, total_line_count=None):
        self.editor_widget = _FakeEditorWidget(text, cursor_line, cursor_col, total_line_count)
        self.user_preferences = {}


def _doc(body_line, cursor_col=None):
    text = f"---\nTitel: T\nFach: Mathematik\nThema: X\n---\n{body_line}"
    cursor_line = 6
    if cursor_col is None:
        cursor_col = len(body_line)
    return text, cursor_line, cursor_col


def test_operator_completion_suggests_official_form_for_partial_word():
    text, cursor_line, cursor_col = _doc("!!Best")
    editor = _DummyContextEditor(text, cursor_line, cursor_col)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["kind"] == "operator_value"
    labels = {item["label"] for item in context["suggestions"]}
    assert "Bestimmen" in labels
    assert "bestimme" not in labels  # conjugated formen must never leak in


def test_operator_completion_none_without_matching_fach_data():
    text = "---\nTitel: T\nFach: Chemie\nThema: X\n---\n!!Best"
    editor = _DummyContextEditor(text, cursor_line=6, cursor_col=len("!!Best"))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is None


def test_operator_completion_none_when_marker_already_closed():
    text, cursor_line, _ = _doc("!!Bestimmen!! die Nullstellen")
    editor = _DummyContextEditor(text, cursor_line, cursor_col=len("!!Bestimmen!! die Nullstellen"))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is None


def test_operator_completion_none_when_closed_marker_is_followed_by_operator_like_text():
    # Regression: a naive "last !! to end of line" match would wrongly
    # treat "Begr" after an already-closed "!!Bestimmen!!" as a fresh open
    # marker's partial content (it happens to prefix-match "Begründen").
    # An even count of "!!" on this line means nothing is actually open.
    body = "!!Bestimmen!! die Nullstellen. Begr"
    text, cursor_line, _ = _doc(body)
    editor = _DummyContextEditor(text, cursor_line, cursor_col=len(body))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is None


def test_frontmatter_meta_reads_fach_and_stufe():
    text = "---\nTitel: T\nFach: Mathematik\nStufe: Q1\n---\n!!Best"
    editor = _DummyContextEditor(text, cursor_line=6, cursor_col=len("!!Best"))

    meta = editor._editor_read_frontmatter_meta()

    assert meta.get("Fach") == "Mathematik"
    assert str(meta.get("Stufe")) == "Q1"


def test_frontmatter_meta_gives_up_cleanly_without_second_delimiter():
    # No closing "---" within the scan limit -- must return {} instead of
    # reading the rest of a potentially very long document.
    text = "---\nTitel: T\nFach: Mathematik\n"
    editor = _DummyContextEditor(text, cursor_line=4, cursor_col=0, total_line_count=10_000)

    meta = editor._editor_read_frontmatter_meta()

    assert meta == {}


def test_frontmatter_meta_scan_is_bounded_regardless_of_document_length():
    # A 10,000-line document -- _editor_read_frontmatter_meta must never
    # read past _FRONTMATTER_SCAN_LINE_LIMIT, independent of total size or
    # cursor position deep in the document.
    text = "---\nTitel: T\nFach: Mathematik\nThema: X\n---\n"
    editor = _DummyContextEditor(text, cursor_line=9_000, cursor_col=0, total_line_count=10_000)

    meta = editor._editor_read_frontmatter_meta()

    assert meta.get("Fach") == "Mathematik"
    max_line_read = max(int(start.split(".")[0]) for start, _end in editor.editor_widget.get_calls)
    assert max_line_read <= _FRONTMATTER_SCAN_LINE_LIMIT
