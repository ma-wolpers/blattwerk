"""Einklappbare Editor-Panels (Diagnostik, Klausur-Übersicht, Struktur) mit echtem Tk.

Nutzt die echten Builder (`_build_editor_diagnostics_panel`,
`_build_exam_overview_panel`, `_build_editor_outline_panel`) und prüft die
tatsächliche Pack-Reihenfolge im Editor-Parent, nicht nur das Widget isoliert.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.blatt_ui_editor_diagnostics import BlattwerkAppEditorDiagnosticsMixin
from app.ui.blatt_ui_editor_panels import (
    EDITOR_PANELS_SETTINGS_KEY,
    PANEL_DIAGNOSTICS,
    PANEL_EXAM_OVERVIEW,
    PANEL_OUTLINE,
    BlattwerkEditorPanelsMixin,
    normalize_editor_panels_collapsed,
)
from app.ui.blatt_ui_exam_overview import BlattwerkExamOverviewMixin

EXAM_TEXT = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n:::task points=2 afb=1\nA\n:::\n"


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    root.geometry("+0+0")
    yield root
    root.destroy()


class _Harness(BlattwerkEditorPanelsMixin, BlattwerkExamOverviewMixin, BlattwerkAppEditorDiagnosticsMixin):
    def __init__(self, root, settings=None, outline_visible=True):
        self.ui_settings = {} if settings is None else settings
        self.saved = []
        self.parent = tk.Frame(root)
        self.parent.pack()
        self._build_editor_diagnostics_panel(self.parent)
        self._build_exam_overview_panel(self.parent)
        self._build_editor_outline_panel(self.parent, {"outline_visible_on_start": outline_visible})
        root.update()

    def _save_ui_settings(self):
        self.saved.append(dict(self.ui_settings.get(EDITOR_PANELS_SETTINGS_KEY, {})))

    def _on_editor_diagnostic_selected(self, _event=None):
        pass

    _on_editor_diagnostic_click = _on_editor_diagnostics_ack_column_click = _on_editor_diagnostic_selected
    _on_editor_diagnostics_context_menu = _on_editor_outline_selected = _on_editor_outline_click = _on_editor_diagnostic_selected

    def order(self):
        names = {id(self._editor_section(key)): key for key in (PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW, PANEL_OUTLINE)}
        return [names[id(widget)] for widget in self.parent.pack_slaves() if id(widget) in names]


@pytest.fixture
def make(tk_root):
    created = []

    def factory(**kwargs):
        harness = _Harness(tk_root, **kwargs)
        created.append(harness)
        return harness

    yield factory
    for harness in created:
        harness.parent.destroy()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, {"diagnostics": False, "exam_overview": False, "outline": False}),
        ("kaputt", {"diagnostics": False, "exam_overview": False, "outline": False}),
        ({"outline": True}, {"diagnostics": False, "exam_overview": False, "outline": True}),
        ({"diagnostics": "ja", "outline": 1, "fremd": True}, {"diagnostics": False, "exam_overview": False, "outline": False}),
        ({"diagnostics": True, "exam_overview": True, "outline": True}, {"diagnostics": True, "exam_overview": True, "outline": True}),
    ],
)
def test_normalize_settings_is_robust_and_canonical(raw, expected):
    assert normalize_editor_panels_collapsed(raw) == expected


def test_worksheet_order_without_overview(make):
    harness = make()
    harness._refresh_exam_overview("x", "worksheet")
    assert harness.order() == [PANEL_DIAGNOSTICS, PANEL_OUTLINE]


def test_type_switches_keep_overview_between_diagnostics_and_outline(make, tk_root):
    harness = make()
    for document_type in ("exam", "worksheet", "exam", "worksheet", "exam"):
        harness._refresh_exam_overview(EXAM_TEXT, document_type)
        tk_root.update()
        expected = [PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW, PANEL_OUTLINE] if document_type == "exam" else [PANEL_DIAGNOSTICS, PANEL_OUTLINE]
        assert harness.order() == expected


def test_outline_hidden_on_start_still_orders_overview_after_diagnostics(make):
    harness = make(outline_visible=False)
    harness._refresh_exam_overview(EXAM_TEXT, "exam")
    assert harness.order() == [PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW]
    assert not harness._editor_section(PANEL_OUTLINE).winfo_manager()


def test_saved_state_is_applied_and_survives_hide_and_show(make):
    settings = {EDITOR_PANELS_SETTINGS_KEY: {"diagnostics": True, "exam_overview": True, "outline": False}}
    harness = make(settings=settings)
    overview = harness._editor_section(PANEL_EXAM_OVERVIEW)
    assert harness._editor_section(PANEL_DIAGNOSTICS).collapsed and overview.collapsed
    assert not harness._editor_section(PANEL_OUTLINE).collapsed
    for document_type in ("exam", "worksheet", "exam"):
        harness._refresh_exam_overview(EXAM_TEXT, document_type)
    assert overview.collapsed and harness.saved == []


def test_user_toggle_saves_canonical_state(make):
    harness = make(settings={EDITOR_PANELS_SETTINGS_KEY: {"outline": "kaputt", "fremd": 1}})
    harness._editor_section(PANEL_OUTLINE).toggle()
    assert harness.saved == [{"diagnostics": False, "exam_overview": False, "outline": True}]
    harness._editor_section(PANEL_DIAGNOSTICS).toggle()
    assert harness.saved[-1] == {"diagnostics": True, "exam_overview": False, "outline": True}


def test_collapsed_panels_keep_their_position(make, tk_root):
    harness = make(settings={EDITOR_PANELS_SETTINGS_KEY: {"diagnostics": True, "outline": True}})
    harness._refresh_exam_overview(EXAM_TEXT, "exam")
    harness._editor_section(PANEL_EXAM_OVERVIEW).toggle()
    tk_root.update()
    assert harness.order() == [PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW, PANEL_OUTLINE]
    assert all(harness._editor_section(key).collapsed for key in (PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW, PANEL_OUTLINE))


def test_collapsed_real_panels_only_take_their_title_row(make, tk_root):
    """Regression (Screenshot 2026-10-05): eingeklappt darf ein Panel nicht seine volle Höhe behalten."""
    harness = make()
    harness._refresh_exam_overview(EXAM_TEXT, "exam")
    tk_root.update()
    for key in (PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW, PANEL_OUTLINE):
        section = harness._editor_section(key)
        expanded = section.winfo_height()
        section.toggle()
        tk_root.update()
        title_row = section._header.winfo_reqheight()
        assert section.winfo_height() <= title_row + 12 < expanded, key
        section.toggle()
        tk_root.update()
        assert section.winfo_height() == expanded, key
