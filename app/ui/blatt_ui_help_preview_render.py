"""Lernhilfenvorschau: Seiten rendern, einpassen, anzeigen und neu aufbauen (BlattwerkApp-Mixin).

Aus ``blatt_ui_help_preview.py`` ausgelagert (300-Zeilen-Regel), Methoden unverändert."""

from __future__ import annotations

from pathlib import Path
import tempfile
import fitz
from PIL import Image, ImageTk

from .dialog_services import messagebox
from .ui_constants import PREVIEW_CANVAS_PADDING_PX, PREVIEW_MIN_FRAME_PX, PREVIEW_SCALE_MAX, PREVIEW_SCALE_MIN
from .preview_geometry import get_fit_scales, get_preview_frame_size, get_zoom_target_size
from .help_card_image_trim import trim_lernhilfe_image
from ..core.build_requests import HelpCardsBuildRequest, build_help_cards_from_request


class BlattwerkAppHelpPreviewRenderMixin:
    """Lernhilfenvorschau: Seiten rendern, einpassen, anzeigen und neu aufbauen (BlattwerkApp-Mixin)."""

    def _render_help_pdf_pages(
        self,
        input_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
    ):
        """Renders lernhilfen pages as trimmed PIL images."""
        worksheet_design = self._worksheet_design_options()
        metadata_defaults = {}
        if hasattr(self, "_metadata_defaults_from_preferences"):
            metadata_defaults = self._metadata_defaults_from_preferences()
        copyright_override = None
        if hasattr(self, "_copyright_text_from_preferences"):
            copyright_override = self._copyright_text_from_preferences() or None
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            temp_pdf_path = Path(tmp.name)

        try:
            build_help_cards_from_request(
                HelpCardsBuildRequest(
                    input_path=input_path,
                    output_path=temp_pdf_path,
                    include_solutions=include_solutions,
                    page_format=page_format,
                    print_profile=contrast_profile,
                    design=worksheet_design,
                    add_running_elements=False,
                    block_on_critical=False,
                    metadata_defaults=metadata_defaults,
                    copyright_text_override=copyright_override,
                )
            )

            pages = []
            with fitz.open(temp_pdf_path) as doc:
                for page_index in range(len(doc)):
                    page = doc.load_page(page_index)
                    pix = page.get_pixmap(dpi=150, alpha=False)
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    pages.append(trim_lernhilfe_image(image))
            return pages
        finally:
            try:
                temp_pdf_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _help_get_fit_scale(self, image: Image.Image):
        """Calculates width-based fit scale for lernhilfen preview."""
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
        """Fits one lernhilfe image to preview width and current zoom."""
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
        """Clears existing canvas image items for lernhilfen preview."""
        if self.help_preview_canvas is None:
            return

        for item_id in self._help_preview_image_items:
            self.help_preview_canvas.delete(item_id)
        self._help_preview_image_items = []
        self._help_tk_preview_images = []

    def _jump_to_help_index(self, index: int):
        """Jumps the scroll position to a specific lernhilfe index."""
        if self.help_preview_canvas is None or not self._help_card_y_offsets:
            return

        index = max(0, min(index, len(self._help_card_y_offsets) - 1))
        self.help_current_page_index = index
        total_height = max(1, int(self._help_stacked_image_size[1]))
        y_offset = int(self._help_card_y_offsets[index])
        normalized = max(0.0, min(1.0, y_offset / total_height))
        self.help_preview_canvas.yview_moveto(normalized)
        self.help_page_info_var.set(
            f"Lernhilfe {self.help_current_page_index + 1}/{len(self.help_preview_images)}"
        )
        self._update_help_nav_buttons()

    def _show_help_current_page(self):
        """Shows all lernhilfen stacked vertically in one scrollable canvas."""
        if self.help_preview_canvas is None or self.help_preview_text_item is None:
            return

        if not self.help_preview_images:
            self._clear_help_preview_image_items()
            self._help_card_y_offsets = []
            self._help_stacked_image_size = (0, 0)
            self.help_preview_canvas.itemconfig(
                self.help_preview_text_item, text="Keine Lernhilfen erkannt."
            )
            self.help_preview_canvas.coords(self.help_preview_text_item, 20, 20)
            self.help_preview_canvas.config(scrollregion=(0, 0, 520, 360))
            self.help_page_info_var.set("Lernhilfe 0/0")
            self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")
            self._update_help_nav_buttons()
            return

        self.help_current_page_index = max(
            0, min(self.help_current_page_index, len(self.help_preview_images) - 1)
        )

        fitted_cards = [self._fit_help_image_for_preview(page) for page in self.help_preview_images]
        gap = 18
        max_width = max(card.width for card in fitted_cards)
        total_height = sum(card.height for card in fitted_cards) + max(0, len(fitted_cards) - 1) * gap

        stacked = Image.new("RGB", (max_width, total_height), "white")
        offsets = []
        current_y = 0
        for card in fitted_cards:
            offsets.append(current_y)
            x_offset = max(0, (max_width - card.width) // 2)
            stacked.paste(card, (x_offset, current_y))
            current_y += card.height + gap

        self._clear_help_preview_image_items()
        tk_image = ImageTk.PhotoImage(stacked)
        item_id = self.help_preview_canvas.create_image(
            0, 0, anchor="nw", image=tk_image
        )
        self._help_tk_preview_images = [tk_image]
        self._help_preview_image_items = [item_id]
        self._help_card_y_offsets = offsets
        self._help_stacked_image_size = (stacked.width, stacked.height)

        self.help_preview_canvas.itemconfig(self.help_preview_text_item, text="")
        self.help_preview_canvas.config(
            scrollregion=(0, 0, stacked.width, stacked.height)
        )
        self.help_preview_canvas.xview_moveto(0)

        self.help_zoom_info_var.set(f"Zoom: {int(round(self.help_zoom_percent))}%")
        self._jump_to_help_index(self.help_current_page_index)

    def _update_help_nav_buttons(self):
        """Updates card-jump navigation button state."""
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

    def _refresh_help_preview(
        self,
        input_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
    ):
        """Refreshes lernhilfen preview content."""
        expected_count = None
        if hasattr(self, "_count_visible_lernhilfen"):
            try:
                expected_count = self._count_visible_lernhilfen(
                    input_path,
                    include_solutions=include_solutions,
                )
            except Exception:
                expected_count = None

        try:
            pages = self._render_help_pdf_pages(
                input_path, include_solutions, page_format, contrast_profile
            )
        except ValueError as error:
            if expected_count == 0:
                pages = []
            else:
                self.status_var.set("Lernhilfen-Vorschau fehlgeschlagen")
                if self.help_preview_canvas is not None and self.help_preview_text_item is not None:
                    self.help_preview_canvas.itemconfig(
                        self.help_preview_text_item,
                        text="Lernhilfen konnten nicht geladen werden.",
                    )
                messagebox.showerror(
                    "Lernhilfen-Vorschau",
                    f"Lernhilfen konnten nicht geladen werden:\n{error}",
                )
                return
        except Exception as error:
            self.status_var.set("Lernhilfen-Vorschau fehlgeschlagen")
            if self.help_preview_canvas is not None and self.help_preview_text_item is not None:
                self.help_preview_canvas.itemconfig(
                    self.help_preview_text_item,
                    text="Lernhilfen konnten nicht geladen werden.",
                )
            messagebox.showerror(
                "Lernhilfen-Vorschau",
                f"Lernhilfen konnten nicht geladen werden:\n{error}",
            )
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
