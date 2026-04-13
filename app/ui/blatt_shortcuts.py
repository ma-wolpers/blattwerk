"""Shortcut-Definitionen für die Blattwerk-Hauptansicht."""

from __future__ import annotations

from .shortcut_manager import ShortcutBinding
from .ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
    VIEW_FIT_PAGE,
    VIEW_FIT_WIDTH,
    VIEW_LAYOUT_SINGLE,
    VIEW_LAYOUT_STACK,
    VIEW_LAYOUT_STRIP,
)


def build_preview_shortcuts(app):
    """Liefert alle Hauptfenster-Shortcuts als zentrale Liste."""

    return [
        ShortcutBinding("<Left>", app.prev_page, "← / →   Seite wechseln"),
        ShortcutBinding("<Right>", app.next_page),
        ShortcutBinding(
            "<Up>", lambda: app._scroll_preview_vertical(-4), "↑ / ↓   Scrollen"
        ),
        ShortcutBinding("<Down>", lambda: app._scroll_preview_vertical(4)),
        ShortcutBinding("<KeyPress-s>", app._toggle_contrast, "S   Kontrast wechseln"),
        ShortcutBinding(
            "<KeyPress-f>",
            lambda: app._cycle_design_color_profile(step=1),
            "F   Farbprofil wechseln",
        ),
        ShortcutBinding(
            "<KeyPress-4>",
            lambda: app._set_page_format("a4_portrait"),
            "4 / 5   Seitenformat A4 / A5",
        ),
        ShortcutBinding("<KeyPress-5>", lambda: app._set_page_format("a5_landscape")),
        ShortcutBinding(
            "<KeyPress-0>",
            lambda: app.set_view_fit_mode(VIEW_FIT_WIDTH),
            "0 / 1   Seitenbreite / ganze Seite",
        ),
        ShortcutBinding("<KeyPress-1>", lambda: app.set_view_fit_mode(VIEW_FIT_PAGE)),
        ShortcutBinding(
            "<KeyPress-e>",
            lambda: app.set_preview_layout_mode(VIEW_LAYOUT_SINGLE),
            "E / N / U   Einzel / neben / untereinander",
        ),
        ShortcutBinding(
            "<KeyPress-n>", lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STRIP)
        ),
        ShortcutBinding(
            "<KeyPress-u>", lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STACK)
        ),
        ShortcutBinding(
            "<KeyPress-minus>", lambda: app.change_zoom(-10), "- / +   Zoom raus / rein"
        ),
        ShortcutBinding("<KeyPress-plus>", lambda: app.change_zoom(10)),
        ShortcutBinding("<KP_Subtract>", lambda: app.change_zoom(-10)),
        ShortcutBinding("<KP_Add>", lambda: app.change_zoom(10)),
        ShortcutBinding("<Tab>", app._toggle_preview_mode, "Tab   Aufgabe / Lösung"),
        ShortcutBinding(
            "<space>", app.refresh_preview, "Leertaste   Vorschau aktualisieren"
        ),
        ShortcutBinding("<Return>", app.open_export_dialog, "Enter   Exportieren"),
        ShortcutBinding("<KP_Enter>", app.open_export_dialog),
        ShortcutBinding("<KeyPress-o>", app.pick_input, "O   Markdown öffnen"),
        ShortcutBinding(
            "<Control-n>",
            app.create_new_markdown_file,
            "Strg+N   neue Markdown-Datei",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-o>",
            app.pick_input,
            "Strg+O   Markdown öffnen",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-Shift-s>",
            app.save_markdown_file_as,
            "Strg+Shift+S   Speichern unter",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-comma>",
            app._open_local_settings_dialog,
            "Strg+,   Einstellungen",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-Key-1>",
            lambda: app._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY),
            "Strg+1/2/3   Vorschau / beides / Editor",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-Key-2>",
            lambda: app._set_editor_view_mode(EDITOR_VIEW_BOTH),
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-Key-3>",
            lambda: app._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY),
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-t>",
            app._cycle_theme,
            "Strg+T   Theme wechseln",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<Control-f>",
            app._cycle_font_profile,
            "Strg+F   Schriftprofil wechseln",
            ignore_when_text_input=False,
            allow_modifiers=True,
        ),
        ShortcutBinding(
            "<KeyPress-z>", app._open_last_markdown, "Z   zuletzt geladenes Markdown"
        ),
        ShortcutBinding("<Escape>", app.root.destroy, "Esc   Beenden"),
    ]
