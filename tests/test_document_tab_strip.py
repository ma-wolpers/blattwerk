"""Dokument-Tab-Leiste: Schließen-Button bleibt sichtbar, Tab-Köpfe scrollen horizontal.

Echtes Tk (kein Fake): geprüft wird Geometrie -- Platzvergabe von ``pack``, Überlauf und
Scrollposition -- die sich gegen ein Test-Double nicht sinnvoll nachbilden lässt.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.theming import configure_ttk_theme

from app.ui.blatt_ui_persistence import BlattwerkAppPersistenceMixin
from app.ui.blatt_ui_tab_strip import BlattwerkAppTabStripMixin

ROOT_WIDTH_PX = 700


class _Harness(BlattwerkAppTabStripMixin):
    """Minimal host providing exactly what the mixin expects from the app."""

    def __init__(self, root: ui.Tk) -> None:
        self.root = root
        self.closed_calls = 0
        row = widgets.Frame(root, style="ControlStrip.TFrame")
        row.pack(fill="x")
        widgets.Label(row, text="Dokumente:", width=10).pack(side="left")
        self.row = row
        self._build_document_tab_strip(row)

    def close_active_document_tab(self) -> None:
        self.closed_calls += 1

    def _on_document_tab_changed(self, _event=None) -> None:
        return None

    def add_tabs(self, count: int) -> None:
        start = len(self.document_notebook.tabs())
        for index in range(start, start + count):
            self.document_notebook.add(widgets.Frame(self.document_notebook), text=f"datei-{index:02d}.md")
        self.root.update()

    def close_button(self):
        return next(child for child in self.row.pack_slaves() if child.pack_info()["side"] == "right")


@pytest.fixture(scope="module")
def _module_tk_root():
    """One real Tk interpreter for this module.

    Creating and destroying several ``Tk()`` interpreters in one process fails
    intermittently on this Windows setup ("invalid command name tcl_findLibrary"),
    a Tcl runtime race unrelated to the code under test (same finding as bw-gui's
    ``tests/conftest.py``). Tests get a clean slate via ``harness`` teardown.
    """
    try:
        root = ui.Tk()
    except ui.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    configure_ttk_theme(root, "charcoal")
    yield root
    root.destroy()


@pytest.fixture
def harness(_module_tk_root):
    root = _module_tk_root
    root.geometry(f"{ROOT_WIDTH_PX}x120+0+0")
    root.update()
    host = _Harness(root)
    root.update()
    yield host
    for child in root.winfo_children():
        child.destroy()


def _is_fully_inside_root(widget, root) -> bool:
    left = widget.winfo_rootx() - root.winfo_rootx()
    return widget.winfo_ismapped() and left >= 0 and left + widget.winfo_width() <= root.winfo_width()


def test_close_button_stays_visible_with_many_tabs(harness):
    harness.add_tabs(30)

    assert _is_fully_inside_root(harness.close_button(), harness.root)


def test_few_tabs_shrink_wrap_without_scrollbar(harness):
    harness.add_tabs(3)

    strip = harness.document_tab_strip
    assert strip.canvas.winfo_width() == harness.document_notebook.winfo_reqwidth()
    assert not strip._scrollbar.winfo_ismapped()


def test_many_tabs_overflow_into_a_scrollable_strip(harness):
    harness.add_tabs(30)

    strip = harness.document_tab_strip
    assert strip._scrollbar.winfo_ismapped()
    assert harness.document_notebook.winfo_reqwidth() > strip.canvas.winfo_width()


def test_tab_x_ranges_follow_tab_order_without_overlap(harness):
    harness.add_tabs(5)

    ranges = [harness._document_tab_x_range(index) for index in range(5)]

    assert all(span is not None for span in ranges)
    for (_left_a, right_a), (left_b, _right_b) in zip(ranges, ranges[1:]):
        assert right_a <= left_b + 2


def test_selecting_a_tab_outside_the_view_scrolls_it_into_view(harness):
    harness.add_tabs(30)
    strip = harness.document_tab_strip
    notebook = harness.document_notebook
    last_index = len(notebook.tabs()) - 1
    span = harness._document_tab_x_range(last_index)
    assert span is not None and span[1] > strip.canvas.winfo_width()

    notebook.select(notebook.tabs()[last_index])
    harness.root.update()
    harness._scroll_active_tab_into_view()
    harness.root.update()

    view_left = strip.canvas.canvasx(0)
    assert view_left + strip.canvas.winfo_width() >= notebook.winfo_x() + span[1]
    assert view_left <= notebook.winfo_x() + span[0]


def test_restore_window_geometry_leaves_maximized_state_before_applying_geometry():
    calls: list[tuple[str, str]] = []
    fake_root = SimpleNamespace(
        state=lambda value: calls.append(("state", value)),
        geometry=lambda value: calls.append(("geometry", value)),
    )
    fake_app = SimpleNamespace(root=fake_root, ui_settings={"window_geometry": " 900x600+10+20 "})

    BlattwerkAppPersistenceMixin._restore_window_geometry_if_enabled(fake_app, {"remember_window_geometry": True})

    assert calls == [("state", "normal"), ("geometry", "900x600+10+20")]


@pytest.mark.parametrize(
    ("preferences", "ui_settings"),
    [
        ({"remember_window_geometry": False}, {"window_geometry": "900x600+10+20"}),
        ({"remember_window_geometry": True}, {}),
    ],
)
def test_restore_window_geometry_keeps_maximized_default_when_nothing_to_restore(preferences, ui_settings):
    calls: list[str] = []
    fake_root = SimpleNamespace(state=lambda value: calls.append(value), geometry=lambda value: calls.append(value))
    fake_app = SimpleNamespace(root=fake_root, ui_settings=ui_settings)

    BlattwerkAppPersistenceMixin._restore_window_geometry_if_enabled(fake_app, preferences)

    assert calls == []
