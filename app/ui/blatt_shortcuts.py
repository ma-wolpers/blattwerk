"""Shortcut-Definitionen für die Blattwerk-Hauptansicht.

Tasten sind ``KeySpec``s in kanonischer Notation (bw-gui-Keyboard-Contract).
Migrationsregeln gegenüber den früheren Tk-Sequenzen am ``ShortcutManager``:

* **Exakte Modifier:** Strg-Kürzel feuern nur noch genau mit Strg (früher über
  ``allow_modifiers=True`` und Tks Mindestmengen-Semantik auch mit Strg+Alt).
  Einbuchstaben-Kürzel blockierten schon immer bei Strg/Alt.
* **Shift:** blockierte früher nie. Benannte Tasten (Pfeile, Tab, Leertaste, Esc)
  tolerieren Shift deshalb ausdrücklich; Buchstaben folgen Shift (``s`` ≠ ``S``),
  wie bei den früheren Keysym-Bindungen, aber nie mehr CapsLock.
* **Strg+Shift+Buchstabe:** Die früheren ``<Control-Shift-h>``-Bindungen (Klein-
  buchstabe) feuerten nur mit eingeschalteter Feststelltaste; jetzt ``Ctrl+Shift+H``.
* **Ziffernblock:** ``KP_Add``/``KP_Subtract`` sind die Zeichen ``+``/``-`` (eine
  Definition je Aktion); Ziffern gelten auch auf dem Ziffernblock.
"""

from __future__ import annotations

from typing import Iterable

from bw_gui.contracts.key_spec import KeySpec
from bw_gui.contracts.keybinding import (
    UI_MODE_DIALOG,
    UI_MODE_GLOBAL,
    UI_MODE_PREVIEW,
    KeyBindingDefinition,
    KeybindingRegistry,
)
from .ui_intents import UiIntent
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


_k = KeySpec.parse


def build_preview_keybinding_registry(app) -> KeybindingRegistry:
    """Build central mode-aware shortcut registry for the main preview UI."""
    registry = KeybindingRegistry()
    registry.register_many(
        [
            KeyBindingDefinition("preview.prev_page", _k("Left (tolerate: Shift)"), UiIntent.PREVIEW_PREV_PAGE, (UI_MODE_PREVIEW,), "← / →   Seite wechseln", handler=app.prev_page),
            KeyBindingDefinition("preview.next_page", _k("Right (tolerate: Shift)"), UiIntent.PREVIEW_NEXT_PAGE, (UI_MODE_PREVIEW,), handler=app.next_page),
            KeyBindingDefinition("preview.scroll_up", _k("Up (tolerate: Shift)"), UiIntent.PREVIEW_SCROLL_UP, (UI_MODE_PREVIEW,), "↑ / ↓   Scrollen", handler=lambda: app._scroll_preview_vertical(-4)),
            KeyBindingDefinition("preview.scroll_down", _k("Down (tolerate: Shift)"), UiIntent.PREVIEW_SCROLL_DOWN, (UI_MODE_PREVIEW,), handler=lambda: app._scroll_preview_vertical(4)),
            KeyBindingDefinition("preview.toggle_contrast", _k("S"), UiIntent.PREVIEW_TOGGLE_CONTRAST, (UI_MODE_PREVIEW,), "S   Kontrast wechseln", handler=app._toggle_contrast),
            KeyBindingDefinition("preview.cycle_design", _k("F"), UiIntent.PREVIEW_CYCLE_DESIGN, (UI_MODE_PREVIEW,), "F   Farbprofil wechseln", handler=lambda: app._cycle_design_color_profile(step=1)),
            KeyBindingDefinition("preview.black_both", _k("K"), UiIntent.PREVIEW_BLACK_BOTH, (UI_MODE_PREVIEW,), "K   Black-Screen beides", handler=app._set_preview_black_screen_both),
            KeyBindingDefinition("preview.page_a4", _k("4"), UiIntent.PREVIEW_PAGE_A4, (UI_MODE_PREVIEW,), "4 / Q / 5   Seitenformat A4 / A4 quer / A5", handler=lambda: app._set_page_format("a4_portrait")),
            KeyBindingDefinition("preview.page_a4_landscape", _k("Q"), UiIntent.PREVIEW_PAGE_A4_LANDSCAPE, (UI_MODE_PREVIEW,), handler=lambda: app._set_page_format("a4_landscape")),
            KeyBindingDefinition("preview.page_a5", _k("5"), UiIntent.PREVIEW_PAGE_A5, (UI_MODE_PREVIEW,), handler=lambda: app._set_page_format("a5_landscape")),
            KeyBindingDefinition("preview.fit_width", _k("0"), UiIntent.PREVIEW_FIT_WIDTH, (UI_MODE_PREVIEW,), "0 / 1   Seitenbreite / ganze Seite", handler=lambda: app.set_view_fit_mode(VIEW_FIT_WIDTH)),
            KeyBindingDefinition("preview.fit_page", _k("1"), UiIntent.PREVIEW_FIT_PAGE, (UI_MODE_PREVIEW,), handler=lambda: app.set_view_fit_mode(VIEW_FIT_PAGE)),
            KeyBindingDefinition("preview.layout_single", _k("E"), UiIntent.PREVIEW_LAYOUT_SINGLE, (UI_MODE_PREVIEW,), "E / N / U   Einzel / neben / untereinander", handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_SINGLE)),
            KeyBindingDefinition("preview.layout_strip", _k("N"), UiIntent.PREVIEW_LAYOUT_STRIP, (UI_MODE_PREVIEW,), handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STRIP)),
            KeyBindingDefinition("preview.layout_stack", _k("U"), UiIntent.PREVIEW_LAYOUT_STACK, (UI_MODE_PREVIEW,), handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STACK)),
            KeyBindingDefinition("preview.zoom_out", _k("-"), UiIntent.PREVIEW_ZOOM_OUT, (UI_MODE_PREVIEW,), "- / +   Zoom raus / rein", handler=lambda: app.change_zoom(-10)),
            KeyBindingDefinition("preview.zoom_in", _k("+"), UiIntent.PREVIEW_ZOOM_IN, (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(10)),
            KeyBindingDefinition("preview.toggle_mode", _k("Tab (tolerate: Shift)"), UiIntent.PREVIEW_TOGGLE_MODE, (UI_MODE_PREVIEW,), "Tab   Aufgabe / Lösung", handler=app._toggle_preview_mode),
            KeyBindingDefinition("preview.refresh", _k("Space (tolerate: Shift)"), UiIntent.PREVIEW_REFRESH, (UI_MODE_PREVIEW,), "Leertaste   Vorschau aktualisieren", handler=app._compile_now),
            KeyBindingDefinition("global.export", _k("Ctrl+E"), UiIntent.GLOBAL_EXPORT, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+E   Exportieren", allow_when_text_input=True, handler=app.open_export_dialog),
            KeyBindingDefinition("global.help_preview", _k("Ctrl+Shift+H"), UiIntent.GLOBAL_HELP_PREVIEW, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+H   Lernhilfenansicht", allow_when_text_input=True, handler=app.open_help_preview_window),
            KeyBindingDefinition("global.open_file", _k("O"), UiIntent.GLOBAL_OPEN_FILE, (UI_MODE_GLOBAL,), "O   Markdown öffnen", handler=app.pick_input),
            KeyBindingDefinition("global.new_file", _k("Ctrl+N"), UiIntent.GLOBAL_NEW_FILE, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+N   neues Dokument", allow_when_text_input=True, handler=app.create_new_markdown_file),
            KeyBindingDefinition("global.open_file_ctrl", _k("Ctrl+O"), UiIntent.GLOBAL_OPEN_FILE_CTRL, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+O   Markdown öffnen", allow_when_text_input=True, handler=app.pick_input),
            KeyBindingDefinition("global.save_as", _k("Ctrl+Shift+S"), UiIntent.GLOBAL_SAVE_AS, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+S   Speichern unter", allow_when_text_input=True, handler=app.save_markdown_file_as),
            KeyBindingDefinition("global.settings", _k("Ctrl+,"), UiIntent.GLOBAL_SETTINGS, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+,   Einstellungen", allow_when_text_input=True, handler=app._open_local_settings_dialog),
            KeyBindingDefinition("global.view_preview", _k("Ctrl+1"), UiIntent.GLOBAL_VIEW_PREVIEW, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+1/2/3   Vorschau / beides / Editor", allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY)),
            KeyBindingDefinition("global.view_both", _k("Ctrl+2"), UiIntent.GLOBAL_VIEW_BOTH, (UI_MODE_GLOBAL, UI_MODE_DIALOG), allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_BOTH)),
            KeyBindingDefinition("global.view_editor", _k("Ctrl+3"), UiIntent.GLOBAL_VIEW_EDITOR, (UI_MODE_GLOBAL, UI_MODE_DIALOG), allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY)),
            KeyBindingDefinition("global.cycle_theme", _k("Ctrl+T"), UiIntent.GLOBAL_CYCLE_THEME, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+T   Theme wechseln", allow_when_text_input=True, handler=app._cycle_theme),
            KeyBindingDefinition("global.cycle_font", _k("Ctrl+Shift+F"), UiIntent.GLOBAL_CYCLE_FONT, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+F   Schriftprofil wechseln", allow_when_text_input=True, handler=app._cycle_font_profile),
            KeyBindingDefinition("global.open_recent", _k("Z"), UiIntent.GLOBAL_OPEN_RECENT, (UI_MODE_GLOBAL,), "Z   zuletzt geladenes Markdown", handler=app._open_last_markdown),
            KeyBindingDefinition("global.debug_overlay", _k("Ctrl+Shift+D"), UiIntent.GLOBAL_DEBUG_OVERLAY, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+D   Shortcut-Debug-Overlay", allow_when_text_input=True, handler=app._toggle_shortcut_debug_overlay),
            KeyBindingDefinition("global.debug_offline", _k("Ctrl+Shift+O"), UiIntent.GLOBAL_DEBUG_OFFLINE, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+O   Offline simulieren", allow_when_text_input=True, handler=app._toggle_shortcut_debug_offline),
            KeyBindingDefinition("global.escape", _k("Escape (tolerate: Shift)"), UiIntent.GLOBAL_ESCAPE, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Esc   Zurueck", handler=app._handle_global_escape),
        ]
    )
    return registry


def iter_menu_labels(definitions: Iterable[KeyBindingDefinition]):
    """Liefert die Menü-Hinweistexte der Definitionen dedupliziert in Tabellenreihenfolge."""
    seen: set[str] = set()
    for definition in definitions:
        label = definition.description
        if not label or label in seen:
            continue
        seen.add(label)
        yield label


def get_preview_shortcut_mode_manifest(app) -> dict[str, list[str]]:
    """Return mode to binding-id mapping for debug/help output."""
    return build_preview_keybinding_registry(app).mode_manifest()
