from app.ui.blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin


class _FakeEditorWidget:
    def __init__(self, text, cursor_line, cursor_col):
        self._lines = text.splitlines()
        self._cursor_line = cursor_line
        self._cursor_col = cursor_col

    def index(self, _index):
        return f"{self._cursor_line}.{self._cursor_col}"

    def get(self, start, end):
        line_no = int(start.split(".")[0])
        line_text = self._lines[line_no - 1] if 0 < line_no <= len(self._lines) else ""
        return line_text


class _DummyContextEditor(BlattwerkAppEditorCompletionContextMixin):
    def __init__(self, text, cursor_line, cursor_col):
        self.editor_widget = _FakeEditorWidget(text, cursor_line, cursor_col)
        self.user_preferences = {}


def test_exact_single_block_type_match_suppresses_popup():
    # ":::lines" mit Cursor direkt am Zeilenende -- "lines" ist der einzige
    # Blocktyp, der mit "lines" beginnt.
    editor = _DummyContextEditor(":::lines", cursor_line=1, cursor_col=8)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is None


def test_partial_block_type_prefix_still_shows_suggestions():
    # ":::lin" ist kein exakter Treffer -- weiterhin Vorschlaege erwuenscht.
    editor = _DummyContextEditor(":::lin", cursor_line=1, cursor_col=6)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["suggestions"]


def test_helper_returns_false_for_empty_prefix():
    assert not BlattwerkAppEditorCompletionContextMixin._is_single_exact_completion_match(
        "", [{"insert_text": "lines"}]
    )


def test_helper_returns_false_for_multiple_suggestions():
    assert not BlattwerkAppEditorCompletionContextMixin._is_single_exact_completion_match(
        "li", [{"insert_text": "lines"}, {"insert_text": "linebreak"}]
    )


def test_helper_returns_true_for_single_exact_case_insensitive_match():
    assert BlattwerkAppEditorCompletionContextMixin._is_single_exact_completion_match(
        "Lines", [{"insert_text": "lines"}]
    )


def test_exact_single_block_option_key_match_suppresses_popup():
    # ":::grid rows" -- "rows" ist die einzige grid-Option, die mit "rows" beginnt.
    editor = _DummyContextEditor(":::grid rows", cursor_line=1, cursor_col=12)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is None


def test_helper_returns_false_for_single_non_exact_match():
    assert not BlattwerkAppEditorCompletionContextMixin._is_single_exact_completion_match(
        "lin", [{"insert_text": "lines"}]
    )


def test_helper_compares_against_label_not_insert_text_for_self_closing_types():
    # `insert_text` traegt bei selbstschliessenden Typen zusaetzlich das
    # automatisch angehaengte "::: " -- der Vergleich muss trotzdem ueber
    # `label` (den getippten Namen) exakt treffen.
    assert BlattwerkAppEditorCompletionContextMixin._is_single_exact_completion_match(
        "nextcol", [{"label": "nextcol", "insert_text": "nextcol :::"}]
    )


def test_self_closing_block_type_suggestion_appends_closing_fence():
    # ":::nextc" -- "nextcol" ist der einzige passende Blocktyp, aber kein
    # exakter Treffer, daher bleibt das Popup offen und liefert den
    # vervollstaendigten Marker inklusive schliessendem ':::'.
    editor = _DummyContextEditor(":::nextc", cursor_line=1, cursor_col=8)

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert len(context["suggestions"]) == 1
    assert context["suggestions"][0]["insert_text"] == "nextcol :::"


def test_regular_block_type_suggestion_does_not_append_closing_fence():
    editor = _DummyContextEditor(":::lin", cursor_line=1, cursor_col=6)

    context = editor._collect_editor_completion_context(auto=False)

    matches = [item for item in context["suggestions"] if item["label"] == "lines"]
    assert matches
    assert matches[0]["insert_text"] == "lines"
