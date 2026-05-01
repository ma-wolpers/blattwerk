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
    def _refresh_editor_mode_segmented_buttons(self):
        """Updates segmented area buttons so the active view mode is visually highlighted."""

        buttons = getattr(self, "_editor_mode_segment_buttons", {})
        if not buttons:
            return

        active_mode = self.editor_view_mode_var.get()
        for mode, button in buttons.items():
            style_name = "SegmentedActive.TButton" if mode == active_mode else "Segmented.TButton"
            button.configure(style=style_name)

    def _build_ui(self):
        """Build ui."""
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        file_row = ttk.Frame(outer)
        file_row.pack(fill="x", pady=(0, 8))
        ttk.Label(file_row, text="Markdown-Datei:", width=16).pack(side="left")
        ttk.Entry(file_row, textvariable=self.input_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(file_row, text="Durchsuchen…", command=self.pick_input, style="SecondaryAction.TButton").pack(side="left")

        file_row_actions = ttk.Frame(file_row)
        file_row_actions.pack(side="right")
        ttk.Button(file_row_actions, text="Beenden", command=self.root.destroy, style="UtilityAction.TButton").pack(side="right")
        self.export_btn = ttk.Button(
            file_row_actions,
            text="Exportieren…",
            style="PrimaryAction.TButton",
            command=self.open_worksheet_export_dialog,
        )
        self.export_btn.pack(side="right", padx=(0, 8))

        area_row = ttk.Frame(outer, style="ControlStrip.TFrame", padding=(8, 6))
        area_row.pack(fill="x", pady=(0, 8))
        ttk.Label(area_row, text="Bereich:", width=10, style="ControlStripLabel.TLabel").pack(side="left", padx=(0, 8))

        segment_group = ttk.Frame(area_row, style="ControlStrip.TFrame")
        segment_group.pack(side="left")
        self._editor_mode_segment_buttons = {
            EDITOR_VIEW_PREVIEW_ONLY: ttk.Button(
                segment_group,
                text="Vorschau",
                style="Segmented.TButton",
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY),
            ),
            EDITOR_VIEW_BOTH: ttk.Button(
                segment_group,
                text="Beides",
                style="Segmented.TButton",
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_BOTH),
            ),
            EDITOR_VIEW_EDITOR_ONLY: ttk.Button(
                segment_group,
                text="Schreibbereich",
                style="Segmented.TButton",
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY),
            ),
        }
        for button in self._editor_mode_segment_buttons.values():
            button.pack(side="left", padx=(0, 6))

        ttk.Separator(area_row, orient="vertical", style="ControlStrip.TSeparator").pack(side="left", fill="y", padx=(10, 10))
        ttk.Label(area_row, text="Dokumente:", width=10, style="ControlStripLabel.TLabel").pack(side="left", padx=(0, 8))

        self.document_notebook = ttk.Notebook(area_row, style="ControlStrip.TNotebook")
        self.document_notebook.pack(side="left", fill="x", expand=True)
        self.document_notebook.bind("<<NotebookTabChanged>>", self._on_document_tab_changed)

        ttk.Button(
            area_row,
            text="×",
            width=3,
            style="SecondaryAction.TButton",
            command=self.close_active_document_tab,
        ).pack(side="left", padx=(8, 0))

        self._refresh_editor_mode_segmented_buttons()
        self.editor_view_mode_var.trace_add("write", lambda *_args: self._refresh_editor_mode_segmented_buttons())

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

        preview_controls = ttk.Frame(self.preview_container, padding=8)
        preview_controls.pack(fill="x")

        self._responsive_sections = []

        format_section = ttk.Frame(preview_controls)
        format_section.pack(fill="x", pady=(0, 8))
        format_group_main = ttk.Frame(format_section)
        ttk.Label(format_group_main, text="Format:", width=16).pack(side="left")
        ttk.Radiobutton(
            format_group_main,
            text="Aufgabe",
            value="worksheet",
            variable=self.preview_mode_var,
            command=self.refresh_preview,
        ).pack(side="left")
        ttk.Radiobutton(
            format_group_main,
            text="Lösung",
            value="solution",
            variable=self.preview_mode_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))

        format_group_dina = ttk.Frame(format_section)
        ttk.Separator(format_group_dina, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        ttk.Radiobutton(
            format_group_dina,
            text="DIN A4",
            value="a4_portrait",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left")
        ttk.Radiobutton(
            format_group_dina,
            text="DIN A5",
            value="a5_landscape",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))
        ttk.Radiobutton(
            format_group_dina,
            text="16:9",
            value="presentation_16_9",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))
        ttk.Radiobutton(
            format_group_dina,
            text="16:10",
            value="presentation_16_10",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))
        ttk.Radiobutton(
            format_group_dina,
            text="4:3",
            value="presentation_4_3",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(10, 0))

        format_group_black = ttk.Frame(format_section)
        ttk.Separator(format_group_black, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(format_group_black, text="Black-Screen:").pack(side="left")
        ttk.Radiobutton(
            format_group_black,
            text="Aus",
            value="none",
            variable=self.preview_black_screen_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(6, 0))
        ttk.Radiobutton(
            format_group_black,
            text="Vorher",
            value="before",
            variable=self.preview_black_screen_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(6, 0))
        ttk.Radiobutton(
            format_group_black,
            text="Nachher",
            value="after",
            variable=self.preview_black_screen_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(6, 0))
        ttk.Radiobutton(
            format_group_black,
            text="Beides",
            value="both",
            variable=self.preview_black_screen_var,
            command=self.refresh_preview,
        ).pack(side="left", padx=(6, 0))

        self._register_responsive_section(
            container=format_section,
            main_group=format_group_main,
            optional_groups=[format_group_dina, format_group_black],
            indent_px=16,
            gap_px=12,
        )

        design_section = ttk.Frame(preview_controls)
        design_section.pack(fill="x", pady=(0, 8))
        design_group_main = ttk.Frame(design_section)
        ttk.Label(design_group_main, text="Gestaltung:", width=16).pack(side="left")
        ttk.Label(design_group_main, text="Kontrast:").pack(side="left")
        for contrast_key in CONTRAST_PROFILE_ORDER:
            ttk.Radiobutton(
                design_group_main,
                text=CONTRAST_PROFILE_LABELS[contrast_key],
                value=contrast_key,
                variable=self.preview_contrast_var,
                command=self.refresh_preview,
            ).pack(side="left", padx=(8, 0))

        design_group_color = ttk.Frame(design_section)
        ttk.Separator(design_group_color, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(design_group_color, text="Farbprofil:").pack(side="left")
        for profile_key in COLOR_PROFILE_ORDER:
            swatch = tk.Canvas(
                design_group_color,
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

        design_group_font = ttk.Frame(design_section)
        ttk.Separator(design_group_font, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(design_group_font, text="Schrift: ").pack(side="left")
        self.font_profile_combo = ttk.Combobox(
            design_group_font,
            state="readonly",
            width=14,
            values=[FONT_PROFILE_LABELS[key] for key in FONT_PROFILE_ORDER],
        )
        self.font_profile_combo.pack(side="left", padx=(8, 0))
        self._sync_font_profile_combo()
        self.font_profile_combo.bind("<<ComboboxSelected>>", self._on_font_profile_selected)

        ttk.Label(design_group_font, text="Größe:").pack(side="left", padx=(12, 0))
        self.font_size_profile_combo = ttk.Combobox(
            design_group_font,
            state="readonly",
            width=10,
            values=[FONT_SIZE_PROFILE_LABELS[key] for key in FONT_SIZE_PROFILE_ORDER],
        )
        self.font_size_profile_combo.pack(side="left", padx=(8, 0))
        self._sync_font_size_profile_combo()
        self.font_size_profile_combo.bind("<<ComboboxSelected>>", self._on_font_size_profile_selected)

        self._register_responsive_section(
            container=design_section,
            main_group=design_group_main,
            optional_groups=[design_group_color, design_group_font],
            indent_px=16,
            gap_px=12,
        )

        actions_section = ttk.Frame(preview_controls)
        actions_section.pack(fill="x", pady=(0, 8))

        actions_group_main = ttk.Frame(actions_section)
        ttk.Label(actions_group_main, text="Vorschau:", width=16).pack(side="left")
        self.prev_btn = ttk.Button(actions_group_main, text="◀", command=self.prev_page, width=5, style="NavAction.TButton")
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(actions_group_main, text="▶", command=self.next_page, width=5, style="NavAction.TButton")
        self.next_btn.pack(side="left", padx=(8, 0))

        actions_group_zoom = ttk.Frame(actions_section)
        ttk.Separator(actions_group_zoom, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        ttk.Button(actions_group_zoom, text="-", command=lambda: self.change_zoom(-10), width=3, style="SecondaryAction.TButton").pack(side="left")
        ttk.Button(actions_group_zoom, text="+", command=lambda: self.change_zoom(10), width=3, style="SecondaryAction.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(actions_group_zoom, text="100%", command=self.reset_zoom, style="SecondaryAction.TButton").pack(side="left", padx=(8, 0))

        actions_group_refresh = ttk.Frame(actions_section)
        ttk.Separator(actions_group_refresh, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        ttk.Button(actions_group_refresh, text="Aktualisieren", command=self.refresh_preview, style="UtilityAction.TButton").pack(side="left")

        actions_group_lernhilfen = ttk.Frame(actions_section)
        ttk.Separator(actions_group_lernhilfen, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        self.lernhilfen_action_btn = ttk.Button(
            actions_group_lernhilfen,
            text="Lernhilfen",
            command=self.open_help_preview_window,
            style="UtilityAction.TButton",
            state="disabled",
        )
        self.lernhilfen_action_btn.pack(side="left")

        self._register_responsive_section(
            container=actions_section,
            main_group=actions_group_main,
            optional_groups=[actions_group_zoom, actions_group_refresh, actions_group_lernhilfen],
            indent_px=16,
            gap_px=12,
        )

        info_row = ttk.Frame(preview_controls)
        info_row.pack(fill="x", pady=(0, 8))
        ttk.Label(info_row, textvariable=self.page_info_var).pack(side="left")
        ttk.Label(info_row, textvariable=self.zoom_info_var).pack(side="left", padx=(14, 0))
        self.status_label = ttk.Label(info_row, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="right")

        ttk.Separator(self.preview_container, orient="horizontal").pack(fill="x")

        preview_canvas_frame = ttk.Frame(self.preview_container)
        preview_canvas_frame.pack(fill="both", expand=True)

        theme = get_theme(self.theme_var.get())
        self.preview_canvas = tk.Canvas(preview_canvas_frame, background=theme["bg_main"], highlightthickness=0)
        self.preview_canvas.pack(side="left", fill="both", expand=True)

        v_scroll = ttk.Scrollbar(preview_canvas_frame, orient="vertical", command=self.preview_canvas.yview)
        v_scroll.pack(side="right", fill="y")
        self.preview_h_scroll = ttk.Scrollbar(self.preview_container, orient="horizontal", command=self.preview_canvas.xview)
        self.preview_h_scroll.pack(fill="x")

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
        self._reflow_responsive_sections()
        self._apply_editor_view_mode()
        self._update_nav_buttons()

    def _register_responsive_section(self, container, main_group, optional_groups, indent_px=16, gap_px=12):
        """Registers a responsive control section with dynamic row wrapping."""

        container.grid_columnconfigure(0, weight=0)
        container.grid_columnconfigure(99, weight=1)

        section = {
            "container": container,
            "main_group": main_group,
            "optional_groups": list(optional_groups),
            "indent_px": int(indent_px),
            "gap_px": int(gap_px),
        }

        main_group.grid(row=0, column=0, sticky="w")
        for index, group in enumerate(optional_groups, start=1):
            group.grid(row=0, column=index, sticky="w", padx=(gap_px, 0))

        self._responsive_sections.append(section)
        container.bind("<Configure>", lambda _event, s=section: self._reflow_responsive_section(s))

    def _reflow_responsive_sections(self):
        """Reflows all responsive sections after UI creation."""

        for section in getattr(self, "_responsive_sections", []):
            self._reflow_responsive_section(section)

    def _reflow_responsive_section(self, section):
        """Places optional control groups across as many rows as needed."""

        container = section["container"]
        main_group = section["main_group"]
        optional_groups = section["optional_groups"]
        indent_px = section["indent_px"]
        gap_px = section["gap_px"]

        available = container.winfo_width()
        if available <= 1:
            return

        main_group.grid_forget()
        for group in optional_groups:
            group.grid_forget()

        main_group.grid(row=0, column=0, sticky="w")

        if not bool(getattr(self, "_responsive_controls_wrap_enabled", True)):
            for index, group in enumerate(optional_groups, start=1):
                group.grid(row=0, column=index, sticky="w", padx=(gap_px, 0), pady=(0, 0))
            return

        current_row = 0
        current_col = 1
        used_width = main_group.winfo_reqwidth()

        for group in optional_groups:
            group_width = group.winfo_reqwidth()
            if current_row == 0:
                pad_left = gap_px
            else:
                pad_left = indent_px if current_col == 0 else gap_px

            next_width = used_width + pad_left + group_width

            # Wrap to a new row when the next group does not fit in the current row.
            if next_width > available and current_col > 0:
                current_row += 1
                current_col = 0
                used_width = 0
                pad_left = indent_px
                next_width = used_width + pad_left + group_width

            group.grid(
                row=current_row,
                column=current_col,
                sticky="w",
                padx=(pad_left, 0),
                pady=(4, 0) if current_row > 0 else (0, 0),
            )
            used_width = next_width
            current_col += 1

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
