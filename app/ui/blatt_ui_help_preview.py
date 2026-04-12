"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
import tempfile
import fitz
from PIL import Image, ImageTk
from .blatt_ui_dependencies import (
    PREVIEW_CANVAS_PADDING_PX,
    PREVIEW_MIN_FRAME_PX,
    PREVIEW_SCALE_MAX,
    PREVIEW_SCALE_MIN,
    PREVIEW_ZOOM_MAX_PERCENT,
    PREVIEW_ZOOM_MIN_PERCENT,
    build_help_cards,
    clamp,
    get_fit_scales,
    get_preview_frame_size,
    get_theme,
    get_zoom_target_size,
    ttk,
    tk,
)


class BlattwerkAppHelpPreviewMixin:
    """Erzeugt und steuert das separate Vorschaufenster für Hilfekarten."""

    def _ensure_help_preview_window(self):
        """Ensure help preview window."""
        if (
            self.help_preview_window is not None
            and self.help_preview_window.winfo_exists()
        ):
            return

        window = tk.Toplevel(self.root)
        window.title("Hilfeblöcke Vorschau")
        window.geometry("640x520")
        window.minsize(420, 340)
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._close_help_preview_window)

        outer = ttk.Frame(window, padding=10)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Hilfeblöcke", font=("Segoe UI", 11, "bold")).pack(
            anchor="w"
        )

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(8, 6))

        self.help_prev_btn = ttk.Button(
            actions,
            text="◀",
            command=self._help_prev_page,
            width=5,
            style="NavAction.TButton",
        )
        self.help_prev_btn.pack(side="left")
        self.help_next_btn = ttk.Button(
            actions,
            text="▶",
            command=self._help_next_page,
            width=5,
            style="NavAction.TButton",
        )
        self.help_next_btn.pack(side="left", padx=(8, 0))

        ttk.Separator(actions, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Button(
            actions,
            text="-",
            command=lambda: self._help_change_zoom(-10),
            width=3,
            style="SecondaryAction.TButton",
        ).pack(side="left")
        ttk.Button(
            actions,
            text="+",
            command=lambda: self._help_change_zoom(10),
            width=3,
            style="SecondaryAction.TButton",
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            actions,
            text="100%",
            command=self._help_reset_zoom,
            style="SecondaryAction.TButton",
        ).pack(side="left", padx=(8, 0))

        info_row = ttk.Frame(outer)
        info_row.pack(fill="x", pady=(0, 6))
        ttk.Label(info_row, textvariable=self.help_page_info_var).pack(side="left")
        ttk.Label(info_row, textvariable=self.help_zoom_info_var).pack(
            side="left", padx=(14, 0)
        )

        preview_frame = ttk.Frame(outer, relief="solid", borderwidth=1)
        preview_frame.pack(fill="both", expand=True)

        theme = get_theme(self.theme_var.get())
        canvas = tk.Canvas(
            preview_frame, background=theme["bg_main"], highlightthickness=0
        )
        canvas.pack(side="left", fill="both", expand=True)

        v_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=canvas.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = ttk.Scrollbar(window, orient="horizontal", command=canvas.xview)
        h_scroll.pack(fill="x", padx=10, pady=(0, 10))

        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        text_item = canvas.create_text(
            20,
            20,
            anchor="nw",
            text="Keine Hilfeblöcke erkannt.",
            fill=theme["fg_muted"],
            font=("Segoe UI", 10),
        )

        canvas.bind("<Configure>", self._on_help_canvas_resize)
        canvas.bind("<Enter>", lambda _event: canvas.focus_set())
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

        self.help_preview_window = window
        self.help_preview_canvas = canvas
        self.help_preview_text_item = text_item
        self._help_tk_preview_images = []
        self._help_preview_image_items = []
        self._apply_theme(redraw_preview=False)
        self._update_help_nav_buttons()

    def _close_help_preview_window(self):
        """Close help preview window."""
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
        self.help_page_info_var.set("Hilfe 0/0")
        self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")

    def _on_help_canvas_resize(self, _event):
        """On help canvas resize."""
        if self.help_preview_images:
            self._show_help_current_page()

    def _render_help_pdf_pages(
        self,
        input_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
    ):
        """Render help pdf pages."""
        worksheet_design = self._worksheet_design_kwargs()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            temp_pdf_path = Path(tmp.name)

        try:
            build_help_cards(
                str(input_path),
                str(temp_pdf_path),
                include_solutions=include_solutions,
                page_format=page_format,
                print_profile=contrast_profile,
                **worksheet_design,
            )

            pages = []
            with fitz.open(temp_pdf_path) as doc:
                for page_index in range(len(doc)):
                    page = doc.load_page(page_index)
                    pix = page.get_pixmap(dpi=150, alpha=False)
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    pages.append(image)
            return pages
        finally:
            try:
                temp_pdf_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _help_get_fit_scale(self, image: Image.Image):
        """Help get fit scale."""
        if self.help_preview_canvas is None:
            return 1.0

        frame_width, _frame_height = get_preview_frame_size(
            self.help_preview_canvas.winfo_width(),
            self.help_preview_canvas.winfo_height(),
            PREVIEW_CANVAS_PADDING_PX,
            PREVIEW_MIN_FRAME_PX,
        )
        source_w, source_h = image.size
        width_fit_scale, _page_fit_scale = get_fit_scales(
            frame_width, PREVIEW_MIN_FRAME_PX, source_w, source_h
        )
        return width_fit_scale

    def _fit_help_image_for_preview(self, image: Image.Image):
        """Fit help image for preview."""
        source_w, source_h = image.size
        width_fit_scale = self._help_get_fit_scale(image)
        target_size = get_zoom_target_size(
            source_w,
            source_h,
            width_fit_scale,
            self.help_zoom_percent,
            PREVIEW_SCALE_MIN,
            PREVIEW_SCALE_MAX,
        )
        if target_size != image.size:
            return image.resize(target_size, Image.Resampling.LANCZOS)
        return image

    def _clear_help_preview_image_items(self):
        """Clear help preview image items."""
        if self.help_preview_canvas is None:
            return

        for item_id in self._help_preview_image_items:
            self.help_preview_canvas.delete(item_id)
        self._help_preview_image_items = []
        self._help_tk_preview_images = []

    def _show_help_current_page(self):
        """Show help current page."""
        if self.help_preview_canvas is None or self.help_preview_text_item is None:
            return

        if not self.help_preview_images:
            self._clear_help_preview_image_items()
            self.help_preview_canvas.itemconfig(
                self.help_preview_text_item, text="Keine Hilfeblöcke erkannt."
            )
            self.help_preview_canvas.coords(self.help_preview_text_item, 20, 20)
            self.help_preview_canvas.config(scrollregion=(0, 0, 520, 360))
            self.help_page_info_var.set("Hilfe 0/0")
            self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")
            self._update_help_nav_buttons()
            return

        self.help_current_page_index = max(
            0, min(self.help_current_page_index, len(self.help_preview_images) - 1)
        )
        page = self.help_preview_images[self.help_current_page_index]
        fitted = self._fit_help_image_for_preview(page)

        self._clear_help_preview_image_items()
        tk_image = ImageTk.PhotoImage(fitted)
        item_id = self.help_preview_canvas.create_image(
            0, 0, anchor="nw", image=tk_image
        )
        self._help_tk_preview_images = [tk_image]
        self._help_preview_image_items = [item_id]
        self.help_preview_canvas.itemconfig(self.help_preview_text_item, text="")
        self.help_preview_canvas.config(
            scrollregion=(0, 0, fitted.width, fitted.height)
        )
        self.help_preview_canvas.xview_moveto(0)
        self.help_preview_canvas.yview_moveto(0)

        self.help_page_info_var.set(
            f"Hilfe {self.help_current_page_index + 1}/{len(self.help_preview_images)}"
        )
        self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")
        self._update_help_nav_buttons()

    def _update_help_nav_buttons(self):
        """Update help nav buttons."""
        if not hasattr(self, "help_prev_btn") or not hasattr(self, "help_next_btn"):
            return

        has_pages = bool(self.help_preview_images)
        has_prev = has_pages and self.help_current_page_index > 0
        has_next = (
            has_pages
            and self.help_current_page_index < len(self.help_preview_images) - 1
        )

        self.help_prev_btn.config(state="normal" if has_prev else "disabled")
        self.help_next_btn.config(state="normal" if has_next else "disabled")

    def _help_change_zoom(self, delta):
        """Help change zoom."""
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
        """Help reset zoom."""
        self.help_zoom_percent = 100
        self.help_zoom_info_var.set("Zoom: 100%")
        if self.help_preview_images:
            self._show_help_current_page()
        return "break"

    def _help_prev_page(self):
        """Help prev page."""
        if not self.help_preview_images or self.help_current_page_index <= 0:
            return "break"
        self.help_current_page_index -= 1
        self._show_help_current_page()
        return "break"

    def _help_next_page(self):
        """Help next page."""
        if (
            not self.help_preview_images
            or self.help_current_page_index >= len(self.help_preview_images) - 1
        ):
            return "break"
        self.help_current_page_index += 1
        self._show_help_current_page()
        return "break"

    def _help_scroll_vertical(self, units: int):
        """Help scroll vertical."""
        if self.help_preview_canvas is None:
            return "break"
        self.help_preview_canvas.yview_scroll(units, "units")
        return "break"

    def _on_help_mousewheel(self, event):
        """On help mousewheel."""
        direction = self._wheel_direction(event)
        if direction == 0 or self.help_preview_canvas is None:
            return "break"

        state = getattr(event, "state", 0)
        shift_pressed = bool(state & 0x0001)
        control_pressed = bool(state & 0x0004)

        if control_pressed:
            self._help_change_zoom(10 if direction > 0 else -10)
            return "break"

        scroll_units = -direction
        if shift_pressed:
            self.help_preview_canvas.xview_scroll(scroll_units, "units")
        else:
            self.help_preview_canvas.yview_scroll(scroll_units, "units")

        return "break"

    def _refresh_help_preview(
        self,
        input_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
    ):
        """Refresh help preview."""
        try:
            pages = self._render_help_pdf_pages(
                input_path, include_solutions, page_format, contrast_profile
            )
        except ValueError:
            self._close_help_preview_window()
            return

        self._ensure_help_preview_window()

        preserve_position = self._help_last_preview_input_path == input_path and bool(
            self.help_preview_images
        )
        previous_index = self.help_current_page_index
        self.help_preview_images = pages
        self._help_last_preview_input_path = input_path

        if not self.help_preview_images:
            self.help_current_page_index = 0
        elif preserve_position:
            self.help_current_page_index = min(
                previous_index, len(self.help_preview_images) - 1
            )
        else:
            self.help_current_page_index = 0

        self._show_help_current_page()
        if (
            self.help_preview_window is not None
            and self.help_preview_window.winfo_exists()
        ):
            self.help_preview_window.deiconify()
