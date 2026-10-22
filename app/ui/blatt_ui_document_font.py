"""Schriftmenue der Vorschau: Auswahl wird als `font_profile` ins Dokument geschrieben.

Das Dokument ist die Quelle der Schrift (`app/core/document_font.py`): Die Wahl im
Menue (und Strg+Shift+F) setzt `font_profile` im Frontmatter des aktiven Dokuments,
"Standard (App-Einstellung)" entfernt den Eintrag. Das Menue zeigt immer den Wert des
Dokuments an, damit Vorschau und Export dasselbe zeigen. Ohne Eintrag gilt der
App-Standard aus den Einstellungen (`default_font_profile`).
"""

from __future__ import annotations

from ..core.blatt_kern_shared import split_front_matter
from ..core.document_font import FONT_PROFILE_KEY, document_font_profile_value
from ..core.frontmatter_edit import EditUnsafe, FrontmatterEditor
from ..styles.blatt_styles import DEFAULT_FONT_PROFILE, FONT_PROFILE_LABELS, FONT_PROFILE_ORDER, normalize_font_profile
from .ui_constants import EDITOR_DOCUMENT_LOADED

APP_DEFAULT_FONT_CHOICE = "__app_default__"
"""Menuewert fuer "kein `font_profile` im Dokument" (App-Einstellung gilt)."""


class BlattwerkAppDocumentFontMixin:
    """Verbindet das Schriftmenue mit dem `font_profile` des aktiven Dokuments."""

    def _document_text_for_font(self) -> str | None:
        """Editortext des geladenen Dokuments oder ``None`` (kein Dokument geladen)."""
        editor = getattr(self, "editor_widget", None)
        if editor is None or getattr(self, "_editor_document_state", None) != EDITOR_DOCUMENT_LOADED:
            return None
        return editor.get("1.0", "end-1c")

    def _current_document_font_choice(self) -> str:
        """Menuewert fuer das aktive Dokument: sein `font_profile` oder `APP_DEFAULT_FONT_CHOICE`.

        Ein ungueltiger Wert im Dokument wird hier wie "kein Wert" angezeigt; der
        Validator meldet ihn als Warnung FM012.
        """
        text = self._document_text_for_font()
        if text is None:
            return APP_DEFAULT_FONT_CHOICE
        meta, _ = split_front_matter(text)
        value = document_font_profile_value(meta)
        return value if value in FONT_PROFILE_ORDER else APP_DEFAULT_FONT_CHOICE

    def _app_default_font_profile(self) -> str:
        """Schriftprofil, das ohne Dokumentwert gerendert wird.

        Das ist die Vorschau-Gestaltung (`design_font_profile_var`), die aus der
        Einstellung `default_font_profile` gesetzt wird -- derselbe Wert, den die
        Vorschau als App-Standard an den Renderer gibt.
        """
        variable = getattr(self, "design_font_profile_var", None)
        return normalize_font_profile(variable.get() if variable is not None else DEFAULT_FONT_PROFILE)

    def _set_font_profile(self, choice: str):
        """Schreibt die Menuewahl als `font_profile` ins Dokument (oder entfernt den Eintrag).

        Die Aenderung ist ein einziger Undo-Schritt im Editor; danach wird gespeichert
        und die Vorschau aktualisiert. Ohne geladenes Dokument passiert nichts.
        Laesst sich das Frontmatter nicht sicher bearbeiten (`EditUnsafe`), bleibt
        der Text unveraendert und die Statuszeile sagt warum.
        """
        text = self._document_text_for_font()
        if text is None or choice == self._current_document_font_choice():
            self._sync_font_profile_combo()
            return
        editor = FrontmatterEditor(text)
        try:
            if choice == APP_DEFAULT_FONT_CHOICE:
                editor.remove_key(FONT_PROFILE_KEY)
            else:
                editor.ensure_frontmatter()
                editor.set_scalar(FONT_PROFILE_KEY, normalize_font_profile(choice))
            new_text = editor.result()
        except EditUnsafe as error:
            self.status_var.set(f"Schrift nicht geändert: Frontmatter nicht sicher bearbeitbar ({error}).")
            self._sync_font_profile_combo()
            return
        self._replace_editor_text_as_one_undo_step(new_text)
        self._save_editor_content()
        self._sync_font_profile_combo()
        self.refresh_preview()

    def _cycle_font_profile(self, step: int = 1):
        """Strg+Shift+F: naechste Schrift (inkl. "Standard") fuer das aktive Dokument."""
        choices = [APP_DEFAULT_FONT_CHOICE, *FONT_PROFILE_ORDER]
        current = self._current_document_font_choice()
        index = choices.index(current) if current in choices else 0
        self._set_font_profile(choices[(index + step) % len(choices)])

    def _sync_font_profile_combo(self):
        """Zeigt den Schriftwert des Dokuments im Menueknopf und an den Menue-Radios."""
        if not hasattr(self, "font_profile_menubutton"):
            return
        choice = self._current_document_font_choice()
        self._font_profile_menu_var.set(choice)
        if choice == APP_DEFAULT_FONT_CHOICE:
            app_label = FONT_PROFILE_LABELS.get(self._app_default_font_profile(), "")
            text = f"Standard ({app_label})"
        else:
            text = FONT_PROFILE_LABELS.get(choice, choice)
        self.font_profile_menubutton.configure(text=text)

    def _replace_editor_text_as_one_undo_step(self, new_text: str) -> None:
        """Ersetzt den Editorinhalt als genau einen Undo-Schritt und behaelt die Scrollposition."""
        editor = self.editor_widget
        scroll_fraction = editor.yview()[0]
        previous = editor.cget("autoseparators")
        editor.configure(autoseparators=False)
        try:
            editor.edit_separator()
            editor.delete("1.0", "end")
            editor.insert("1.0", new_text)
            editor.edit_separator()
        finally:
            editor.configure(autoseparators=previous)
        editor.yview_moveto(scroll_fraction)
