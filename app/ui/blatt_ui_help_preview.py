"""GUI mixin module."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts import NO_MODIFIERS, UNKNOWN_MODIFIERS, modifiers_from_event
from bw_gui.runtime import ui, widgets


from .ui_constants import PREVIEW_ZOOM_MAX_PERCENT, PREVIEW_ZOOM_MIN_PERCENT
from .preview_geometry import clamp
from .ui_theme import get_theme
from .blatt_ui_help_preview_render import BlattwerkAppHelpPreviewRenderMixin


class BlattwerkAppHelpPreviewMixin(BlattwerkAppHelpPreviewRenderMixin):
    """Erzeugt und steuert das separate Vorschaufenster für Lernhilfen."""

    def open_help_preview_window(self):
        """Opens the standalone lernhilfen preview window for the current file."""

        input_path = self._validate_input()
        if not input_path:
            return

        include_solutions = self.preview_mode_var.get() == "solution"
        if hasattr(self, "_count_visible_lernhilfen"):
            lernhilfen_count = self._count_visible_lernhilfen(
                input_path,
                include_solutions=include_solutions,
            )
            if lernhilfen_count <= 0:
                if hasattr(self, "_update_lernhilfen_action_state"):
                    self._update_lernhilfen_action_state(
                        input_path=input_path,
                        include_solutions=include_solutions,
                    )
                return

        page_format = self.preview_page_format_var.get()
        contrast_profile = self.preview_contrast_var.get()
        self._ensure_help_preview_window()
        self._refresh_help_preview(
            input_path,
            include_solutions,
            page_format,
            contrast_profile,
        )

    def _open_lernhilfen_export_from_window(self):
        """Opens lernhilfen export from the lernhilfen preview window."""

        if hasattr(self, "open_lernhilfen_export_dialog"):
            self.open_lernhilfen_export_dialog()
        return "break"

    def _ensure_help_preview_window(self):
        """Ensures the lernhilfen preview window exists and is wired."""
        if (
            self.help_preview_window is not None
            and self.help_preview_window.winfo_exists()
        ):
            return

        window = ui.Toplevel(self.root)
        window.title("Lernhilfen Vorschau")
        window.geometry("700x560")
        window.minsize(460, 360)
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._close_help_preview_window)

        outer = widgets.Frame(window, padding=10)
        outer.pack(fill="both", expand=True)

        widgets.Label(outer, text="Lernhilfen", font=("Segoe UI", 11, "bold")).pack(
            anchor="w"
        )

        actions = widgets.Frame(outer)
        actions.pack(fill="x", pady=(8, 6))

        self.help_prev_btn = widgets.Button(
            actions,
            text="◀",
            command=self._help_prev_page,
            width=5,
            style="NavAction.TButton",
        )
        self.help_prev_btn.pack(side="left")
        self.help_next_btn = widgets.Button(
            actions,
            text="▶",
            command=self._help_next_page,
            width=5,
            style="NavAction.TButton",
        )
        self.help_next_btn.pack(side="left", padx=(8, 0))

        widgets.Separator(actions, orient="vertical").pack(side="left", fill="y", padx=12)

        widgets.Button(
            actions,
            text="-",
            command=lambda: self._help_change_zoom(-10),
            width=3,
            style="SecondaryAction.TButton",
        ).pack(side="left")
        widgets.Button(
            actions,
            text="+",
            command=lambda: self._help_change_zoom(10),
            width=3,
            style="SecondaryAction.TButton",
        ).pack(side="left", padx=(8, 0))
        widgets.Button(
            actions,
            text="100%",
            command=self._help_reset_zoom,
            style="SecondaryAction.TButton",
        ).pack(side="left", padx=(8, 0))

        widgets.Separator(actions, orient="vertical").pack(side="left", fill="y", padx=12)
        self.help_export_btn = widgets.Button(
            actions,
            text="Exportieren",
            command=self.open_lernhilfen_export_dialog,
            style="PrimaryAction.TButton",
        )
        self.help_export_btn.pack(side="left")

        info_row = widgets.Frame(outer)
        info_row.pack(fill="x", pady=(0, 6))
        widgets.Label(info_row, textvariable=self.help_page_info_var).pack(side="left")
        widgets.Label(info_row, textvariable=self.help_zoom_info_var).pack(
            side="left", padx=(14, 0)
        )

        preview_frame = widgets.Frame(outer, relief="solid", borderwidth=1)
        preview_frame.pack(fill="both", expand=True)

        theme = get_theme(self.theme_var.get())
        canvas = ui.Canvas(
            preview_frame, background=theme["bg_main"], highlightthickness=0
        )
        canvas.pack(side="left", fill="both", expand=True)

        v_scroll = widgets.Scrollbar(preview_frame, orient="vertical", command=canvas.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = widgets.Scrollbar(window, orient="horizontal", command=canvas.xview)
        h_scroll.pack(fill="x", padx=10, pady=(0, 10))

        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        text_item = canvas.create_text(
            20,
            20,
            anchor="nw",
            text="Keine Lernhilfen erkannt.",
            fill=theme["fg_muted"],
            font=("Segoe UI", 10),
        )

        canvas.bind("<Configure>", self._on_help_canvas_resize)
        canvas.bind("<Button-1>", lambda _event: canvas.focus_set())
        canvas.bind("<MouseWheel>", self._on_help_mousewheel)
        canvas.bind("<Shift-MouseWheel>", self._on_help_mousewheel)
        canvas.bind("<Control-MouseWheel>", self._on_help_mousewheel)
        canvas.bind("<Button-4>", self._on_help_mousewheel)
        canvas.bind("<Button-5>", self._on_help_mousewheel)
        canvas.bind("<Shift-Button-4>", self._on_help_mousewheel)
        canvas.bind("<Shift-Button-5>", self._on_help_mousewheel)
        canvas.bind("<Control-Button-4>", self._on_help_mousewheel)
        canvas.bind("<Control-Button-5>", self._on_help_mousewheel)

        window.bind("<Left>", lambda _event: self._help_prev_page())
        window.bind("<Right>", lambda _event: self._help_next_page())
        window.bind("<Up>", lambda _event: self._help_scroll_vertical(-4))
        window.bind("<Down>", lambda _event: self._help_scroll_vertical(4))
        window.bind("<KeyPress-minus>", lambda _event: self._help_change_zoom(-10))
        window.bind("<KeyPress-plus>", lambda _event: self._help_change_zoom(10))
        window.bind("<KP_Subtract>", lambda _event: self._help_change_zoom(-10))
        window.bind("<KP_Add>", lambda _event: self._help_change_zoom(10))
        window.bind("<KeyPress-0>", lambda _event: self._help_reset_zoom())
        window.bind("<Control-e>", lambda _event: self._open_lernhilfen_export_from_window())

        self.help_preview_window = window
        self.help_preview_canvas = canvas
        self.help_preview_text_item = text_item
        self._help_tk_preview_images = []
        self._help_preview_image_items = []
        self._help_card_y_offsets = []
        self._help_stacked_image_size = (0, 0)
        self._apply_theme(redraw_preview=False)
        self._update_help_nav_buttons()

    def _close_help_preview_window(self):
        """Closes lernhilfen preview window and resets state."""
        if (
            self.help_preview_window is not None
            and self.help_preview_window.winfo_exists()
        ):
            self.help_preview_window.destroy()

        self.help_preview_window = None
        self.help_preview_canvas = None
        self.help_preview_text_item = None
        self.help_preview_images = []
        self.help_current_page_index = 0
        self._help_tk_preview_images = []
        self._help_preview_image_items = []
        self._help_card_y_offsets = []
        self._help_stacked_image_size = (0, 0)
        self.help_page_info_var.set("Lernhilfe 0/0")
        self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")

    def _on_help_canvas_resize(self, _event):
        """Reflows stacked lernhilfen image when canvas size changes."""
        if self.help_preview_images:
            self._show_help_current_page()

    def _help_change_zoom(self, delta):
        """Changes lernhilfen zoom and redraws stack."""
        self.help_zoom_percent = clamp(
            self.help_zoom_percent + delta,
            PREVIEW_ZOOM_MIN_PERCENT,
            PREVIEW_ZOOM_MAX_PERCENT,
        )
        self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")
        if self.help_preview_images:
            self._show_help_current_page()
        return "break"

    def _help_reset_zoom(self):
        """Resets lernhilfen zoom to 100%."""
        self.help_zoom_percent = 100
        self.help_zoom_info_var.set("Zoom: 100%")
        if self.help_preview_images:
            self._show_help_current_page()
        return "break"

    def _help_prev_page(self):
        """Jumps to the previous lernhilfe card."""
        if not self.help_preview_images or self.help_current_page_index <= 0:
            return "break"
        self._jump_to_help_index(self.help_current_page_index - 1)
        return "break"

    def _help_next_page(self):
        """Jumps to the next lernhilfe card."""
        if (
            not self.help_preview_images
            or self.help_current_page_index >= len(self.help_preview_images) - 1
        ):
            return "break"
        self._jump_to_help_index(self.help_current_page_index + 1)
        return "break"

    def _help_scroll_vertical(self, units: int):
        """Performs vertical canvas scroll in lernhilfen preview."""
        if self.help_preview_canvas is None:
            return "break"
        self.help_preview_canvas.yview_scroll(units, "units")
        return "break"

    def _on_help_mousewheel(self, event):
        """Handles mousewheel scrolling and zoom for lernhilfen preview."""
        direction = self._wheel_direction(event)
        if direction == 0 or self.help_preview_canvas is None:
            return "break"

        # Modifier-Semantik aus dem bw-gui-Contract (kein eigenes event.state-Bitraten).
        # Unbekannter Zustand -> normales Scrollen (beim Mausrad der harmlose Fall).
        modifiers = modifiers_from_event(event)
        if modifiers is UNKNOWN_MODIFIERS:
            modifiers = NO_MODIFIERS
        shift_pressed = modifiers.shift
        control_pressed = modifiers.control

        if control_pressed:
            self._help_change_zoom(10 if direction > 0 else -10)
            return "break"

        scroll_units = -direction
        if shift_pressed:
            self.help_preview_canvas.xview_scroll(scroll_units, "units")
        else:
            self.help_preview_canvas.yview_scroll(scroll_units, "units")

        return "break"
