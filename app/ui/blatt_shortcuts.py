"""Shortcut-Definitionen für die Blattwerk-Hauptansicht."""

from __future__ import annotations

from bw_libs.ui_contract.keybinding import (
    UI_MODE_DIALOG,
    UI_MODE_GLOBAL,
    UI_MODE_PREVIEW,
    KeyBindingDefinition,
    KeybindingRegistry,
)
from .shortcut_manager import ShortcutBinding
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


def _to_shortcut_binding(app, definition: KeyBindingDefinition) -> ShortcutBinding:
    """Convert central keybinding definitions to Tkinter shortcut bindings."""
    return ShortcutBinding(
        definition.sequence,
        definition.handler or (lambda: None),
        definition.description or None,
        ignore_when_text_input=not definition.allow_when_text_input,
        allow_modifiers=definition.allow_modifiers,
        binding_id=definition.binding_id,
        can_execute=lambda definition=definition: app._evaluate_keybinding_runtime(definition),
    )


def build_preview_keybinding_registry(app) -> KeybindingRegistry:
    """Build central mode-aware shortcut registry for the main preview UI."""
    registry = KeybindingRegistry()
    registry.register_many(
        [
            KeyBindingDefinition("preview.prev_page", "<Left>", UiIntent.PREVIEW_PREV_PAGE, (UI_MODE_PREVIEW,), "← / →   Seite wechseln", handler=app.prev_page),
            KeyBindingDefinition("preview.next_page", "<Right>", UiIntent.PREVIEW_NEXT_PAGE, (UI_MODE_PREVIEW,), handler=app.next_page),
            KeyBindingDefinition("preview.scroll_up", "<Up>", UiIntent.PREVIEW_SCROLL_UP, (UI_MODE_PREVIEW,), "↑ / ↓   Scrollen", handler=lambda: app._scroll_preview_vertical(-4)),
            KeyBindingDefinition("preview.scroll_down", "<Down>", UiIntent.PREVIEW_SCROLL_DOWN, (UI_MODE_PREVIEW,), handler=lambda: app._scroll_preview_vertical(4)),
            KeyBindingDefinition("preview.toggle_contrast", "<KeyPress-s>", UiIntent.PREVIEW_TOGGLE_CONTRAST, (UI_MODE_PREVIEW,), "S   Kontrast wechseln", handler=app._toggle_contrast),
            KeyBindingDefinition("preview.cycle_design", "<KeyPress-f>", UiIntent.PREVIEW_CYCLE_DESIGN, (UI_MODE_PREVIEW,), "F   Farbprofil wechseln", handler=lambda: app._cycle_design_color_profile(step=1)),
            KeyBindingDefinition("preview.black_both", "<KeyPress-k>", UiIntent.PREVIEW_BLACK_BOTH, (UI_MODE_PREVIEW,), "K   Black-Screen beides", handler=app._set_preview_black_screen_both),
            KeyBindingDefinition("preview.page_a4", "<KeyPress-4>", UiIntent.PREVIEW_PAGE_A4, (UI_MODE_PREVIEW,), "4 / 5   Seitenformat A4 / A5", handler=lambda: app._set_page_format("a4_portrait")),
            KeyBindingDefinition("preview.page_a5", "<KeyPress-5>", UiIntent.PREVIEW_PAGE_A5, (UI_MODE_PREVIEW,), handler=lambda: app._set_page_format("a5_landscape")),
            KeyBindingDefinition("preview.fit_width", "<KeyPress-0>", UiIntent.PREVIEW_FIT_WIDTH, (UI_MODE_PREVIEW,), "0 / 1   Seitenbreite / ganze Seite", handler=lambda: app.set_view_fit_mode(VIEW_FIT_WIDTH)),
            KeyBindingDefinition("preview.fit_page", "<KeyPress-1>", UiIntent.PREVIEW_FIT_PAGE, (UI_MODE_PREVIEW,), handler=lambda: app.set_view_fit_mode(VIEW_FIT_PAGE)),
            KeyBindingDefinition("preview.layout_single", "<KeyPress-e>", UiIntent.PREVIEW_LAYOUT_SINGLE, (UI_MODE_PREVIEW,), "E / N / U   Einzel / neben / untereinander", handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_SINGLE)),
            KeyBindingDefinition("preview.layout_strip", "<KeyPress-n>", UiIntent.PREVIEW_LAYOUT_STRIP, (UI_MODE_PREVIEW,), handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STRIP)),
            KeyBindingDefinition("preview.layout_stack", "<KeyPress-u>", UiIntent.PREVIEW_LAYOUT_STACK, (UI_MODE_PREVIEW,), handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STACK)),
            KeyBindingDefinition("preview.zoom_out", "<KeyPress-minus>", UiIntent.PREVIEW_ZOOM_OUT, (UI_MODE_PREVIEW,), "- / +   Zoom raus / rein", handler=lambda: app.change_zoom(-10)),
            KeyBindingDefinition("preview.zoom_in", "<KeyPress-plus>", UiIntent.PREVIEW_ZOOM_IN, (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(10)),
            KeyBindingDefinition("preview.zoom_out_numpad", "<KP_Subtract>", UiIntent.PREVIEW_ZOOM_OUT_NUMPAD, (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(-10)),
            KeyBindingDefinition("preview.zoom_in_numpad", "<KP_Add>", UiIntent.PREVIEW_ZOOM_IN_NUMPAD, (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(10)),
            KeyBindingDefinition("preview.toggle_mode", "<Tab>", UiIntent.PREVIEW_TOGGLE_MODE, (UI_MODE_PREVIEW,), "Tab   Aufgabe / Lösung", handler=app._toggle_preview_mode),
            KeyBindingDefinition("preview.refresh", "<space>", UiIntent.PREVIEW_REFRESH, (UI_MODE_PREVIEW,), "Leertaste   Vorschau aktualisieren", handler=app.refresh_preview),
            KeyBindingDefinition("global.export", "<Control-e>", UiIntent.GLOBAL_EXPORT, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+E   Exportieren", allow_modifiers=True, allow_when_text_input=True, handler=app.open_worksheet_export_dialog),
            KeyBindingDefinition("global.help_preview", "<Control-h>", UiIntent.GLOBAL_HELP_PREVIEW, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+H   Lernhilfenansicht", allow_modifiers=True, allow_when_text_input=True, handler=app.open_help_preview_window),
            KeyBindingDefinition("global.open_file", "<KeyPress-o>", UiIntent.GLOBAL_OPEN_FILE, (UI_MODE_GLOBAL,), "O   Markdown öffnen", handler=app.pick_input),
            KeyBindingDefinition("global.new_file", "<Control-n>", UiIntent.GLOBAL_NEW_FILE, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+N   neue Markdown-Datei", allow_modifiers=True, allow_when_text_input=True, handler=app.create_new_markdown_file),
            KeyBindingDefinition("global.open_file_ctrl", "<Control-o>", UiIntent.GLOBAL_OPEN_FILE_CTRL, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+O   Markdown öffnen", allow_modifiers=True, allow_when_text_input=True, handler=app.pick_input),
            KeyBindingDefinition("global.save_as", "<Control-Shift-s>", UiIntent.GLOBAL_SAVE_AS, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+S   Speichern unter", allow_modifiers=True, allow_when_text_input=True, handler=app.save_markdown_file_as),
            KeyBindingDefinition("global.settings", "<Control-comma>", UiIntent.GLOBAL_SETTINGS, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+,   Einstellungen", allow_modifiers=True, allow_when_text_input=True, handler=app._open_local_settings_dialog),
            KeyBindingDefinition("global.view_preview", "<Control-Key-1>", UiIntent.GLOBAL_VIEW_PREVIEW, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+1/2/3   Vorschau / beides / Editor", allow_modifiers=True, allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY)),
            KeyBindingDefinition("global.view_both", "<Control-Key-2>", UiIntent.GLOBAL_VIEW_BOTH, (UI_MODE_GLOBAL, UI_MODE_DIALOG), allow_modifiers=True, allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_BOTH)),
            KeyBindingDefinition("global.view_editor", "<Control-Key-3>", UiIntent.GLOBAL_VIEW_EDITOR, (UI_MODE_GLOBAL, UI_MODE_DIALOG), allow_modifiers=True, allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY)),
            KeyBindingDefinition("global.cycle_theme", "<Control-t>", UiIntent.GLOBAL_CYCLE_THEME, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+T   Theme wechseln", allow_modifiers=True, allow_when_text_input=True, handler=app._cycle_theme),
            KeyBindingDefinition("global.cycle_font", "<Control-f>", UiIntent.GLOBAL_CYCLE_FONT, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+F   Schriftprofil wechseln", allow_modifiers=True, allow_when_text_input=True, handler=app._cycle_font_profile),
            KeyBindingDefinition("global.open_recent", "<KeyPress-z>", UiIntent.GLOBAL_OPEN_RECENT, (UI_MODE_GLOBAL,), "Z   zuletzt geladenes Markdown", handler=app._open_last_markdown),
            KeyBindingDefinition("global.debug_overlay", "<Control-Shift-d>", UiIntent.GLOBAL_DEBUG_OVERLAY, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+D   Shortcut-Debug-Overlay", allow_modifiers=True, allow_when_text_input=True, handler=app._toggle_shortcut_debug_overlay),
            KeyBindingDefinition("global.debug_offline", "<Control-Shift-o>", UiIntent.GLOBAL_DEBUG_OFFLINE, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+O   Offline simulieren", allow_modifiers=True, allow_when_text_input=True, handler=app._toggle_shortcut_debug_offline),
            KeyBindingDefinition("global.escape", "<Escape>", UiIntent.GLOBAL_ESCAPE, (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Esc   Zurueck", handler=app._handle_global_escape),
        ]
    )
    return registry


def build_preview_shortcuts(app, registry: KeybindingRegistry | None = None):
    """Return main-window shortcuts derived from the central registry."""
    active_registry = registry or build_preview_keybinding_registry(app)
    return [_to_shortcut_binding(app, definition) for definition in active_registry.all()]


def get_preview_shortcut_mode_manifest(app) -> dict[str, list[str]]:
    """Return mode to binding-id mapping for debug/help output."""
    return build_preview_keybinding_registry(app).mode_manifest()
