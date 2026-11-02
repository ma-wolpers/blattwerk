"""Tests for frontmatter enum-value completion (`Stufe:`, `document_type:`)
in `blatt_ui_editor_completion_context.py`.
"""

from app.ui.blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin
from editor_text_fake import FakeEditorText


class _DummyContextEditor(BlattwerkAppEditorCompletionContextMixin):
    def __init__(self, text, cursor_line, cursor_col):
        self.editor_widget = FakeEditorText(text, cursor_line, cursor_col)
        self.user_preferences = {}


def test_stufe_value_completion_suggests_all_allowed_values():
    text = "---\nTitel: T\nStufe: "
    editor = _DummyContextEditor(text, cursor_line=3, cursor_col=len("Stufe: "))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["kind"] == "frontmatter_value"
    labels = {item["label"] for item in context["suggestions"]}
    assert labels == {"5", "6", "7", "8", "9", "10", "11", "12", "13", "e", "q1", "q2", "sek1", "sek2"}


def test_stufe_value_completion_filters_by_prefix():
    text = "---\nTitel: T\nStufe: q"
    editor = _DummyContextEditor(text, cursor_line=3, cursor_col=len("Stufe: q"))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    labels = {item["label"] for item in context["suggestions"]}
    assert labels == {"q1", "q2"}


def test_document_type_value_completion_still_works_after_adding_stufe():
    text = "---\nTitel: T\ndocument_type: "
    editor = _DummyContextEditor(text, cursor_line=3, cursor_col=len("document_type: "))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is not None
    assert context["kind"] == "frontmatter_value"
    labels = {item["label"] for item in context["suggestions"]}
    assert labels == {"exam", "kurzentwurf", "markdown", "presentation", "schild", "worksheet"}


def test_non_enum_frontmatter_field_has_no_value_completion():
    text = "---\nTitel: T\ncopyright: "
    editor = _DummyContextEditor(text, cursor_line=3, cursor_col=len("copyright: "))

    context = editor._collect_editor_completion_context(auto=False)

    assert context is None
