"""Blattwerk-specific theme configuration.

Delegates to bw_gui.theming for the canonical theme registry, color math, and
the shared ttk baseline.  Only Blattwerk-specific widget overrides live here.

``THEME_ORDER`` and ``get_theme`` / ``normalize_theme_key`` are re-exported so
existing callers across the codebase do not need import changes.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from bw_gui.runtime import ui, widgets
from bw_gui.runtime.platform import apply_window_chrome_theme
from bw_gui.theming import (
    THEME_ORDER,
    configure_ttk_theme as _configure_base,
    get_theme as _get_theme,
    is_dark_color,
    mix_hex,
    normalize_theme_key as _normalize,
)

DEFAULT_THEME = "slate_indigo"


def normalize_theme_key(theme_key: str | None = None) -> str:
    """Return *theme_key* if known, otherwise bw_gui's DEFAULT_THEME.

    Re-exported so callers in blatt_ui_persistence can continue to import
    from this module without change.
    """
    return _normalize(theme_key)


def get_theme(theme_key: str | None = None) -> dict[str, str]:
    """Return the fully-resolved theme dict for *theme_key*.

    Wraps ``bw_gui.theming.get_theme()``, which fills semantic defaults and
    applies intensity scaling.  Re-exported so existing callers do not need to
    update their imports.
    """
    return _get_theme(theme_key)


def is_dark_theme(theme_key: str | None = None) -> bool:
    """Return True if the background of *theme_key* is perceptually dark.

    Used by the editor to decide whether to load a dark or light syntax
    highlighting preset.
    """
    return is_dark_color(get_theme(theme_key)["bg_main"])


def apply_window_theme(window: ui.Misc, theme_key: str | None = None) -> None:
    """Set *window*'s background to ``bg_main`` and apply the Windows title bar chrome.

    Call this once per theme switch on every top-level window (main window,
    export dialog, help preview).  The chrome call is a no-op on non-Windows
    platforms.
    """
    theme = get_theme(theme_key)
    window.configure(bg=theme["bg_main"])
    apply_window_chrome_theme(window, prefer_dark=is_dark_theme(theme_key))


def configure_ttk_theme(root: ui.Misc, theme_key: str | None = None) -> None:
    """Configure the bw_gui baseline and add Blattwerk-specific style overrides.

    Calls ``bw_gui.theming.configure_ttk_theme()`` first to establish the
    shared baseline (frames, labels, action buttons, segmented controls,
    scrollbars, treeview …), then applies Blattwerk additions:

    - ``TLabelframe`` / ``TLabelframe.Label`` — themed group-box border and
      label, used in settings panels and the export dialog.
    - ``TSeparator`` — thin divider using the border color.
    - ``TRadiobutton`` — background fixed to ``bg_main`` so radio buttons do
      not bleed into themed panels.
    - ``TEntry`` readonly state map — marks read-only fields with the same
      colors as editable ones (Blattwerk shows non-editable fields in read-only
      entry widgets).
    - ``TCombobox`` extended — adds an arrow-button background derived from the
      border/surface mix, active/readonly maps, and ``option_add`` calls that
      theme the native dropdown Listbox (background, foreground, selection
      colors).  The bw_gui baseline does not include these dropdown options.

    Args:
        root:      Any Tk widget; passed to bw_gui and used for ``option_add``.
        theme_key: Active theme key, falls back to bw_gui's DEFAULT_THEME.
    """
    _configure_base(root, theme_key)

    theme = get_theme(theme_key)
    style = widgets.Style(root)
    border = theme["border"]

    style.configure(
        "TLabelframe",
        background=theme["bg_main"],
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=theme["bg_main"],
        foreground=theme["fg_muted"],
        font=("Segoe UI Semibold", 9),
    )
    style.configure("TSeparator", background=border)
    style.configure(
        "TRadiobutton",
        background=theme["bg_main"],
        foreground=theme["fg_primary"],
    )
    style.map(
        "TRadiobutton",
        background=[("active", theme["bg_main"]), ("selected", theme["bg_main"])],
    )
    style.map(
        "TEntry",
        fieldbackground=[("readonly", theme["bg_surface"])],
        foreground=[("readonly", theme["fg_primary"])],
    )

    combo_arrow_bg = mix_hex(border, theme["bg_surface"], 0.40)
    combo_arrow_hover_bg = mix_hex(theme["accent_soft"], theme["bg_surface"], 0.48)
    style.configure(
        "TCombobox",
        fieldbackground=theme["bg_surface"],
        background=combo_arrow_bg,
        foreground=theme["fg_primary"],
        arrowcolor=theme["fg_primary"],
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
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


def style_canvas(canvas: ui.Canvas, theme_key: str | None = None) -> None:
    """Set the preview canvas background to ``bg_main`` with no highlight border.

    Uses ``bg_main`` (not ``bg_surface``) so the canvas blends into the main
    panel rather than appearing raised.  The ``highlightthickness=0`` removes
    the default focus border, which would create a visible outline around the
    preview area.

    For generic non-preview canvases use ``bw_gui.theming.theme_canvas()``
    instead, which uses ``bg_surface`` and a 1-pixel border.
    """
    theme = get_theme(theme_key)
    canvas.configure(background=theme["bg_main"], highlightthickness=0)


def style_preview_placeholder(
    canvas: ui.Canvas,
    text_item_id: int,
    theme_key: str | None = None,
) -> None:
    """Update the fill color of a placeholder text canvas item to ``fg_muted``.

    Called when a preview canvas has no content yet; the placeholder text
    should read as secondary/muted against the ``bg_main`` canvas background.

    Args:
        canvas:       The canvas widget containing the placeholder text item.
        text_item_id: Canvas item ID returned by ``canvas.create_text()``.
        theme_key:    Active theme key.
    """
    theme = get_theme(theme_key)
    canvas.itemconfig(text_item_id, fill=theme["fg_muted"])
