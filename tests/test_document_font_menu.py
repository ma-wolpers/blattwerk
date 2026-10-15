"""Schriftmenue schreibt `font_profile` ins Dokument (Wunschliste Schritt 5a).

Mit einem echten (unsichtbaren) Tk-Textfeld: Menuewahl setzt den Eintrag,
"Standard" entfernt ihn, beides ist genau ein Undo-Schritt, Strg+Shift+F zyklisch,
das Menue zeigt den Dokumentwert, und ohne Dokument passiert nichts.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.blatt_ui_document_font import APP_DEFAULT_FONT_CHOICE, BlattwerkAppDocumentFontMixin
from app.ui.ui_constants import EDITOR_DOCUMENT_LOADED, EDITOR_DOCUMENT_NOT_LOADED

DOC = "---\nTitel: T\nFach: M\nThema: X\n---\n:::task\nA\n:::\n"


@pytest.fixture(scope="module")
def tk_root():
    """Ein unsichtbares Tk-Fenster fuer das ganze Modul (wiederholtes `tk.Tk()` ist unter
    Windows gelegentlich instabil)."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no Tk display available: {error}")
    root.withdraw()
    yield root
    root.destroy()


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Button:
    def __init__(self):
        self.text = ""

    def configure(self, text):
        self.text = text


class _Host(BlattwerkAppDocumentFontMixin):
    def __init__(self, root, text, loaded=True):
        self.editor_widget = tk.Text(root, undo=True)
        self.editor_widget.insert("1.0", text)
        self.editor_widget.edit_reset()
        self._editor_document_state = EDITOR_DOCUMENT_LOADED if loaded else EDITOR_DOCUMENT_NOT_LOADED
        self.design_font_profile_var = _Var("calibri")
        self._font_profile_menu_var = _Var()
        self.font_profile_menubutton = _Button()
        self.status_var = _Var()
        self.saves = 0
        self.refreshes = 0

    def _save_editor_content(self):
        self.saves += 1

    def refresh_preview(self, force_rebuild=False):
        self.refreshes += 1

    def text(self):
        return self.editor_widget.get("1.0", "end-1c")


def test_menu_choice_writes_font_profile_and_saves(tk_root):
    """Die Wahl landet im Frontmatter, wird gespeichert, die Vorschau aktualisiert."""
    host = _Host(tk_root, DOC)
    host._set_font_profile("comic_neue")
    assert "font_profile: comic_neue" in host.text()
    assert host.text().endswith(":::task\nA\n:::\n")
    assert (host.saves, host.refreshes) == (1, 1)
    assert host._font_profile_menu_var.get() == "comic_neue"
    assert host.font_profile_menubutton.text.startswith("Comic Neue")


def test_standard_removes_the_key(tk_root):
    """"Standard (App-Einstellung)" entfernt den Eintrag; das Menue zeigt den App-Standard."""
    host = _Host(tk_root, DOC.replace("Thema: X\n", "Thema: X\nfont_profile: arial\n"))
    host._set_font_profile(APP_DEFAULT_FONT_CHOICE)
    assert "font_profile" not in host.text()
    assert host._font_profile_menu_var.get() == APP_DEFAULT_FONT_CHOICE
    assert host.font_profile_menubutton.text == "Standard (Calibri)"


def test_change_is_exactly_one_undo_step(tk_root):
    """Ein Undo stellt den Text vor der Menuewahl vollstaendig wieder her."""
    host = _Host(tk_root, DOC)
    host.editor_widget.insert("end", "\nnoch getippt")
    before = host.text()
    host._set_font_profile("andika")
    host.editor_widget.edit_undo()
    assert host.text() == before


def test_cycle_goes_through_standard_and_all_profiles(tk_root):
    """Strg+Shift+F: Standard -> erstes Profil -> ... -> Standard."""
    host = _Host(tk_root, DOC)
    host._cycle_font_profile()
    first = host._current_document_font_choice()
    assert first != APP_DEFAULT_FONT_CHOICE
    host._cycle_font_profile(step=-1)
    assert host._current_document_font_choice() == APP_DEFAULT_FONT_CHOICE


def test_invalid_document_value_shows_as_standard(tk_root):
    """Ein ungueltiger Wert (Warnung FM012) wird im Menue als Standard angezeigt."""
    host = _Host(tk_root, DOC.replace("Thema: X\n", "Thema: X\nfont_profile: papyrus\n"))
    host._sync_font_profile_combo()
    assert host._font_profile_menu_var.get() == APP_DEFAULT_FONT_CHOICE


def test_without_loaded_document_nothing_changes(tk_root):
    """Ohne geladenes Dokument wird nichts geschrieben oder gespeichert."""
    host = _Host(tk_root, DOC, loaded=False)
    host._set_font_profile("comic_neue")
    assert "font_profile" not in host.text()
    assert host.saves == 0


def test_document_without_frontmatter_gets_one(tk_root):
    """Ein Dokument ohne Frontmatter bekommt eines mit dem Eintrag."""
    host = _Host(tk_root, ":::task\nA\n:::\n")
    host._set_font_profile("fredoka")
    assert host.text().startswith("---\nfont_profile: fredoka\n---")
