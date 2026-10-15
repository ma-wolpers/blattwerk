"""GUI mixin module."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts.events import EventResult
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.runtime import WindowShortcutBinder, bind_click, bind_wheel, ui, widgets


from .local_keys import bind_actions, scroll_or_zoom
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
        bind_click(canvas, lambda _event: canvas.focus_set())
        bind_wheel(canvas, self._on_help_mousewheel)

        # Fenster-Kürzel (Toplevel-Binder). Pfeile tolerieren Shift wie die früheren
        # rohen Bindungen; die Ziffernblock-Zeichen +/- sind dieselben Specs.
        _k = KeySpec.parse
        bind_actions(
            WindowShortcutBinder(window),
            (
                (_k("Left (tolerate: Shift)"), "prev_page", self._help_prev_page),
                (_k("Right (tolerate: Shift)"), "next_page", self._help_next_page),
                (_k("Up (tolerate: Shift)"), "scroll_up", lambda: self._help_scroll_vertical(-4)),
                (_k("Down (tolerate: Shift)"), "scroll_down", lambda: self._help_scroll_vertical(4)),
                (_k("-"), "zoom_out", lambda: self._help_change_zoom(-10)),
                (_k("+"), "zoom_in", lambda: self._help_change_zoom(10)),
                (_k("0"), "zoom_reset", self._help_reset_zoom),
                (_k("Ctrl+E"), "export", self._open_lernhilfen_export_from_window),
            ),
            text=True,
            prefix="help_preview",
        )

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

    def _help_reset_zoom(self):
        """Resets lernhilfen zoom to 100%."""
        self.help_zoom_percent = 100
        self.help_zoom_info_var.set("Zoom: 100%")
        if self.help_preview_images:
            self._show_help_current_page()

    def _help_prev_page(self):
        """Jumps to the previous lernhilfe card."""
        if not self.help_preview_images or self.help_current_page_index <= 0:
            return
        self._jump_to_help_index(self.help_current_page_index - 1)

    def _help_next_page(self):
        """Jumps to the next lernhilfe card."""
        if (
            not self.help_preview_images
            or self.help_current_page_index >= len(self.help_preview_images) - 1
        ):
            return
        self._jump_to_help_index(self.help_current_page_index + 1)

    def _help_scroll_vertical(self, units: int):
        """Performs vertical canvas scroll in lernhilfen preview."""
        if self.help_preview_canvas is None:
            return
        self.help_preview_canvas.yview_scroll(units, "units")

    def _on_help_mousewheel(self, event):
        """Mausrad über der Lernhilfenvorschau (``WheelEvent``): Strg zoomt, Shift horizontal."""
        if self.help_preview_canvas is not None:
            scroll_or_zoom(event, self.help_preview_canvas, self._help_change_zoom)
        return EventResult.HANDLED
