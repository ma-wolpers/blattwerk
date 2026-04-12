"""UI construction mixin for the main window and canvas wiring."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
    PREVIEW_CANVAS_PADDING_PX,
    PREVIEW_MIN_FRAME_PX,
    PREVIEW_PAGE_GAP_PX,
    PREVIEW_PAGE_MARGIN_PX,
    PREVIEW_SCALE_MAX,
    PREVIEW_SCALE_MIN,
    PREVIEW_ZOOM_MAX_PERCENT,
    PREVIEW_ZOOM_MIN_PERCENT,
    VIEW_LAYOUT_STACK,
    VIEW_LAYOUT_STRIP,
)
from .ui_theme import get_theme
from ..styles.blatt_styles import (
    FONT_PROFILE_LABELS,
    FONT_PROFILE_ORDER,
    FONT_SIZE_PROFILE_LABELS,
    FONT_SIZE_PROFILE_ORDER,
)
from ..styles.worksheet_design import (
    COLOR_PROFILE_ORDER,
    CONTRAST_PROFILE_LABELS,
    CONTRAST_PROFILE_ORDER,
)


class BlattwerkAppBuildMixin:
    """Baut die Hauptoberfläche und verdrahtet Preview-Canvas/Controls."""
    def _build_ui(self):
        """Build ui."""
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Blattwerk Vorschau", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Markdown laden, Vorschau prüfen, danach gezielt exportieren.").pack(anchor="w", pady=(2, 10))

        file_row = ttk.Frame(outer)
        file_row.pack(fill="x", pady=(0, 8))
        ttk.Label(file_row, text="Markdown-Datei:", width=16).pack(side="left")
        ttk.Entry(file_row, textvariable=self.input_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(file_row, text="Durchsuchen…", command=self.pick_input, style="SecondaryAction.TButton").pack(side="left")

        options_row = ttk.Frame(outer)
        options_row.pack(fill="x", pady=(0, 8))

        ttk.Label(options_row, text="Format:", width=16).pack(side="left")
        ttk.Radiobutton(
            options_row,
            text="Aufgabe",
            value="worksheet",
            variable=self.preview_mode_var,
            command=self.refresh_preview,
        ).pack(side="left")
        ttk.Radiobutton(
            options_row,
            text="Lösung",
            value="solution",
            variable=self.preview_mode_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))

        ttk.Separator(options_row, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Radiobutton(
            options_row,
            text="DIN A4",
            value="a4_portrait",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left")
        ttk.Radiobutton(
            options_row,
            text="DIN A5",
            value="a5_landscape",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))

        ttk.Separator(options_row, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Label(options_row, text="Bereich:").pack(side="left")
        ttk.Radiobutton(
            options_row,
            text="Vorschau",
            value=EDITOR_VIEW_PREVIEW_ONLY,
            variable=self.editor_view_mode_var,
            command=lambda: self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY),
        ).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(
            options_row,
            text="Beides",
            value=EDITOR_VIEW_BOTH,
            variable=self.editor_view_mode_var,
            command=lambda: self._set_editor_view_mode(EDITOR_VIEW_BOTH),
        ).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(
            options_row,
            text="Schreibbereich",
            value=EDITOR_VIEW_EDITOR_ONLY,
            variable=self.editor_view_mode_var,
            command=lambda: self._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY),
        ).pack(side="left", padx=(8, 0))

        design_row = ttk.Frame(outer)
        design_row.pack(fill="x", pady=(0, 8))

        ttk.Label(design_row, text="Gestaltung:", width=16).pack(side="left")

        ttk.Label(design_row, text="Kontrast:").pack(side="left")
        for contrast_key in CONTRAST_PROFILE_ORDER:
            ttk.Radiobutton(
                design_row,
                text=CONTRAST_PROFILE_LABELS[contrast_key],
                value=contrast_key,
                variable=self.preview_contrast_var,
                command=self.refresh_preview,
            ).pack(side="left", padx=(8, 0))

        ttk.Separator(design_row, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Label(design_row, text="Farbprofil:").pack(side="left")

        for profile_key in COLOR_PROFILE_ORDER:
            swatch = tk.Canvas(
                design_row,
                width=28,
                height=20,
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            swatch.pack(side="left", padx=(6, 0))
            swatch.bind("<Button-1>", lambda _event, key=profile_key: self._set_color_profile(key))
            swatch.bind("<Enter>", lambda event, key=profile_key: self._on_color_profile_swatch_enter(event, key))
            swatch.bind("<Leave>", self._on_color_profile_swatch_leave)
            self._color_profile_swatches[profile_key] = swatch

        self._refresh_color_profile_swatches()

        ttk.Separator(design_row, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Label(design_row, text="Schrift: ").pack(side="left")
        self.font_profile_combo = ttk.Combobox(
            design_row,
            state="readonly",
            width=14,
            values=[FONT_PROFILE_LABELS[key] for key in FONT_PROFILE_ORDER],
        )
        self.font_profile_combo.pack(side="left", padx=(8, 0))
        self._sync_font_profile_combo()
        self.font_profile_combo.bind("<<ComboboxSelected>>", self._on_font_profile_selected)

        ttk.Label(design_row, text="Größe:").pack(side="left", padx=(12, 0))
        self.font_size_profile_combo = ttk.Combobox(
            design_row,
            state="readonly",
            width=10,
            values=[FONT_SIZE_PROFILE_LABELS[key] for key in FONT_SIZE_PROFILE_ORDER],
        )
        self.font_size_profile_combo.pack(side="left", padx=(8, 0))
        self._sync_font_size_profile_combo()
        self.font_size_profile_combo.bind("<<ComboboxSelected>>", self._on_font_size_profile_selected)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))

        actions_left = ttk.Frame(actions)
        actions_left.pack(side="left", fill="x", expand=True)

        self.prev_btn = ttk.Button(actions_left, text="◀", command=self.prev_page, width=5, style="NavAction.TButton")
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(actions_left, text="▶", command=self.next_page, width=5, style="NavAction.TButton")
        self.next_btn.pack(side="left", padx=(8, 0))

        ttk.Separator(actions_left, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Button(actions_left, text="-", command=lambda: self.change_zoom(-10), width=3, style="SecondaryAction.TButton").pack(side="left")
        ttk.Button(actions_left, text="+", command=lambda: self.change_zoom(10), width=3, style="SecondaryAction.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(actions_left, text="100%", command=self.reset_zoom, style="SecondaryAction.TButton").pack(side="left", padx=(8, 0))

        ttk.Separator(actions_left, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Button(actions_left, text="Aktualisieren", command=self.refresh_preview, style="UtilityAction.TButton").pack(side="left")
        ttk.Button(actions_left, text="Beenden", command=self.root.destroy, style="UtilityAction.TButton").pack(side="left", padx=(8, 0))

        self.export_btn = ttk.Button(
            actions,
            text="Exportieren…",
            style="PrimaryAction.TButton",
            command=self.open_export_dialog,
        )
        self.export_btn.pack(side="right")

        info_row = ttk.Frame(outer)
        info_row.pack(fill="x", pady=(0, 8))
        ttk.Label(info_row, textvariable=self.page_info_var).pack(side="left")
        ttk.Label(info_row, textvariable=self.zoom_info_var).pack(side="left", padx=(14, 0))
        self.status_label = ttk.Label(info_row, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="right")

        self.editor_preview_paned = tk.PanedWindow(
            outer,
            orient="horizontal",
            sashwidth=6,
            sashrelief="raised",
            opaqueresize=True,
            bd=0,
        )
        self.editor_preview_paned.pack(fill="both", expand=True)

        self.editor_container = ttk.Frame(self.editor_preview_paned, relief="solid", borderwidth=1)
        self.preview_container = ttk.Frame(self.editor_preview_paned, relief="solid", borderwidth=1)

        self._build_editor_panel(self.editor_container)

        theme = get_theme(self.theme_var.get())
        self.preview_canvas = tk.Canvas(self.preview_container, background=theme["bg_main"], highlightthickness=0)
        self.preview_canvas.pack(side="left", fill="both", expand=True)

        v_scroll = ttk.Scrollbar(self.preview_container, orient="vertical", command=self.preview_canvas.yview)
        v_scroll.pack(side="right", fill="y")
        self.preview_h_scroll = ttk.Scrollbar(outer, orient="horizontal", command=self.preview_canvas.xview)

        self.preview_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=self.preview_h_scroll.set)
        v_scroll.configure(command=self._on_vertical_scrollbar)
        self.preview_h_scroll.configure(command=self._on_horizontal_scrollbar)

        self.preview_text_item = self.preview_canvas.create_text(
            40,
            40,
            anchor="nw",
            text="Noch keine Vorschau geladen.",
            fill=theme["fg_muted"],
            font=("Segoe UI", 11),
        )

        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)
        self.preview_canvas.bind("<Enter>", lambda _event: self.preview_canvas.focus_set())
        self.preview_canvas.bind("<Button-1>", lambda _event: self.preview_canvas.focus_set())
        self.preview_canvas.bind("<MouseWheel>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Shift-MouseWheel>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Control-MouseWheel>", self._on_preview_mousewheel)

        # Linux/X11 Fallbacks
        self.preview_canvas.bind("<Button-4>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Button-5>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Shift-Button-4>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Shift-Button-5>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Control-Button-4>", self._on_preview_mousewheel)
        self.preview_canvas.bind("<Control-Button-5>", self._on_preview_mousewheel)
        self._apply_editor_view_mode()
        self._update_nav_buttons()

    def _on_canvas_resize(self, _event):
        """On canvas resize."""
        if self.preview_images:
            x_view_start = self.preview_canvas.xview()[0]
            y_view_start = self.preview_canvas.yview()[0]
            self._show_current_page(
                reset_scroll=False,
                x_view_start=x_view_start,
                y_view_start=y_view_start,
            )
