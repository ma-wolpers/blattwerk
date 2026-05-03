"""Shortcut-Definitionen für die Blattwerk-Hauptansicht."""

from __future__ import annotations

from .keybinding_registry import (
    UI_MODE_DIALOG,
    UI_MODE_GLOBAL,
    UI_MODE_PREVIEW,
    KeyBindingDefinition,
    KeybindingRegistry,
)
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


def _to_shortcut_binding(definition: KeyBindingDefinition) -> ShortcutBinding:
    """Convert central keybinding definitions to Tkinter shortcut bindings."""
    return ShortcutBinding(
        definition.sequence,
        definition.handler or (lambda: None),
        definition.description or None,
        ignore_when_text_input=not definition.allow_when_text_input,
        allow_modifiers=definition.allow_modifiers,
    )


def build_preview_keybinding_registry(app) -> KeybindingRegistry:
    """Build central mode-aware shortcut registry for the main preview UI."""
    registry = KeybindingRegistry()
    registry.register_many(
        [
            KeyBindingDefinition("preview.prev_page", "<Left>", "preview.prev_page", (UI_MODE_PREVIEW,), "← / →   Seite wechseln", handler=app.prev_page),
            KeyBindingDefinition("preview.next_page", "<Right>", "preview.next_page", (UI_MODE_PREVIEW,), handler=app.next_page),
            KeyBindingDefinition("preview.scroll_up", "<Up>", "preview.scroll_up", (UI_MODE_PREVIEW,), "↑ / ↓   Scrollen", handler=lambda: app._scroll_preview_vertical(-4)),
            KeyBindingDefinition("preview.scroll_down", "<Down>", "preview.scroll_down", (UI_MODE_PREVIEW,), handler=lambda: app._scroll_preview_vertical(4)),
            KeyBindingDefinition("preview.toggle_contrast", "<KeyPress-s>", "preview.toggle_contrast", (UI_MODE_PREVIEW,), "S   Kontrast wechseln", handler=app._toggle_contrast),
            KeyBindingDefinition("preview.cycle_design", "<KeyPress-f>", "preview.cycle_design", (UI_MODE_PREVIEW,), "F   Farbprofil wechseln", handler=lambda: app._cycle_design_color_profile(step=1)),
            KeyBindingDefinition("preview.black_both", "<KeyPress-k>", "preview.black_both", (UI_MODE_PREVIEW,), "K   Black-Screen beides", handler=app._set_preview_black_screen_both),
            KeyBindingDefinition("preview.page_a4", "<KeyPress-4>", "preview.page_a4", (UI_MODE_PREVIEW,), "4 / 5   Seitenformat A4 / A5", handler=lambda: app._set_page_format("a4_portrait")),
            KeyBindingDefinition("preview.page_a5", "<KeyPress-5>", "preview.page_a5", (UI_MODE_PREVIEW,), handler=lambda: app._set_page_format("a5_landscape")),
            KeyBindingDefinition("preview.fit_width", "<KeyPress-0>", "preview.fit_width", (UI_MODE_PREVIEW,), "0 / 1   Seitenbreite / ganze Seite", handler=lambda: app.set_view_fit_mode(VIEW_FIT_WIDTH)),
            KeyBindingDefinition("preview.fit_page", "<KeyPress-1>", "preview.fit_page", (UI_MODE_PREVIEW,), handler=lambda: app.set_view_fit_mode(VIEW_FIT_PAGE)),
            KeyBindingDefinition("preview.layout_single", "<KeyPress-e>", "preview.layout_single", (UI_MODE_PREVIEW,), "E / N / U   Einzel / neben / untereinander", handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_SINGLE)),
            KeyBindingDefinition("preview.layout_strip", "<KeyPress-n>", "preview.layout_strip", (UI_MODE_PREVIEW,), handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STRIP)),
            KeyBindingDefinition("preview.layout_stack", "<KeyPress-u>", "preview.layout_stack", (UI_MODE_PREVIEW,), handler=lambda: app.set_preview_layout_mode(VIEW_LAYOUT_STACK)),
            KeyBindingDefinition("preview.zoom_out", "<KeyPress-minus>", "preview.zoom_out", (UI_MODE_PREVIEW,), "- / +   Zoom raus / rein", handler=lambda: app.change_zoom(-10)),
            KeyBindingDefinition("preview.zoom_in", "<KeyPress-plus>", "preview.zoom_in", (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(10)),
            KeyBindingDefinition("preview.zoom_out_numpad", "<KP_Subtract>", "preview.zoom_out_numpad", (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(-10)),
            KeyBindingDefinition("preview.zoom_in_numpad", "<KP_Add>", "preview.zoom_in_numpad", (UI_MODE_PREVIEW,), handler=lambda: app.change_zoom(10)),
            KeyBindingDefinition("preview.toggle_mode", "<Tab>", "preview.toggle_mode", (UI_MODE_PREVIEW,), "Tab   Aufgabe / Lösung", handler=app._toggle_preview_mode),
            KeyBindingDefinition("preview.refresh", "<space>", "preview.refresh", (UI_MODE_PREVIEW,), "Leertaste   Vorschau aktualisieren", handler=app.refresh_preview),
            KeyBindingDefinition("global.export", "<Control-e>", "global.export", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+E   Exportieren", allow_modifiers=True, allow_when_text_input=True, handler=app.open_worksheet_export_dialog),
            KeyBindingDefinition("global.help_preview", "<Control-h>", "global.help_preview", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+H   Lernhilfenansicht", allow_modifiers=True, allow_when_text_input=True, handler=app.open_help_preview_window),
            KeyBindingDefinition("global.open_file", "<KeyPress-o>", "global.open_file", (UI_MODE_GLOBAL,), "O   Markdown öffnen", handler=app.pick_input),
            KeyBindingDefinition("global.new_file", "<Control-n>", "global.new_file", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+N   neue Markdown-Datei", allow_modifiers=True, allow_when_text_input=True, handler=app.create_new_markdown_file),
            KeyBindingDefinition("global.open_file_ctrl", "<Control-o>", "global.open_file_ctrl", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+O   Markdown öffnen", allow_modifiers=True, allow_when_text_input=True, handler=app.pick_input),
            KeyBindingDefinition("global.save_as", "<Control-Shift-s>", "global.save_as", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+Shift+S   Speichern unter", allow_modifiers=True, allow_when_text_input=True, handler=app.save_markdown_file_as),
            KeyBindingDefinition("global.settings", "<Control-comma>", "global.settings", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+,   Einstellungen", allow_modifiers=True, allow_when_text_input=True, handler=app._open_local_settings_dialog),
            KeyBindingDefinition("global.view_preview", "<Control-Key-1>", "global.view_preview", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+1/2/3   Vorschau / beides / Editor", allow_modifiers=True, allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY)),
            KeyBindingDefinition("global.view_both", "<Control-Key-2>", "global.view_both", (UI_MODE_GLOBAL, UI_MODE_DIALOG), allow_modifiers=True, allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_BOTH)),
            KeyBindingDefinition("global.view_editor", "<Control-Key-3>", "global.view_editor", (UI_MODE_GLOBAL, UI_MODE_DIALOG), allow_modifiers=True, allow_when_text_input=True, handler=lambda: app._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY)),
            KeyBindingDefinition("global.cycle_theme", "<Control-t>", "global.cycle_theme", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+T   Theme wechseln", allow_modifiers=True, allow_when_text_input=True, handler=app._cycle_theme),
            KeyBindingDefinition("global.cycle_font", "<Control-f>", "global.cycle_font", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Strg+F   Schriftprofil wechseln", allow_modifiers=True, allow_when_text_input=True, handler=app._cycle_font_profile),
            KeyBindingDefinition("global.open_recent", "<KeyPress-z>", "global.open_recent", (UI_MODE_GLOBAL,), "Z   zuletzt geladenes Markdown", handler=app._open_last_markdown),
            KeyBindingDefinition("global.exit", "<Escape>", "global.exit", (UI_MODE_GLOBAL, UI_MODE_DIALOG), "Esc   Beenden", handler=app.root.destroy),
        ]
    )
    return registry


def build_preview_shortcuts(app):
    """Return main-window shortcuts derived from the central registry."""
    registry = build_preview_keybinding_registry(app)
    return [_to_shortcut_binding(definition) for definition in registry.all()]


def get_preview_shortcut_mode_manifest(app) -> dict[str, list[str]]:
    """Return mode to binding-id mapping for debug/help output."""
    return build_preview_keybinding_registry(app).mode_manifest()
