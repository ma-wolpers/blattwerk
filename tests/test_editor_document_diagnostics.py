from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin


class _FakeEditorWidget:
    def __init__(self, text):
        self._text = text
        self.added_tags = []

    def get(self, _start, _end):
        return self._text

    def tag_remove(self, _tag, _start, _end):
        return None

    def tag_add(self, tag_name, start, end):
        self.added_tags.append((tag_name, start, end))

    def index(self, _index):
        line_count = max(1, len(self._text.splitlines()) + (0 if self._text.endswith("\n") else 0))
        return f"{line_count}.0"


class _DummyDiagnosticsEditor(BlattwerkAppEditorMixin):
    def __init__(self, text):
        self.editor_widget = _FakeEditorWidget(text)
        self.editor_diagnostics_listbox = None
        self.user_preferences = {"document_type_detection_mode": "yaml_keys"}
        self._editor_diagnostics_after_id = None
        self._editor_block_pairs_cache = []
        self.items = None

    def _set_editor_diagnostics(self, items):
        self.items = list(items)


def test_refresh_editor_diagnostics_skips_blattwerk_structure_suffix_checks_for_kurzentwurf():
    editor = _DummyDiagnosticsEditor(
        "---\n"
        "Stundenthema: Thema\n"
        "Lerngruppe: 6a\n"
        "start: 08:00\n"
        "---\n"
        ":::lines\n"
    )

    editor._refresh_editor_diagnostics()

    codes = {item["code"] for item in editor.items}
    assert "KZF010" in codes
    assert "SY001" not in codes
    assert "SY002" not in codes