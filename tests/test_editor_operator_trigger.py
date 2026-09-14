"""Regression test for the `!!`-operator autocomplete auto-trigger.

`_collect_editor_completion_context` already returns the full operator
suggestion list for an empty prefix right after `!!` (see
`test_editor_completion_operator_values.py`) -- the gap fixed here is one
level up: `_on_editor_key_release`'s `trigger_chars` gate didn't include `!`,
so typing the second `!` of `!!` never called `_open_editor_completion`
automatically. This test spies on that call directly, independent of the
context-detection logic already covered elsewhere.
"""

from __future__ import annotations

from app.ui.blatt_ui_editor import BlattwerkAppEditorMixin
from app.ui.blatt_ui_editor_diagnostics import BlattwerkAppEditorDiagnosticsMixin


class _FakeRoot:
    def after(self, _delay_ms, _callback):
        return "timer-1"

    def after_cancel(self, _timer_id):
        pass


class _FakeTextWidget:
    """Minimal double -- only what `_on_editor_key_release` touches before
    the trigger-chars check (`bbox`/`index` are never reached in this test
    since the completion popup itself is stubbed out below)."""

    def __init__(self, content: str = ""):
        self.lines = content.split("\n")

    def get(self, start: str, end: str) -> str:
        if start == "1.0" and end == "end-1c":
            return "\n".join(self.lines)
        line_no = int(start.split(".")[0])
        return self.lines[line_no - 1]

    def index(self, idx: str) -> str:
        if idx == "end-1c":
            return f"{len(self.lines)}.{len(self.lines[-1])}"
        raise ValueError(f"unsupported index in fake widget: {idx!r}")


class _FakeKeyEvent:
    def __init__(self, keysym: str, char: str = ""):
        self.keysym = keysym
        self.char = char


class _DummyEditor(BlattwerkAppEditorDiagnosticsMixin, BlattwerkAppEditorMixin):
    """Spies on `_open_editor_completion`/`_close_editor_completion` instead
    of wiring up the full completion-context/popup mixins -- the trigger-
    chars gate is the only thing under test here."""

    def __init__(self, content: str = ""):
        self.root = _FakeRoot()
        self.editor_widget = _FakeTextWidget(content)
        self._editor_highlighting_after_id = None
        self._editor_outline_after_id = None
        self._editor_block_pair_after_id = None
        self._editor_block_pair_delay_ms = 120
        self._editor_block_pairs_cache = []
        self.user_preferences = {}
        self.open_completion_calls: list[bool] = []
        self.close_completion_calls = 0

    def _open_editor_completion(self, auto: bool):
        self.open_completion_calls.append(auto)

    def _close_editor_completion(self):
        self.close_completion_calls += 1


def test_second_exclamation_mark_of_open_operator_marker_triggers_completion():
    app = _DummyEditor("!")

    app._on_editor_key_release(_FakeKeyEvent("exclam", char="!"))

    assert app.open_completion_calls == [True]


def test_lone_exclamation_mark_outside_any_marker_still_triggers_context_lookup():
    # "!" is now an unconditional trigger char, same as the pre-existing "_"
    # -- it always calls `_open_editor_completion(auto=True)`, which is what
    # then asks the context layer whether anything actually matches. Outside
    # an open `!!...!!` marker the context layer returns `None` and the
    # popup closes itself (proven by `test_operator_completion_none_*` in
    # `test_editor_completion_operator_values.py`); this test only proves
    # the key-release gate now behaves identically for "!" as it already
    # does for the other trigger characters, not the context result itself.
    app = _DummyEditor("Hello!")

    app._on_editor_key_release(_FakeKeyEvent("exclam", char="!"))

    assert app.open_completion_calls == [True]


def test_existing_trigger_characters_still_trigger_completion():
    app = _DummyEditor("foo_")

    app._on_editor_key_release(_FakeKeyEvent("underscore", char="_"))

    assert app.open_completion_calls == [True]


def test_non_trigger_character_closes_completion_instead():
    app = _DummyEditor("x")

    app._on_editor_key_release(_FakeKeyEvent("percent", char="%"))

    assert app.open_completion_calls == []
    assert app.close_completion_calls == 1
