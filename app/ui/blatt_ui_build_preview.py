"""Builders for the preview-options panel and the preview canvas (BlattwerkAppBuildMixin mixin).

Split out of blatt_ui_build.py (file-size rule): the former 348-line _build_ui now calls
these section builders; their bodies are the unchanged former sections."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import Switch

from .ui_theme import get_theme
from ..styles.blatt_styles import FONT_PROFILE_ORDER, FONT_PROFILE_PRESETS, FONT_SIZE_PROFILE_LABELS, FONT_SIZE_PROFILE_ORDER
from ..styles.worksheet_design import (
    COLOR_PROFILE_ORDER,
    CONTRAST_PROFILE_LABELS,
    CONTRAST_PROFILE_ORDER,
)


class BlattwerkPreviewBuildMixin:
    """Builders for the preview-options panel and the preview canvas (BlattwerkAppBuildMixin mixin)."""

    def _build_preview_controls_frame(self):
        """Build the collapsible preview-options header and return the options frame."""

        preview_controls_header = widgets.Frame(self.preview_container, padding=(8, 4, 8, 0))
        preview_controls_header.pack(fill="x")
        self.preview_controls_toggle_btn = widgets.Button(
            preview_controls_header,
            text="▾",
            width=3,
            style="SecondaryAction.TButton",
            command=self._toggle_preview_controls_collapsed,
        )
        self.preview_controls_toggle_btn.pack(side="left")
        widgets.Label(preview_controls_header, text="Vorschau-Optionen", style="Muted.TLabel").pack(
            side="left", padx=(6, 0)
        )

        preview_controls = widgets.Frame(self.preview_container, padding=8)
        preview_controls.pack(fill="x")
        self._preview_controls_frame = preview_controls

        self._responsive_sections = []
        self._responsive_hidden_groups = set()
        return preview_controls

    def _build_preview_format_section(self, preview_controls):
        """Build the format section (page format, DIN A4/A5, black screen, phases) of the preview options."""

        format_section = widgets.Frame(preview_controls)
        format_section.pack(fill="x", pady=(0, 8))
        format_group_main = widgets.Frame(format_section)
        widgets.Label(format_group_main, text="Format:", width=16).pack(side="left")
        self.preview_mode_btn_worksheet = widgets.Radiobutton(
            format_group_main,
            text="Aufgabe",
            value="worksheet",
            variable=self.preview_mode_var,
            command=self.refresh_preview,
        )
        self.preview_mode_btn_worksheet.pack(side="left")
        self.preview_mode_btn_solution = widgets.Radiobutton(
            format_group_main,
            text="Lösung",
            value="solution",
            variable=self.preview_mode_var,
            command=self.refresh_preview,
        )
        self.preview_mode_btn_solution.pack(side="left", padx=(10, 0))
        self.preview_mode_static_label = widgets.Label(
            format_group_main,
            text="Präsentation",
        )

        format_group_dina = widgets.Frame(format_section)
        widgets.Separator(format_group_dina, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        self.preview_page_format_btn_a4 = widgets.Radiobutton(
            format_group_dina,
            text="DIN A4",
            value="a4_portrait",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        )
        self.preview_page_format_btn_a4.pack(side="left")
        self.preview_page_format_btn_a5 = widgets.Radiobutton(
            format_group_dina,
            text="DIN A5",
            value="a5_landscape",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        )
        self.preview_page_format_btn_a5.pack(side="left", padx=(10, 0))
        self.preview_page_format_btn_16_9 = widgets.Radiobutton(
            format_group_dina,
            text="16:9",
            value="presentation_16_9",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        )
        self.preview_page_format_btn_16_9.pack(side="left", padx=(10, 0))
        self.preview_page_format_btn_16_10 = widgets.Radiobutton(
            format_group_dina,
            text="16:10",
            value="presentation_16_10",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        )
        self.preview_page_format_btn_16_10.pack(side="left", padx=(10, 0))
        self.preview_page_format_btn_4_3 = widgets.Radiobutton(
            format_group_dina,
            text="4:3",
            value="presentation_4_3",
            variable=self.preview_page_format_var,
            command=self.refresh_preview,
        )
        self.preview_page_format_btn_4_3.pack(side="left", padx=(10, 0))

        format_group_black = self.format_group_black = widgets.Frame(format_section)
        widgets.Separator(format_group_black, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Label(format_group_black, text="Black-Screen:").pack(side="left")
        self.preview_black_screen_buttons = []
        for label, value in (
            ("Aus", "none"),
            ("Vorher", "before"),
            ("Nachher", "after"),
            ("Beides", "both"),
        ):
            btn = widgets.Radiobutton(
                format_group_black,
                text=label,
                value=value,
                variable=self.preview_black_screen_var,
                command=self.refresh_preview,
            )
            btn.pack(side="left", padx=(6, 0))
            self.preview_black_screen_buttons.append(btn)

        format_group_phase = self.format_group_phase = widgets.Frame(format_section)
        widgets.Separator(format_group_phase, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Label(format_group_phase, text="Phasen:").pack(side="left")
        self.preview_phase_separator_btn_dot = widgets.Radiobutton(
            format_group_phase,
            text="Punkte",
            value="dot",
            variable=self.preview_section_separator_var,
            command=self.refresh_preview,
        )
        self.preview_phase_separator_btn_dot.pack(side="left", padx=(6, 0))
        self.preview_phase_separator_btn_arrow = widgets.Radiobutton(
            format_group_phase,
            text="Pfeile",
            value="arrow",
            variable=self.preview_section_separator_var,
            command=self.refresh_preview,
        )
        self.preview_phase_separator_btn_arrow.pack(side="left", padx=(6, 0))
        self.preview_phase_hide_future_check = Switch(
            format_group_phase,
            text="Zukunft ausblenden",
            variable=self.preview_hide_future_sections_var,
            on_change=lambda _hide: self.refresh_preview(),
        )
        self.preview_phase_hide_future_check.pack(side="left", padx=(10, 0))

        self._register_responsive_section(
            container=format_section,
            main_group=format_group_main,
            optional_groups=[format_group_dina, format_group_black, format_group_phase],
            indent_px=16,
            gap_px=12,
        )

    def _build_preview_design_section(self, preview_controls):
        """Build the design section (contrast, colors, font profiles) of the preview options."""

        design_section = self.design_section = widgets.Frame(preview_controls)
        design_section.pack(fill="x", pady=(0, 8))
        design_group_main = widgets.Frame(design_section)
        widgets.Label(design_group_main, text="Gestaltung:", width=16).pack(side="left")
        widgets.Label(design_group_main, text="Kontrast:").pack(side="left")
        for contrast_key in CONTRAST_PROFILE_ORDER:
            widgets.Radiobutton(
                design_group_main,
                text=CONTRAST_PROFILE_LABELS[contrast_key],
                value=contrast_key,
                variable=self.preview_contrast_var,
                command=self.refresh_preview,
            ).pack(side="left", padx=(8, 0))

        design_group_color = widgets.Frame(design_section)
        widgets.Separator(design_group_color, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Label(design_group_color, text="Farbprofil:").pack(side="left")
        for profile_key in COLOR_PROFILE_ORDER:
            swatch = ui.Canvas(
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

        design_group_font = widgets.Frame(design_section)
        widgets.Separator(design_group_font, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Label(design_group_font, text="Schrift: ").pack(side="left")
        self.font_profile_menubutton = widgets.Menubutton(design_group_font, width=14)
        font_profile_menu = ui.Menu(self.font_profile_menubutton, tearoff=False)
        for key in FONT_PROFILE_ORDER:
            profile = FONT_PROFILE_PRESETS[key]
            font_profile_menu.add_radiobutton(
                label=profile["label"],
                value=key,
                variable=self._font_profile_menu_var,
                font=(profile["tk_family"], 11),
                command=lambda k=key: self._set_font_profile(k),
            )
        self.font_profile_menubutton.configure(menu=font_profile_menu)
        self.font_profile_menubutton.pack(side="left", padx=(8, 0))
        self._sync_font_profile_combo()

        widgets.Label(design_group_font, text="Größe:").pack(side="left", padx=(12, 0))
        self.font_size_profile_combo = widgets.Combobox(
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

    def _build_preview_actions_section(self, preview_controls):
        """Build the actions section (zoom, refresh, learning aids) of the preview options."""

        actions_section = self.actions_section = widgets.Frame(preview_controls)
        actions_section.pack(fill="x", pady=(0, 8))

        actions_group_main = widgets.Frame(actions_section)
        widgets.Label(actions_group_main, text="Vorschau:", width=16).pack(side="left")
        self.prev_btn = widgets.Button(actions_group_main, text="◀", command=self.prev_page, width=5, style="NavAction.TButton")
        self.prev_btn.pack(side="left")
        self.next_btn = widgets.Button(actions_group_main, text="▶", command=self.next_page, width=5, style="NavAction.TButton")
        self.next_btn.pack(side="left", padx=(8, 0))

        actions_group_zoom = widgets.Frame(actions_section)
        widgets.Separator(actions_group_zoom, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Button(actions_group_zoom, text="-", command=lambda: self.change_zoom(-10), width=3, style="SecondaryAction.TButton").pack(side="left")
        widgets.Button(actions_group_zoom, text="+", command=lambda: self.change_zoom(10), width=3, style="SecondaryAction.TButton").pack(side="left", padx=(8, 0))
        widgets.Button(actions_group_zoom, text="100%", command=self.reset_zoom, style="SecondaryAction.TButton").pack(side="left", padx=(8, 0))

        actions_group_refresh = widgets.Frame(actions_section)
        widgets.Separator(actions_group_refresh, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Button(actions_group_refresh, text="Aktualisieren", command=self._compile_now, style="UtilityAction.TButton").pack(side="left")

        actions_group_lernhilfen = widgets.Frame(actions_section)
        widgets.Separator(actions_group_lernhilfen, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        self.lernhilfen_action_btn = widgets.Button(
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

    def _build_preview_canvas_area(self, preview_controls):
        """Build the info row, the preview canvas with scrollbars and its mouse bindings."""

        info_row = widgets.Frame(preview_controls)
        info_row.pack(fill="x", pady=(0, 8))
        widgets.Label(info_row, textvariable=self.page_info_var).pack(side="left")
        widgets.Label(info_row, textvariable=self.zoom_info_var).pack(side="left", padx=(14, 0))

        self._preview_controls_after_anchor = widgets.Separator(self.preview_container, orient="horizontal")
        self._preview_controls_after_anchor.pack(fill="x")

        preview_canvas_frame = widgets.Frame(self.preview_container)
        preview_canvas_frame.pack(fill="both", expand=True)
        if hasattr(self, "_build_migration_bar"):
            self._build_migration_bar(self.preview_container, before=preview_canvas_frame)

        theme = get_theme(self.theme_var.get())
        self.preview_canvas = ui.Canvas(preview_canvas_frame, background=theme["bg_main"], highlightthickness=0)
        self.preview_canvas.pack(side="left", fill="both", expand=True)

        v_scroll = widgets.Scrollbar(preview_canvas_frame, orient="vertical", command=self.preview_canvas.yview)
        v_scroll.pack(side="right", fill="y")
        self.preview_h_scroll = widgets.Scrollbar(self.preview_container, orient="horizontal", command=self.preview_canvas.xview)
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
