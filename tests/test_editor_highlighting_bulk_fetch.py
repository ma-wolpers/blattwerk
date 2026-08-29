"""Regression tests for the bulk-fetch fix in `_refresh_editor_highlighting`/
`_refresh_editor_outline`/`_refresh_editor_block_pair_highlight` (Perf-Fix
2026-08-29, Blattwerk Item 1 of the CPU/Memory analysis plan).

Before the fix, both refresh functions fetched the full buffer once and then
queried the widget again for every single line inside their loop -- an O(N)
Tk round-trip cost that scaled with document length even though the full
text was already available. These tests prove the *mechanism* (bounded
`.get()` call count, independent of document length) rather than just the
unchanged output, since a call-count regression could easily slip back in
without changing any visible tag.
"""

from __future__ import annotations

import re

from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin


class _FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.after_cancel_calls = []

    def after(self, delay_ms, callback):
        timer_id = f"timer-{len(self.after_calls) + 1}"
        self.after_calls.append((delay_ms, callback, timer_id))
        return timer_id

    def after_cancel(self, timer_id):
        self.after_cancel_calls.append(timer_id)


class _FakeTextWidget:
    """Minimal Tk `Text` double that supports exactly the index forms used
    by the editor's syntax/outline/block-pair refresh functions, with real
    line-splitting semantics (verified against a live `tkinter.Text` widget
    for the "1.0"/"end-1c"/"N.0"/"N.end" index forms, including empty-buffer
    and trailing-newline edge cases)."""

    def __init__(self, content: str):
        self.lines = content.split("\n")
        self.insert_mark = "1.0"
        self.get_calls: list[tuple[str, str]] = []
        self.tag_add_calls: list[tuple[str, str, str]] = []
        self.tag_remove_calls: list[tuple[str, str, str]] = []

    def get(self, start: str, end: str) -> str:
        self.get_calls.append((start, end))
        if start == "1.0" and end == "end-1c":
            return "\n".join(self.lines)
        line_no = int(start.split(".")[0])
        return self.lines[line_no - 1]

    def index(self, idx: str) -> str:
        if idx == "end-1c":
            return f"{len(self.lines)}.{len(self.lines[-1])}"
        if idx == "insert":
            return self.insert_mark
        raise ValueError(f"unsupported index in fake widget: {idx!r}")

    def tag_remove(self, tag, start, end):
        self.tag_remove_calls.append((tag, start, end))

    def tag_add(self, tag, start, end):
        self.tag_add_calls.append((tag, start, end))


class _FakeKeyEvent:
    def __init__(self, keysym: str, char: str = ""):
        self.keysym = keysym
        self.char = char


class _DummyEditor(BlattwerkAppEditorMixin):
    def __init__(self, content: str):
        self.root = _FakeRoot()
        self.editor_widget = _FakeTextWidget(content)
        self.editor_outline_listbox = None
        self._editor_highlighting_after_id = None
        self._editor_outline_after_id = None
        self._editor_block_pair_after_id = None
        self._editor_block_pair_delay_ms = 120
        self._editor_block_pairs_cache = []
        self._editor_outline_items = []
        self.user_preferences = {}


_SAMPLE_DOCUMENT = "\n".join(
    [
        "---",  # 1
        "Stundentyp: Unterricht",  # 2
        "---",  # 3
        "",  # 4
        ":::aufgabe typ=mc",  # 5
        "§ Frage 1",  # 6
        ":::",  # 7
    ]
)


def test_refresh_editor_highlighting_fetches_full_text_once():
    app = _DummyEditor(_SAMPLE_DOCUMENT)

    app._refresh_editor_highlighting()

    full_fetch_calls = [c for c in app.editor_widget.get_calls if c == ("1.0", "end-1c")]
    assert len(full_fetch_calls) == 1
    # No per-line re-fetch for the 7 lines of the document -- only the single
    # bulk fetch above (block-pair highlighting adds at most 2 more, bounded
    # by pair count, not document length; here the cursor sits outside any
    # pair so it adds none).
    assert len(app.editor_widget.get_calls) == 1


def test_refresh_editor_highlighting_call_count_independent_of_document_length():
    small = _DummyEditor(_SAMPLE_DOCUMENT)
    large_content = "\n".join([f"plain text line {n}" for n in range(500)])
    large = _DummyEditor(large_content)

    small._refresh_editor_highlighting()
    large._refresh_editor_highlighting()

    assert len(small.editor_widget.get_calls) == len(large.editor_widget.get_calls) == 1


def test_refresh_editor_highlighting_tags_expected_positions():
    app = _DummyEditor(_SAMPLE_DOCUMENT)

    app._refresh_editor_highlighting()

    tags = app.editor_widget.tag_add_calls
    assert ("syn_frontmatter_delim", "1.0", "1.end") in tags
    assert ("syn_frontmatter_key", "2.0", "2.10") in tags
    assert ("syn_frontmatter_delim", "3.0", "3.end") in tags
    assert ("syn_block_fence", "5.0", "5.3") in tags
    assert ("syn_block_type", "5.3", "5.10") in tags
    assert ("syn_option_key", "5.11", "5.14") in tags
    assert ("syn_option_value", "5.15", "5.17") in tags
    assert ("syn_marker", "6.0", "6.1") in tags
    assert ("syn_block_fence", "7.0", "7.3") in tags


def test_refresh_editor_outline_fetches_full_text_once_not_per_line():
    app = _DummyEditor(_SAMPLE_DOCUMENT)

    app._refresh_editor_outline()

    assert len(app.editor_widget.get_calls) == 1
    assert app.editor_widget.get_calls[0] == ("1.0", "end-1c")


def test_refresh_editor_outline_builds_expected_items():
    app = _DummyEditor(_SAMPLE_DOCUMENT)

    app._refresh_editor_outline()

    labels = [item["label"] for item in app._editor_outline_items]
    assert any("Frontmatter" in label for label in labels)
    assert any(re.search(r"aufgabe", label) for label in labels)


def test_refresh_editor_block_pair_highlight_touches_only_pair_lines():
    app = _DummyEditor(_SAMPLE_DOCUMENT)
    app._refresh_editor_highlighting()  # populates _editor_block_pairs_cache = [(5, 7)]
    app.editor_widget.get_calls.clear()
    app.editor_widget.tag_add_calls.clear()
    app.editor_widget.insert_mark = "6.0"  # cursor inside the aufgabe block

    app._refresh_editor_block_pair_highlight()

    # Exactly the two marker lines (open + close), never all 7 document lines.
    assert len(app.editor_widget.get_calls) == 2
    assert ("5.0", "5.end") in app.editor_widget.get_calls
    assert ("7.0", "7.end") in app.editor_widget.get_calls
    assert ("syn_block_pair", "5.0", "5.10") in app.editor_widget.tag_add_calls
    assert ("syn_block_pair", "7.0", "7.3") in app.editor_widget.tag_add_calls


def test_key_release_arrow_navigation_debounces_block_pair_highlight():
    app = _DummyEditor(_SAMPLE_DOCUMENT)

    for _ in range(5):
        app._on_editor_key_release(_FakeKeyEvent("Right"))

    # Each keystroke schedules a new timer and cancels the previous pending
    # one -- rapid navigation collapses into a single pending refresh instead
    # of firing `_refresh_editor_block_pair_highlight` synchronously 5 times.
    assert len(app.root.after_calls) == 5
    assert len(app.root.after_cancel_calls) == 4
    last_timer_id = app.root.after_calls[-1][2]
    assert last_timer_id not in app.root.after_cancel_calls
    assert app.editor_widget.get_calls == []  # nothing ran synchronously yet


def test_queue_editor_block_pair_highlight_immediate_runs_synchronously():
    app = _DummyEditor(_SAMPLE_DOCUMENT)
    app._editor_block_pairs_cache = [(5, 7)]
    app.editor_widget.insert_mark = "6.0"

    app._queue_editor_block_pair_highlight(immediate=True)

    assert app.root.after_calls == []
    assert ("syn_block_pair", "5.0", "5.10") in app.editor_widget.tag_add_calls
