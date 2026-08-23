from app.ui.blatt_ui_editor_completion_context import (
    BlattwerkAppEditorCompletionContextMixin,
    _format_option_value_label,
)


class _DummySuggestionEditor(BlattwerkAppEditorCompletionContextMixin):
    def __init__(self, user_preferences):
        self.editor_widget = None
        self.user_preferences = user_preferences


def test_format_option_value_label_appends_abbreviation_hint():
    assert _format_option_value_label("gruppe", {"gruppe": "ga"}) == "gruppe (ga)"


def test_format_option_value_label_without_hint_returns_value_unchanged():
    assert _format_option_value_label("gruppe", {}) == "gruppe"


def test_build_option_value_suggestions_defaults_to_german_without_abbreviations():
    editor = _DummySuggestionEditor(user_preferences={})

    suggestions = editor._build_option_value_suggestions(
        block_type="task", option_key="work", value_prefix=""
    )

    labels = {item["label"] for item in suggestions}
    insert_texts = {item["insert_text"] for item in suggestions}
    assert labels == {"einzel", "partner", "gruppe"}
    assert insert_texts == {"einzel", "partner", "gruppe"}


def test_build_option_value_suggestions_english_style():
    editor = _DummySuggestionEditor(
        user_preferences={"option_value_language_style": "english"}
    )

    suggestions = editor._build_option_value_suggestions(
        block_type="task", option_key="work", value_prefix=""
    )

    assert {item["label"] for item in suggestions} == {"single", "partner", "group"}


def test_build_option_value_suggestions_abbreviations_are_label_only():
    editor = _DummySuggestionEditor(
        user_preferences={
            "option_value_language_style": "german",
            "option_value_show_abbreviations": True,
        }
    )

    suggestions = editor._build_option_value_suggestions(
        block_type="task", option_key="work", value_prefix="gruppe"
    )

    assert len(suggestions) == 1
    entry = suggestions[0]
    assert entry["label"] == "gruppe (ga)"
    assert entry["insert_text"] == "gruppe"


def test_build_option_value_suggestions_abbreviation_toggle_off_shows_plain_label():
    editor = _DummySuggestionEditor(
        user_preferences={
            "option_value_language_style": "german",
            "option_value_show_abbreviations": False,
        }
    )

    suggestions = editor._build_option_value_suggestions(
        block_type="task", option_key="work", value_prefix="gruppe"
    )

    assert suggestions[0]["label"] == "gruppe"
