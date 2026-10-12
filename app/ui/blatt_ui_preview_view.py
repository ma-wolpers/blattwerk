"""Vorschau-Ansicht: Seitenlayout (einzeln/nebeneinander/untereinander), Zoom, Scrollen
und Seitennavigation auf der Vorschau-Leinwand.
"""

from __future__ import annotations

from PIL import Image, ImageTk
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()

from bw_gui.contracts import NO_MODIFIERS, UNKNOWN_MODIFIERS, modifiers_from_event
from .ui_constants import (
    CUSTOM_FIT_MODE,
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
from .preview_geometry import (
    clamp,
    find_active_page_index,
    get_centered_view_fractions,
    get_preview_frame_size,
    get_zoom_target_size,
    parse_scrollregion,
)
from ..core.document_type_registry import has_slide_layout


class BlattwerkAppPreviewViewMixin:
    """Darstellung und Navigation der gerenderten Vorschauseiten."""


    def _draw_preview_page(self, x_pos: int, y_pos: int, fitted: Image.Image, tk_image: ImageTk.PhotoImage):
            """Draw preview page image without decorative shadow or frame."""
            image_id = self.preview_canvas.create_image(x_pos, y_pos, anchor="nw", image=tk_image)
            return [image_id]


    def _get_preview_frame_size(self):
            """Liefert nutzbare Canvas-Maße mit robusten Mindestwerten."""
            return get_preview_frame_size(
                self.preview_canvas.winfo_width(),
                self.preview_canvas.winfo_height(),
                PREVIEW_CANVAS_PADDING_PX,
                PREVIEW_MIN_FRAME_PX,
            )


    def _fit_image_for_preview(self, image: Image.Image):
            """Skaliert die Seite relativ zur Seitenbreite (100% = Seitenbreite)."""

            source_w, source_h = image.size
            width_fit_scale, _page_fit_scale = self._get_fit_scales(image)
            target_size = get_zoom_target_size(
                source_w,
                source_h,
                width_fit_scale,
                self.zoom_percent,
                PREVIEW_SCALE_MIN,
                PREVIEW_SCALE_MAX,
            )

            if target_size != image.size:
                return image.resize(target_size, Image.Resampling.LANCZOS)
            return image


    def _show_current_page(self, reset_scroll=True, x_view_start=0.0, y_view_start=0.0):
            """Show current page."""
            if not self.preview_images:
                self._clear_preview_image_items()
                self.preview_canvas.itemconfig(self.preview_text_item, text="Keine Seiten verfügbar.")
                self.preview_canvas.coords(self.preview_text_item, 20, 20)
                self.preview_canvas.config(scrollregion=(0, 0, 600, 400))
                self.page_info_var.set("Seite 0/0")
                return

            self._clear_preview_image_items()
            layout_mode = self.preview_layout_mode_var.get()
            if layout_mode == VIEW_LAYOUT_STRIP:
                self._render_strip_layout()
            elif layout_mode == VIEW_LAYOUT_STACK:
                self._render_stack_layout()
            else:
                self._render_single_page_layout()

            self.preview_canvas.itemconfig(self.preview_text_item, text="")
            if reset_scroll:
                if layout_mode in {VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                    self._center_page_in_view(self.current_page_index)
                else:
                    self.preview_canvas.xview_moveto(0)
                    self.preview_canvas.yview_moveto(0)
            else:
                self.preview_canvas.xview_moveto(max(0.0, min(x_view_start, 1.0)))
                self.preview_canvas.yview_moveto(max(0.0, min(y_view_start, 1.0)))

            self._update_current_page_from_viewport_center()
            page_label = (
                "Folie"
                if has_slide_layout(getattr(self, "_current_preview_document_type", None) or "")
                else "Seite"
            )
            self.page_info_var.set(f"{page_label} {self.current_page_index + 1}/{len(self.preview_images)}")
            self._refresh_zoom_label()


    def _clear_preview_image_items(self):
            """Entfernt alle aktuell im Canvas liegenden Seitenbilder."""

            for item_id in self.preview_image_items:
                self.preview_canvas.delete(item_id)
            self.preview_image_items = []
            self._tk_preview_images = []
            self._page_layout_boxes = []


    def _render_single_page_layout(self):
            """Rendert nur die aktuell aktive Seite."""

            page = self.preview_images[self.current_page_index]
            fitted = self._fit_image_for_preview(page)
            tk_image = ImageTk.PhotoImage(fitted)
            item_ids = self._draw_preview_page(0, 0, fitted, tk_image)

            self._tk_preview_images = [tk_image]
            self.preview_image_items = item_ids
            self._page_layout_boxes = [(0, 0, fitted.width, fitted.height)]
            self.preview_canvas.config(scrollregion=(0, 0, fitted.width, fitted.height))


    def _render_strip_layout(self):
            """Rendert alle Seiten nebeneinander als horizontales Seitenband."""

            x_cursor = PREVIEW_PAGE_MARGIN_PX
            y_top = PREVIEW_PAGE_MARGIN_PX
            max_height = 0

            tk_images = []
            image_items = []
            boxes = []

            for page in self.preview_images:
                fitted = self._fit_image_for_preview(page)
                tk_image = ImageTk.PhotoImage(fitted)
                item_ids = self._draw_preview_page(x_cursor, y_top, fitted, tk_image)

                tk_images.append(tk_image)
                image_items.extend(item_ids)
                boxes.append((x_cursor, y_top, x_cursor + fitted.width, y_top + fitted.height))

                x_cursor += fitted.width + PREVIEW_PAGE_GAP_PX
                max_height = max(max_height, fitted.height)

            total_width = max(PREVIEW_MIN_FRAME_PX, x_cursor - PREVIEW_PAGE_GAP_PX + PREVIEW_PAGE_MARGIN_PX)
            total_height = max(PREVIEW_MIN_FRAME_PX, max_height + 2 * PREVIEW_PAGE_MARGIN_PX)

            self._tk_preview_images = tk_images
            self.preview_image_items = image_items
            self._page_layout_boxes = boxes
            self.preview_canvas.config(scrollregion=(0, 0, total_width, total_height))


    def _render_stack_layout(self):
            """Rendert alle Seiten untereinander als vertikales Seitenband."""

            x_left = PREVIEW_PAGE_MARGIN_PX
            y_cursor = PREVIEW_PAGE_MARGIN_PX
            max_width = 0

            tk_images = []
            image_items = []
            boxes = []

            for page in self.preview_images:
                fitted = self._fit_image_for_preview(page)
                tk_image = ImageTk.PhotoImage(fitted)
                item_ids = self._draw_preview_page(x_left, y_cursor, fitted, tk_image)

                tk_images.append(tk_image)
                image_items.extend(item_ids)
                boxes.append((x_left, y_cursor, x_left + fitted.width, y_cursor + fitted.height))

                y_cursor += fitted.height + PREVIEW_PAGE_GAP_PX
                max_width = max(max_width, fitted.width)

            total_width = max(PREVIEW_MIN_FRAME_PX, max_width + 2 * PREVIEW_PAGE_MARGIN_PX)
            total_height = max(PREVIEW_MIN_FRAME_PX, y_cursor - PREVIEW_PAGE_GAP_PX + PREVIEW_PAGE_MARGIN_PX)

            self._tk_preview_images = tk_images
            self.preview_image_items = image_items
            self._page_layout_boxes = boxes
            self.preview_canvas.config(scrollregion=(0, 0, total_width, total_height))


    def _center_page_in_view(self, page_index):
            """Zentriert eine Seite im sichtbaren Canvas-Bereich."""

            if not self._page_layout_boxes:
                return

            safe_index = max(0, min(page_index, len(self._page_layout_boxes) - 1))
            canvas_width = max(1, self.preview_canvas.winfo_width())
            canvas_height = max(1, self.preview_canvas.winfo_height())
            page_box = self._page_layout_boxes[safe_index]
            x_fraction, y_fraction = get_centered_view_fractions(
                page_box,
                canvas_width,
                canvas_height,
                self._get_scrollregion_bounds(),
            )
            self.preview_canvas.xview_moveto(x_fraction)
            self.preview_canvas.yview_moveto(y_fraction)


    def _get_scrollregion_bounds(self):
            """Liest die aktuell gesetzte Scrollregion robust als Float-Tupel."""
            return parse_scrollregion(self.preview_canvas.cget("scrollregion"))


    def _update_current_page_from_viewport_center(self):
            """Ermittelt in Mehrseitenansicht die aktive Seite aus der View-Mitte."""

            layout_mode = self.preview_layout_mode_var.get()
            if layout_mode not in {VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                return
            if not self._page_layout_boxes:
                return

            viewport_center_x = self.preview_canvas.canvasx(max(1, self.preview_canvas.winfo_width()) / 2)
            viewport_center_y = self.preview_canvas.canvasy(max(1, self.preview_canvas.winfo_height()) / 2)

            best_index = find_active_page_index(
                "strip" if layout_mode == VIEW_LAYOUT_STRIP else "stack",
                self._page_layout_boxes,
                viewport_center_x,
                viewport_center_y,
                self.current_page_index,
            )

            if best_index != self.current_page_index:
                self.current_page_index = best_index
                self.page_info_var.set(f"Seite {self.current_page_index + 1}/{len(self.preview_images)}")
                self._update_nav_buttons()


    def _sync_current_page_ui(self):
            """Synchronisiert Seitenanzeige, Zoomlabel und Navigationsstatus."""

            self.page_info_var.set(f"Seite {self.current_page_index + 1}/{len(self.preview_images)}")
            self._refresh_zoom_label()
            self._update_nav_buttons()


    def _on_vertical_scrollbar(self, *args):
            """Leitet Scrollbar-Scroll weiter und aktualisiert aktive Seite."""

            self.preview_canvas.yview(*args)
            self._update_current_page_from_viewport_center()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()


    def _on_horizontal_scrollbar(self, *args):
            """Leitet Scrollbar-Scroll weiter und aktualisiert aktive Seite."""

            self.preview_canvas.xview(*args)
            self._update_current_page_from_viewport_center()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()


    def _update_nav_buttons(self):
            """Update nav buttons."""
            has_pages = bool(self.preview_images)
            has_prev = has_pages and self.current_page_index > 0
            has_next = has_pages and self.current_page_index < len(self.preview_images) - 1

            self.prev_btn.config(state="normal" if has_prev else "disabled")
            self.next_btn.config(state="normal" if has_next else "disabled")


    def change_zoom(self, delta):
            """Ändert den Vorschau-Zoom in 10%-Schritten."""

            self.zoom_percent = clamp(self.zoom_percent + delta, PREVIEW_ZOOM_MIN_PERCENT, PREVIEW_ZOOM_MAX_PERCENT)
            self.preview_fit_mode_var.set(CUSTOM_FIT_MODE)
            self._refresh_zoom_label()
            if self.preview_images:
                self._show_current_page()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()


    @staticmethod
    def _wheel_direction(event):
            """Liefert +1 für Rad hoch und -1 für Rad runter (plattformübergreifend)."""

            if getattr(event, "num", None) == 4:
                return 1
            if getattr(event, "num", None) == 5:
                return -1

            delta = getattr(event, "delta", 0)
            if delta > 0:
                return 1
            if delta < 0:
                return -1
            return 0


    def _on_preview_mousewheel(self, event):
            """Mausrad: Strg=Zoom, Shift=horizontal scroll, sonst vertikal scroll."""

            direction = self._wheel_direction(event)
            if direction == 0:
                return "break"

            # Modifier-Semantik aus dem bw-gui-Contract (kein eigenes event.state-Bitraten).
            # Unbekannter Zustand -> normales Scrollen (beim Mausrad der harmlose Fall).
            modifiers = modifiers_from_event(event)
            if modifiers is UNKNOWN_MODIFIERS:
                modifiers = NO_MODIFIERS
            shift_pressed = modifiers.shift
            control_pressed = modifiers.control

            if control_pressed:
                self.change_zoom(10 if direction > 0 else -10)
                return "break"

            scroll_units = -direction
            if shift_pressed:
                self.preview_canvas.xview_scroll(scroll_units, "units")
            else:
                self.preview_canvas.yview_scroll(scroll_units, "units")

            self._update_current_page_from_viewport_center()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()

            return "break"


    def reset_zoom(self):
            """Setzt den Vorschau-Zoom auf 100%."""

            self.zoom_percent = 100
            self._refresh_zoom_label()
            if self.preview_images:
                self._show_current_page()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()


    def prev_page(self):
            """Prev page."""
            if not self.preview_images or self.current_page_index <= 0:
                return
            self.current_page_index -= 1
            if self.preview_layout_mode_var.get() in {VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                self._center_page_in_view(self.current_page_index)
                self._sync_current_page_ui()
            else:
                self._show_current_page()
                self._update_nav_buttons()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()


    def next_page(self):
            """Next page."""
            if not self.preview_images or self.current_page_index >= len(self.preview_images) - 1:
                return
            self.current_page_index += 1
            if self.preview_layout_mode_var.get() in {VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                self._center_page_in_view(self.current_page_index)
                self._sync_current_page_ui()
            else:
                self._show_current_page()
                self._update_nav_buttons()
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()
