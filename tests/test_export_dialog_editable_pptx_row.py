"""Tests for the "Editierbare Text-/Bildelemente"-checkbox row in
`PresentationExportDialog`: only visible for the PPTX format, stays
correctly positioned (not jumping to the bottom of the dialog) when the
format radio buttons are toggled back and forth, and disabled with a
hint when the experimental export isn't available.

Uses a real (withdrawn) Tk root -- `PresentationExportDialog.__init__`
itself calls `_show_window()` (`focus_force()`/`lift()` on a real,
non-withdrawn Toplevel), which was found to hang in this headless
environment during implementation; these tests bypass `__init__`
(`object.__new__` + manually setting the handful of attributes
`_build_ui()`/`_refresh_output_suggestion()` actually touch) and keep the
dialog's own `window` withdrawn throughout, exactly like the manual
verification run during implementation.

`winfo_manager()` (`"pack"` vs. `""`), not `winfo_ismapped()`, is the
correct visibility check here -- `winfo_ismapped()` depends on the whole
window hierarchy being mapped to the display, which a deliberately
withdrawn window never is, regardless of `pack()` state.
"""

import tkinter as tk

import pytest

from app.ui.export_dialog import PresentationExportDialog


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    root.withdraw()
    yield root
    root.destroy()


def _build_dialog(tk_root, *, editable_pptx_available: bool, monkeypatch):
    from bw_gui.runtime import ui

    monkeypatch.setattr(
        "app.ui.export_dialog.is_editable_pptx_available", lambda: editable_pptx_available
    )

    dialog = object.__new__(PresentationExportDialog)
    dialog.parent = tk_root
    dialog.input_path = __import__("pathlib").Path("test.md")
    dialog.theme_key = "light"
    dialog.initial_output_dir = None
    dialog.result = None
    dialog.shortcuts_visible = False
    dialog.output_var = ui.StringVar()
    dialog.window = ui.Toplevel(tk_root)
    dialog.window.withdraw()
    dialog.window.resizable(False, False)
    dialog.window.transient(tk_root)

    dialog.format_var = ui.StringVar(value="pdf")
    dialog.black_screen_var = ui.StringVar(value="none")
    dialog.ignore_framebreaks_var = ui.BooleanVar(value=False)
    dialog.editable_pptx_var = ui.BooleanVar(value=False)
    dialog._editable_pptx_available = editable_pptx_available

    dialog._build_ui()
    dialog.window.update_idletasks()
    return dialog


def test_row_hidden_by_default_for_pdf_format(tk_root, monkeypatch):
    dialog = _build_dialog(tk_root, editable_pptx_available=True, monkeypatch=monkeypatch)

    assert dialog.editable_pptx_row.winfo_manager() == ""

    dialog.window.destroy()


def test_row_visible_for_pptx_format(tk_root, monkeypatch):
    dialog = _build_dialog(tk_root, editable_pptx_available=True, monkeypatch=monkeypatch)

    dialog.format_var.set("pptx")
    dialog._refresh_output_suggestion()
    dialog.window.update_idletasks()

    assert dialog.editable_pptx_row.winfo_manager() == "pack"

    dialog.window.destroy()


def test_row_stays_visible_after_toggling_formats_back_and_forth(tk_root, monkeypatch):
    # Regression: pack_forget() followed by a bare pack() re-appends a
    # widget at the END of the current pack order instead of restoring
    # its original slot -- without the `before=` anchor, this row would
    # visibly jump below the output/action rows after the first toggle.
    dialog = _build_dialog(tk_root, editable_pptx_available=True, monkeypatch=monkeypatch)

    for fmt in ["pdf", "pptx", "html", "pdf", "pptx"]:
        dialog.format_var.set(fmt)
        dialog._refresh_output_suggestion()
        dialog.window.update_idletasks()

    assert dialog.editable_pptx_row.winfo_manager() == "pack"

    dialog.window.destroy()


def test_checkbutton_disabled_with_hint_when_export_unavailable(tk_root, monkeypatch):
    dialog = _build_dialog(tk_root, editable_pptx_available=False, monkeypatch=monkeypatch)

    assert str(dialog.editable_pptx_checkbutton["state"]) == "disabled"
    assert dialog.editable_pptx_hint_label.winfo_manager() == "pack"

    dialog.window.destroy()


def test_checkbutton_enabled_without_hint_when_export_available(tk_root, monkeypatch):
    dialog = _build_dialog(tk_root, editable_pptx_available=True, monkeypatch=monkeypatch)

    assert str(dialog.editable_pptx_checkbutton["state"]) == "normal"
    assert dialog.editable_pptx_hint_label.winfo_manager() == ""

    dialog.window.destroy()
