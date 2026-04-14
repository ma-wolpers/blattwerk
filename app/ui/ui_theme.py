"""Zentrale Theme-Verwaltung für die Blattwerk-UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .window_identity import apply_window_chrome_theme


THEMES = {
    "slate_indigo": {
        "label": "Slate & Indigo",
        "bg_main": "#EEF1F6",
        "bg_surface": "#FFFFFF",
        "fg_primary": "#1F2937",
        "fg_muted": "#5B6472",
        "accent": "#4F46E5",
        "accent_hover": "#4338CA",
        "accent_soft": "#DDE1FF",
        "danger": "#A73B3B",
        "border": "#C7CFDD",
        "button_fg": "#FFFFFF",
    },
    "forest_moss": {
        "label": "Forest & Moss",
        "bg_main": "#EEF3EF",
        "bg_surface": "#FAFCFA",
        "fg_primary": "#21322A",
        "fg_muted": "#587265",
        "accent": "#3E7A5D",
        "accent_hover": "#33664E",
        "accent_soft": "#D7E6DD",
        "danger": "#A14D45",
        "border": "#BDD1C5",
        "button_fg": "#FFFFFF",
    },
    "sand_terracotta": {
        "label": "Sand & Terracotta",
        "bg_main": "#F5EFE6",
        "bg_surface": "#FFF9F3",
        "fg_primary": "#3B3129",
        "fg_muted": "#7A6A5E",
        "accent": "#B8634F",
        "accent_hover": "#A45443",
        "accent_soft": "#EBD8CC",
        "danger": "#9B4A3B",
        "border": "#D9C7B8",
        "button_fg": "#FFFFFF",
    },
    "midnight_cyan": {
        "label": "Midnight & Cyan",
        "bg_main": "#1E252D",
        "bg_surface": "#26313C",
        "fg_primary": "#CCD6E0",
        "fg_muted": "#9DAAB8",
        "accent": "#18A7C9",
        "accent_hover": "#1286A2",
        "accent_soft": "#2F3E4A",
        "danger": "#E08A7E",
        "border": "#435564",
        "button_fg": "#FFFFFF",
    },
    "lavender_graphite": {
        "label": "Lavender & Graphite",
        "bg_main": "#F2F1F8",
        "bg_surface": "#FCFBFF",
        "fg_primary": "#302D39",
        "fg_muted": "#666174",
        "accent": "#6E5BC7",
        "accent_hover": "#5946B1",
        "accent_soft": "#E0DAF6",
        "danger": "#A84A66",
        "border": "#CBC4E7",
        "button_fg": "#FFFFFF",
    },
    "obsidian_gold": {
        "label": "Obsidian & Gold",
        "bg_main": "#1C1D1F",
        "bg_surface": "#242629",
        "fg_primary": "#D6CEBF",
        "fg_muted": "#AAA18F",
        "accent": "#C9A34A",
        "accent_hover": "#B28E3E",
        "accent_soft": "#34312A",
        "danger": "#D9886B",
        "border": "#4A4740",
        "button_fg": "#121212",
    },
}

THEME_ORDER = [
    "slate_indigo",
    "forest_moss",
    "sand_terracotta",
    "midnight_cyan",
    "lavender_graphite",
    "obsidian_gold",
]

DEFAULT_THEME = "slate_indigo"


def normalize_theme_key(theme_key: str | None = None) -> str:
    """Normalisiert Theme-Schlüssel auf ein vorhandenes Profil."""
    return theme_key if theme_key in THEMES else DEFAULT_THEME


def get_theme(theme_key: str | None = None) -> dict:
    """Liefert das aktive Theme-Dictionary."""
    return THEMES[normalize_theme_key(theme_key)]


def _relative_luminance(hex_color: str) -> float:
    """Berechnet die relative Luminanz einer Hex-Farbe."""
    color = (hex_color or "").strip().lstrip("#")
    if len(color) != 6:
        return 0.0

    try:
        red = int(color[0:2], 16) / 255.0
        green = int(color[2:4], 16) / 255.0
        blue = int(color[4:6], 16) / 255.0
    except ValueError:
        return 0.0

    def srgb_to_linear(channel: float) -> float:
        return (
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )

    r_lin = srgb_to_linear(red)
    g_lin = srgb_to_linear(green)
    b_lin = srgb_to_linear(blue)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def _contrast_text_color(bg_hex: str) -> str:
    """Wählt eine kontrastreiche Textfarbe für einen Hintergrund."""
    return "#111111" if _relative_luminance(bg_hex) >= 0.38 else "#FFFFFF"


def _mix_hex(base_hex: str, target_hex: str, ratio: float) -> str:
    """Mischt zwei Hex-Farben linear anhand von `ratio`."""
    ratio = max(0.0, min(1.0, ratio))

    def _hex_to_rgb(value: str):
        color = (value or "").strip().lstrip("#")
        if len(color) != 6:
            return (0, 0, 0)
        try:
            return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))
        except ValueError:
            return (0, 0, 0)

    base_r, base_g, base_b = _hex_to_rgb(base_hex)
    target_r, target_g, target_b = _hex_to_rgb(target_hex)

    out_r = round(base_r * (1.0 - ratio) + target_r * ratio)
    out_g = round(base_g * (1.0 - ratio) + target_g * ratio)
    out_b = round(base_b * (1.0 - ratio) + target_b * ratio)

    return f"#{out_r:02X}{out_g:02X}{out_b:02X}"


def apply_window_theme(window: tk.Misc, theme_key: str | None = None):
    """Wendet die Grundhintergrundfarbe auf ein Tk-Fenster an."""
    theme = get_theme(theme_key)
    window.configure({"bg": theme["bg_main"]})
    is_dark_theme = _relative_luminance(theme["bg_main"]) < 0.20
    apply_window_chrome_theme(window, prefer_dark=is_dark_theme)


def is_dark_theme(theme_key: str | None = None) -> bool:
    """Liefert, ob das Theme als dunkel eingestuft wird."""
    theme = get_theme(theme_key)
    return _relative_luminance(theme["bg_main"]) < 0.20


def configure_ttk_theme(root: tk.Misc, theme_key: str | None = None):
    """Konfiguriert zentrale ttk-Styles auf Basis des gewählten Themes."""

    theme = get_theme(theme_key)
    dark_theme = is_dark_theme(theme_key)
    style = ttk.Style(root)
    ui_border = theme["border"]
    primary_bg = theme["accent"]
    primary_hover_bg = theme["accent_hover"]
    secondary_bg = ui_border
    secondary_hover_bg = theme["accent_soft"]
    nav_bg = _mix_hex(ui_border, "#59A972", 0.20)
    nav_hover_bg = _mix_hex(theme["accent_soft"], "#59A972", 0.16)
    util_bg = _mix_hex(ui_border, "#8B73D9", 0.20)
    util_hover_bg = _mix_hex(theme["accent_soft"], "#8B73D9", 0.16)

    primary_fg = _contrast_text_color(primary_bg)
    primary_hover_fg = _contrast_text_color(primary_hover_bg)
    secondary_fg = _contrast_text_color(secondary_bg)
    secondary_hover_fg = _contrast_text_color(secondary_hover_bg)
    nav_fg = _contrast_text_color(nav_bg)
    nav_hover_fg = _contrast_text_color(nav_hover_bg)
    util_fg = _contrast_text_color(util_bg)
    util_hover_fg = _contrast_text_color(util_hover_bg)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=theme["bg_main"])
    style.configure(
        "TLabel", background=theme["bg_main"], foreground=theme["fg_primary"]
    )
    style.configure(
        "TLabelframe",
        background=theme["bg_main"],
        bordercolor=ui_border,
        lightcolor=ui_border,
        darkcolor=ui_border,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=theme["bg_main"],
        foreground=theme["fg_muted"],
        font=("Segoe UI Semibold", 9),
    )
    style.configure("TSeparator", background=ui_border)
    style.configure(
        "TRadiobutton", background=theme["bg_main"], foreground=theme["fg_primary"]
    )
    style.map(
        "TRadiobutton",
        background=[("active", theme["bg_main"]), ("selected", theme["bg_main"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=theme["bg_surface"],
        foreground=theme["fg_primary"],
        bordercolor=ui_border,
        lightcolor=ui_border,
        darkcolor=ui_border,
    )
    style.map(
        "TEntry",
        fieldbackground=[("readonly", theme["bg_surface"])],
        foreground=[("readonly", theme["fg_primary"])],
    )

    combo_arrow_bg = _mix_hex(theme["border"], theme["bg_surface"], 0.40)
    combo_arrow_hover_bg = _mix_hex(theme["accent_soft"], theme["bg_surface"], 0.48)
    style.configure(
        "TCombobox",
        fieldbackground=theme["bg_surface"],
        background=combo_arrow_bg,
        foreground=theme["fg_primary"],
        arrowcolor=theme["fg_primary"],
        bordercolor=ui_border,
        lightcolor=ui_border,
        darkcolor=ui_border,
        selectbackground=theme["accent_soft"],
        selectforeground=theme["fg_primary"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", theme["bg_surface"])],
        background=[("readonly", combo_arrow_bg), ("active", combo_arrow_hover_bg)],
        foreground=[("readonly", theme["fg_primary"])],
        arrowcolor=[("active", theme["fg_primary"])],
        selectbackground=[("readonly", theme["accent_soft"])],
        selectforeground=[("readonly", theme["fg_primary"])],
    )
    root.option_add("*TCombobox*Listbox.background", theme["bg_surface"])
    root.option_add("*TCombobox*Listbox.foreground", theme["fg_primary"])
    root.option_add("*TCombobox*Listbox.selectBackground", theme["accent_soft"])
    root.option_add("*TCombobox*Listbox.selectForeground", theme["fg_primary"])

    scroll_bg = _mix_hex(theme["border"], theme["bg_surface"], 0.35)
    scroll_active_bg = _mix_hex(theme["accent_soft"], theme["bg_surface"], 0.52)
    style.configure(
        "TScrollbar",
        troughcolor=theme["bg_main"],
        background=scroll_bg,
        arrowcolor=theme["fg_primary"],
        bordercolor=ui_border,
        lightcolor=ui_border,
        darkcolor=ui_border,
        gripcount=0,
    )
    style.map(
        "TScrollbar",
        background=[("active", scroll_active_bg), ("pressed", scroll_active_bg)],
        arrowcolor=[("disabled", theme["fg_muted"])],
    )
    style.configure(
        "Muted.TLabel", background=theme["bg_main"], foreground=theme["fg_muted"]
    )

    style.configure(
        "TButton",
        background=secondary_bg,
        foreground=secondary_fg,
        bordercolor=ui_border,
        lightcolor=ui_border,
        darkcolor=ui_border,
        padding=(10, 6),
        relief="flat",
        font=("Segoe UI", 9),
    )
    style.map(
        "TButton",
        background=[("active", secondary_hover_bg), ("pressed", secondary_hover_bg)],
        foreground=[("active", secondary_hover_fg), ("pressed", secondary_hover_fg)],
    )

    style.configure(
        "PrimaryAction.TButton",
        padding=(16, 6),
        font=("Segoe UI", 10),
        background=primary_bg,
        foreground=primary_fg,
        bordercolor=theme["accent_hover"],
        lightcolor=theme["accent_hover"],
        darkcolor=theme["accent_hover"],
        relief="flat",
    )
    style.map(
        "PrimaryAction.TButton",
        background=[("active", primary_hover_bg), ("pressed", primary_hover_bg)],
        foreground=[("active", primary_hover_fg), ("pressed", primary_hover_fg)],
    )

    style.configure(
        "SecondaryAction.TButton",
        background=secondary_bg,
        foreground=secondary_fg,
        bordercolor=ui_border,
        lightcolor=ui_border,
        darkcolor=ui_border,
        relief="flat",
        font=("Segoe UI", 9),
    )
    style.map(
        "SecondaryAction.TButton",
        background=[("active", secondary_hover_bg), ("pressed", secondary_hover_bg)],
        foreground=[("active", secondary_hover_fg), ("pressed", secondary_hover_fg)],
    )

    style.configure(
        "NavAction.TButton",
        background=nav_bg,
        foreground=nav_fg,
        bordercolor=nav_bg,
        lightcolor=nav_bg,
        darkcolor=nav_bg,
        relief="flat",
        font=("Segoe UI", 9),
    )
    style.map(
        "NavAction.TButton",
        background=[("active", nav_hover_bg), ("pressed", nav_hover_bg)],
        foreground=[("active", nav_hover_fg), ("pressed", nav_hover_fg)],
    )

    style.configure(
        "UtilityAction.TButton",
        background=util_bg,
        foreground=util_fg,
        bordercolor=util_bg,
        lightcolor=util_bg,
        darkcolor=util_bg,
        relief="flat",
        font=("Segoe UI", 9),
    )
    style.map(
        "UtilityAction.TButton",
        background=[("active", util_hover_bg), ("pressed", util_hover_bg)],
        foreground=[("active", util_hover_fg), ("pressed", util_hover_fg)],
    )

    strip_bg = _mix_hex(theme["bg_surface"], theme["accent_soft"], 0.22)
    strip_border = _mix_hex(ui_border, theme["accent"], 0.18)
    segmented_bg = _mix_hex(theme["bg_surface"], theme["accent_soft"], 0.35)
    segmented_fg = theme["fg_primary"]
    segmented_active_bg = _mix_hex(theme["accent"], theme["bg_surface"], 0.14)
    segmented_active_fg = _contrast_text_color(segmented_active_bg)
    tab_bg = _mix_hex(theme["bg_surface"], theme["accent_soft"], 0.15)
    tab_selected_bg = _mix_hex(theme["accent"], theme["bg_surface"], 0.12)
    tab_hover_bg = _mix_hex(theme["accent_soft"], theme["bg_surface"], 0.30)

    style.configure(
        "ControlStrip.TFrame",
        background=strip_bg,
        bordercolor=strip_border,
        relief="flat",
    )
    style.configure(
        "ControlStripLabel.TLabel",
        background=strip_bg,
        foreground=theme["fg_primary"],
        font=("Segoe UI Semibold", 9),
    )
    style.configure(
        "ControlStrip.TSeparator",
        background=strip_border,
    )

    style.configure(
        "Segmented.TButton",
        background=segmented_bg,
        foreground=segmented_fg,
        bordercolor=strip_border,
        lightcolor=strip_border,
        darkcolor=strip_border,
        padding=(12, 5),
        relief="flat",
        font=("Segoe UI", 9),
    )
    style.map(
        "Segmented.TButton",
        background=[("active", tab_hover_bg), ("pressed", tab_hover_bg)],
        foreground=[("active", theme["fg_primary"]), ("pressed", theme["fg_primary"])],
    )

    style.configure(
        "SegmentedActive.TButton",
        background=segmented_active_bg,
        foreground=segmented_active_fg,
        bordercolor=theme["accent"],
        lightcolor=theme["accent"],
        darkcolor=theme["accent"],
        padding=(12, 5),
        relief="flat",
        font=("Segoe UI Semibold", 9),
    )
    style.map(
        "SegmentedActive.TButton",
        background=[("active", primary_hover_bg), ("pressed", primary_hover_bg)],
        foreground=[("active", primary_hover_fg), ("pressed", primary_hover_fg)],
    )

    style.configure(
        "ControlStrip.TNotebook",
        background=strip_bg,
        bordercolor=strip_border,
        lightcolor=strip_border,
        darkcolor=strip_border,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "ControlStrip.TNotebook.Tab",
        background=tab_bg,
        foreground=theme["fg_muted"],
        bordercolor=strip_border,
        lightcolor=strip_border,
        darkcolor=strip_border,
        padding=(12, 5),
        font=("Segoe UI", 9),
    )
    style.map(
        "ControlStrip.TNotebook.Tab",
        background=[("selected", tab_selected_bg), ("active", tab_hover_bg)],
        foreground=[("selected", theme["fg_primary"]), ("active", theme["fg_primary"])],
    )


def style_canvas(canvas: tk.Canvas, theme_key: str | None = None):
    """Wendet Canvas-Themefarben für die Vorschau an."""
    theme = get_theme(theme_key)
    canvas.configure(background=theme["bg_main"], highlightthickness=0)


def style_preview_placeholder(
    canvas: tk.Canvas, text_item_id: int, theme_key: str | None = None
):
    """Setzt die Platzhalter-Farbe im Preview-Canvas."""
    theme = get_theme(theme_key)
    canvas.itemconfig(text_item_id, fill=theme["fg_muted"])


def populate_theme_menu(view_menu: tk.Menu, theme_var: tk.StringVar, on_theme_changed):
    """Befüllt ein Tkinter-Menu mit einheitlichen Theme-Radiobuttons."""

    for theme_key in THEME_ORDER:
        view_menu.add_radiobutton(
            label=THEMES[theme_key]["label"],
            variable=theme_var,
            value=theme_key,
            command=on_theme_changed,
        )
