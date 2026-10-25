"""Completion der Erwartungstypen nach `(Zahl P ` in Klausur-Lösungspunkten.

Fake-Editor nach dem Muster von `test_editor_completion_exact_match_suppression.py`,
ergänzt um einen mehrzeiligen Buffer (für `_editor_get_enclosing_block_type`)
und den Pfad des aktiven Tabs (für den Dokumenttyp). Nur synthetische Inhalte.
"""

from __future__ import annotations

from app.core.document_semantics import type_for_tab
from app.core.expectation_kinds import EXPECTATION_KINDS
from app.ui.blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin
from app.ui.blatt_ui_editor_completion_points import BlattwerkAppEditorCompletionPointsMixin


class _FakeEditorWidget:
    def __init__(self, text, cursor_line, cursor_col):
        self._lines = text.splitlines()
        self._cursor_line = cursor_line
        self._cursor_col = cursor_col

    def index(self, index):
        if index == "end-1c":
            return f"{len(self._lines)}.0"
        return f"{self._cursor_line}.{self._cursor_col}"

    def get(self, start, _end):
        line_no = int(start.split(".")[0])
        return self._lines[line_no - 1] if 0 < line_no <= len(self._lines) else ""


class _DummyEditor(BlattwerkAppEditorCompletionPointsMixin, BlattwerkAppEditorCompletionContextMixin):
    def __init__(self, text, *, path="klausur.kbw", marker="|"):
        lines = text.splitlines()
        line_index = next(index for index, line in enumerate(lines) if marker in line)
        col = lines[line_index].index(marker)
        lines[line_index] = lines[line_index].replace(marker, "", 1)
        self.editor_widget = _FakeEditorWidget("\n".join(lines), line_index + 1, col)
        self.user_preferences = {}
        self._path = path

    def _active_document_tab_state(self):
        return {"path": self._path} if self._path else None

    def _read_document_type(self, input_path):
        return type_for_tab(input_path, None)


def _context(text, **kwargs):
    return _DummyEditor(text, **kwargs)._collect_expectation_kind_completion_context(auto=True)


_SOLUTION = ":::task points=1\nAufgabe\n:::\n:::solution\n{line}\n:::\n"


def test_offers_all_kinds_after_points_and_space_inserting_full_name():
    context = _context(_SOLUTION.format(line="1. Ansatz notiert (1P |"))

    assert context is not None
    assert context["kind"] == "expectation_kind"
    assert [item["insert_text"] for item in context["suggestions"]] == [kind.label for kind in EXPECTATION_KINDS]
    assert context["suggestions"][0]["label"] == "💡 Ansatz (An)"
    assert context["replace_start"] == context["replace_end"]


def test_typed_prefix_filters_and_is_replaced():
    context = _context(_SOLUTION.format(line="1. Begründet (0,5aP Be|)"))

    assert [item["insert_text"] for item in context["suggestions"]] == ["Beobachtung", "Begründung"]
    assert context["replace_start"] == "5.20"
    assert context["replace_end"] == "5.22"


def test_abbreviation_is_expanded_to_full_name():
    context = _context(_SOLUTION.format(line="1. Begründet (1P Bg|"))

    assert [item["insert_text"] for item in context["suggestions"]] == ["Begründung"]


def test_detail_shows_legend_sentence():
    context = _context(_SOLUTION.format(line="1. Ansatz notiert (1P |"))

    for item, kind in zip(context["suggestions"], EXPECTATION_KINDS):
        assert item["detail"]["description"] == kind.description


def test_full_name_already_typed_opens_no_popup():
    assert _context(_SOLUTION.format(line="1. Ansatz notiert (1P Ansatz|")) is None


def test_only_in_exams():
    assert _context(_SOLUTION.format(line="1. Ansatz notiert (1P |"), path="blatt.abw") is None
    assert _context(_SOLUTION.format(line="1. Ansatz notiert (1P |"), path="") is None


def test_only_inside_solution_block():
    text = ":::task points=1\n1. Ansatz notiert (1P |\n:::\n"
    assert _context(text) is None


def test_only_on_solution_point_head_lines():
    indented = _SOLUTION.format(line="1. Ansatz\n    Folgezeile (1P |")
    assert _context(indented) is None


def test_no_popup_without_space_after_p():
    assert _context(_SOLUTION.format(line="1. Ansatz notiert (1P|")) is None


def test_manual_only_preference_blocks_auto_popup():
    editor = _DummyEditor(_SOLUTION.format(line="1. Ansatz notiert (1P |"))
    editor.user_preferences = {"completion_context_sources": "manual_only"}

    assert editor._collect_expectation_kind_completion_context(auto=True) is None
    assert editor._collect_expectation_kind_completion_context(auto=False) is not None
