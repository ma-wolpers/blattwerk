"""UI construction mixin for the main window and canvas wiring."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import HoverTooltip

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
from ..styles.blatt_styles import FONT_PROFILE_LABELS
from .blatt_ui_build_preview import BlattwerkPreviewBuildMixin


class BlattwerkAppBuildMixin(BlattwerkPreviewBuildMixin):
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

    def _build_ui(self, parent=None):
        """Build ui."""
        _p = parent if parent is not None else self.root
        outer = widgets.Frame(_p, padding=12)
        outer.pack(fill="both", expand=True)

        file_row = widgets.Frame(outer)
        file_row.pack(fill="x", pady=(0, 8))
        widgets.Label(file_row, text="Markdown-Datei:", width=16).pack(side="left")
        widgets.Entry(file_row, textvariable=self.input_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        widgets.Button(file_row, text="Durchsuchen…", command=self.pick_input, style="SecondaryAction.TButton").pack(side="left")

        file_row_actions = widgets.Frame(file_row)
        file_row_actions.pack(side="right")
        widgets.Button(file_row_actions, text="Beenden", command=self.root.destroy, style="UtilityAction.TButton").pack(side="right")
        self.export_btn = widgets.Button(
            file_row_actions,
            text="Exportieren…",
            style="PrimaryAction.TButton",
            command=self.open_export_dialog,
        )
        self.export_btn.pack(side="right", padx=(0, 8))

        area_row = widgets.Frame(outer, style="ControlStrip.TFrame", padding=(8, 6))
        area_row.pack(fill="x", pady=(0, 8))
        widgets.Label(area_row, text="Bereich:", width=10, style="ControlStripLabel.TLabel").pack(side="left", padx=(0, 8))

        segment_group = widgets.Frame(area_row, style="ControlStrip.TFrame")
        segment_group.pack(side="left")
        self._editor_mode_segment_buttons = {
            EDITOR_VIEW_PREVIEW_ONLY: widgets.Button(
                segment_group,
                text="◧",
                width=3,
                style="Segmented.TButton",
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY),
            ),
            EDITOR_VIEW_BOTH: widgets.Button(
                segment_group,
                text="◫",
                width=3,
                style="Segmented.TButton",
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_BOTH),
            ),
            EDITOR_VIEW_EDITOR_ONLY: widgets.Button(
                segment_group,
                text="✎",
                width=3,
                style="Segmented.TButton",
                command=lambda: self._set_editor_view_mode(EDITOR_VIEW_EDITOR_ONLY),
            ),
        }
        _editor_mode_segment_tooltips = {
            EDITOR_VIEW_PREVIEW_ONLY: "Vorschau",
            EDITOR_VIEW_BOTH: "Vorschau + Schreibbereich",
            EDITOR_VIEW_EDITOR_ONLY: "Schreibbereich",
        }
        for mode_key, button in self._editor_mode_segment_buttons.items():
            button.pack(side="left", padx=(0, 6))
            HoverTooltip(button, _editor_mode_segment_tooltips[mode_key])

        widgets.Separator(area_row, orient="vertical", style="ControlStrip.TSeparator").pack(side="left", fill="y", padx=(10, 10))
        widgets.Label(area_row, text="Dokumente:", width=10, style="ControlStripLabel.TLabel").pack(side="left", padx=(0, 8))

        self._build_document_tab_strip(area_row)

        self._refresh_editor_mode_segmented_buttons()
        self.editor_view_mode_var.trace_add("write", lambda *_args: self._refresh_editor_mode_segmented_buttons())

        self.editor_preview_paned = ui.PanedWindow(
            outer,
            orient="horizontal",
            sashwidth=6,
            sashrelief="raised",
            opaqueresize=True,
            bd=0,
        )
        self.editor_preview_paned.pack(fill="both", expand=True)

        self.editor_container = widgets.Frame(self.editor_preview_paned, relief="solid", borderwidth=1)
        self.preview_container = widgets.Frame(self.editor_preview_paned, relief="solid", borderwidth=1)

        self._build_editor_panel(self.editor_container)

        preview_controls = self._build_preview_controls_frame()
        self._build_preview_format_section(preview_controls)
        self._build_preview_design_section(preview_controls)
        self._build_preview_actions_section(preview_controls)
        self._build_preview_canvas_area(preview_controls)

        self._reflow_responsive_sections()
        self._apply_editor_view_mode()
        self._update_nav_buttons()
        self._build_global_status_bar(outer)
        self._apply_preview_controls_collapsed_state()


    def _toggle_preview_controls_collapsed(self):
        """Klappt die Vorschau-Knopfleiste ein oder aus."""

        self.preview_controls_collapsed_var.set(not self.preview_controls_collapsed_var.get())
        self._apply_preview_controls_collapsed_state()
        self._save_ui_settings()

    def _apply_preview_controls_collapsed_state(self):
        """Zeigt oder verbirgt die Vorschau-Knopfleiste je nach Toggle-Zustand."""

        if self._preview_controls_frame is None or self.preview_controls_toggle_btn is None:
            return

        collapsed = bool(self.preview_controls_collapsed_var.get())
        if collapsed:
            self._preview_controls_frame.pack_forget()
        else:
            self._preview_controls_frame.pack(fill="x", before=self._preview_controls_after_anchor)
        self.preview_controls_toggle_btn.configure(text="▸" if collapsed else "▾")

    def _build_global_status_bar(self, parent):
        """Creates the global status line below the editor/preview paned area, spanning both."""

        status_bar = widgets.Frame(parent, style="ControlStrip.TFrame", padding=(8, 4))
        status_bar.pack(fill="x", pady=(6, 0))
        self.status_label = widgets.Label(status_bar, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="left")

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
            if group in self._responsive_hidden_groups:
                continue
            group.grid(row=0, column=index, sticky="w", padx=(gap_px, 0))

        self._responsive_sections.append(section)
        container.bind("<Configure>", lambda _event, s=section: self._reflow_responsive_section(s))

    def _set_responsive_group_hidden(self, group, hidden: bool) -> None:
        """Permanently hides/shows a responsive-section group across resize reflows.

        A plain `grid_forget()` isn't enough here -- `_reflow_responsive_section`
        re-grids every registered group unconditionally on each `<Configure>`
        event, so a hidden group would reappear on the next window resize.
        """

        if hidden:
            self._responsive_hidden_groups.add(group)
            group.grid_forget()
        else:
            self._responsive_hidden_groups.discard(group)
        self._reflow_responsive_sections()

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

        visible_groups = [group for group in optional_groups if group not in self._responsive_hidden_groups]

        if not bool(getattr(self, "_responsive_controls_wrap_enabled", True)):
            for index, group in enumerate(visible_groups, start=1):
                group.grid(row=0, column=index, sticky="w", padx=(gap_px, 0), pady=(0, 0))
            return

        current_row = 0
        current_col = 1
        used_width = main_group.winfo_reqwidth()

        for group in visible_groups:
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


