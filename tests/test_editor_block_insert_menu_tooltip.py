"""Tests for the Ctrl+B block-insert menu's block-explanation tooltip.

Two layers: `_derive_block_type_from_snippet` is pure (no Tk needed) and
covers every real `_EDITOR_BLOCK_MENU_ITEMS` entry; the tooltip
show/hide mechanics (`_on_block_insert_menu_select`/
`_hide_block_insert_menu_tooltip`) need a real (headless) Tk root since
they construct actual `tk.Menu`/`Toplevel`/`Label` widgets -- no fake
stand-in captures that construction the way the completion-popup tests do.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.blatt_ui_editor import (
    _EDITOR_BLOCK_MENU_ITEMS,
    BlattwerkAppEditorMixin,
    _derive_block_type_from_snippet,
)


def test_derive_block_type_from_snippet_returns_type_for_regular_block():
    assert _derive_block_type_from_snippet(":::info type=note\nHinweis hier…\n:::\n") == "info"


def test_derive_block_type_from_snippet_returns_none_for_non_block_snippet():
    assert _derive_block_type_from_snippet('![Bildbeschreibung](bild.png "w=80%")\n') is None


def test_every_real_menu_item_derives_a_block_type_except_image():
    for _letter, label, snippet in _EDITOR_BLOCK_MENU_ITEMS:
        block_type = _derive_block_type_from_snippet(snippet)
        if label == "Bild (image)":
            assert block_type is None
        else:
            assert block_type is not None, f"{label!r} snippet should derive a block type"


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    root.withdraw()
    yield root
    root.destroy()


class _DummyMenuEditor(BlattwerkAppEditorMixin):
    def __init__(self, root):
        self.root = root
        self.editor_widget = None
        self._block_insert_menu_tooltip = None


def _menu_with_items(root, labels):
    menu = tk.Menu(root, tearoff=0)
    for label in labels:
        menu.add_command(label=label, command=lambda: None)
    return menu


def test_menu_select_shows_tooltip_for_entry_with_known_detail(tk_root):
    editor = _DummyMenuEditor(tk_root)
    menu = _menu_with_items(tk_root, ["F   Infobox / Hinweis (info)"])
    menu.activate(0)

    editor._on_block_insert_menu_select(menu, ["info"])

    assert editor._block_insert_menu_tooltip is not None
    assert editor._block_insert_menu_tooltip.winfo_exists()


def test_menu_select_hides_tooltip_for_non_block_entry(tk_root):
    editor = _DummyMenuEditor(tk_root)
    menu = _menu_with_items(tk_root, ["I   Bild (image)"])
    menu.activate(0)

    editor._on_block_insert_menu_select(menu, [None])

    assert editor._block_insert_menu_tooltip is None


def test_menu_select_hides_tooltip_for_unknown_block_type(tk_root):
    editor = _DummyMenuEditor(tk_root)
    menu = _menu_with_items(tk_root, ["Z   Does Not Exist"])
    menu.activate(0)

    editor._on_block_insert_menu_select(menu, ["does-not-exist"])

    assert editor._block_insert_menu_tooltip is None


def test_menu_select_replaces_previous_tooltip_not_stacks_it(tk_root):
    editor = _DummyMenuEditor(tk_root)
    menu = _menu_with_items(tk_root, ["F   Infobox (info)", "T   Aufgabe (task)"])

    menu.activate(0)
    editor._on_block_insert_menu_select(menu, ["info", "task"])
    first_tooltip = editor._block_insert_menu_tooltip
    assert first_tooltip is not None

    menu.activate(1)
    editor._on_block_insert_menu_select(menu, ["info", "task"])
    second_tooltip = editor._block_insert_menu_tooltip

    assert second_tooltip is not None
    assert second_tooltip is not first_tooltip
    assert not first_tooltip.winfo_exists()  # destroyed, not leaked


def test_hide_block_insert_menu_tooltip_is_a_no_op_when_nothing_shown(tk_root):
    editor = _DummyMenuEditor(tk_root)

    editor._hide_block_insert_menu_tooltip()  # must not raise

    assert editor._block_insert_menu_tooltip is None


def test_hide_block_insert_menu_tooltip_destroys_and_clears_reference(tk_root):
    editor = _DummyMenuEditor(tk_root)
    menu = _menu_with_items(tk_root, ["F   Infobox (info)"])
    menu.activate(0)
    editor._on_block_insert_menu_select(menu, ["info"])
    tooltip = editor._block_insert_menu_tooltip
    assert tooltip is not None

    editor._hide_block_insert_menu_tooltip()

    assert editor._block_insert_menu_tooltip is None
    assert not tooltip.winfo_exists()
