"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
import tempfile
import fitz
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

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
    VIEW_LAYOUT_SINGLE,
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
from ..core.build_requests import WorksheetBuildRequest, build_worksheet_from_request
from ..core.diagnostic_warnings import build_warning_payload
from ..styles.blatt_styles import invalidate_stylesheet_template_cache

class BlattwerkAppPreviewMixin:
    """Rendert, skaliert und navigiert die Arbeitsblatt-Vorschau."""

    @staticmethod
    def _default_markdown_content():
            """Liefert den Standardinhalt für neu erzeugte Markdown-Dateien."""

            return (
                "---\n"
                "Titel: Neues Arbeitsblatt\n"
                "Fach: Fach eintragen\n"
                "Thema: Thema eintragen\n"
                "---\n\n"
                ":::material title=\"Hinweis\"\n"
                "Arbeite sauber und lies jede Aufgabe genau.\n"
                ":::\n\n"
                ":::task points=2 work=single action=read\n"
                "Formuliere hier deine erste Aufgabe.\n"
                ":::\n"
            )

    def create_new_markdown_file(self):
            """Erzeugt eine neue Markdown-Datei über Dateidialog und öffnet sie direkt."""

            dialog_kwargs = {
                "title": "Neue Markdown-Datei anlegen",
                "defaultextension": ".md",
                "filetypes": [("Markdown", "*.md"), ("Alle Dateien", "*.*")],
            }
            initial_dir = self._get_initial_dialog_dir("input_markdown")
            if initial_dir:
                dialog_kwargs["initialdir"] = initial_dir

            selected = filedialog.asksaveasfilename(**dialog_kwargs)
            if not selected:
                return

            target_path = Path(selected)
            if target_path.suffix.lower() != ".md":
                target_path = target_path.with_suffix(".md")

            if target_path.exists():
                messagebox.showerror(
                    "Datei existiert bereits",
                    "Bitte wähle einen neuen Dateinamen, damit keine bestehende Datei überschrieben wird.",
                )
                return

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(self._default_markdown_content(), encoding="utf-8")
            except Exception as error:
                messagebox.showerror("Datei konnte nicht erstellt werden", str(error))
                self.status_var.set("Neue Datei konnte nicht erstellt werden")
                return

            self._set_last_dialog_dir("input_markdown", str(target_path))
            self.status_var.set("Neue Markdown-Datei erstellt")
            self._open_input_path(target_path, add_recent=True)

    def _show_document_diagnostics(self, input_path: Path, context_label: str):
            """Zeigt nicht-blockierende Blattwerk-Warnungen einmalig pro Dokumentzustand."""
            warning_payload = build_warning_payload(input_path, context_label)
            if warning_payload is None:
                return

            signature = warning_payload["signature"]
            if signature == self._last_diagnostics_signature:
                return

            self._last_diagnostics_signature = signature
            if warning_payload["count"] <= 0:
                return

            messagebox.showwarning(
                warning_payload["title"],
                "Das Dokument wurde trotzdem verarbeitet.\n\n" + warning_payload["message"],
            )

    def _draw_preview_page(self, x_pos: int, y_pos: int, fitted: Image.Image, tk_image: ImageTk.PhotoImage):
            """Draw preview page image without decorative shadow or frame."""
            image_id = self.preview_canvas.create_image(x_pos, y_pos, anchor="nw", image=tk_image)
            return [image_id]

    def pick_input(self):
            """Pick input."""
            dialog_kwargs = {
                "title": "Markdown-Datei auswählen",
                "filetypes": [("Markdown", "*.md"), ("Alle Dateien", "*.*")],
            }
            initial_dir = self._get_initial_dialog_dir("input_markdown")
            if initial_dir:
                dialog_kwargs["initialdir"] = initial_dir

            selected = filedialog.askopenfilename(**dialog_kwargs)
            if not selected:
                return

            self._set_last_dialog_dir("input_markdown", selected)
            self._open_input_path(Path(selected), add_recent=True)

    def _validate_input(self):
            """Validate input."""
            input_text = self._clean_path_text(self.input_var.get())
            if not input_text:
                messagebox.showwarning("Fehlende Eingabe", "Bitte wähle eine Markdown-Datei aus.")
                return None

            path = Path(input_text)
            if not path.exists():
                messagebox.showerror("Datei nicht gefunden", f"Die Datei existiert nicht:\n{path}")
                return None

            return path

    def _render_pdf_pages(self, input_path: Path, include_solutions: bool, page_format: str, contrast_profile: str):
            """Erzeugt Vorschauseiten als PIL-Bilder aus temporärer PDF-Datei."""

            invalidate_stylesheet_template_cache()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                temp_pdf_path = Path(tmp.name)

            worksheet_design = self._worksheet_design_options()

            try:
                build_worksheet_from_request(
                    WorksheetBuildRequest(
                        input_path=input_path,
                        output_path=temp_pdf_path,
                        include_solutions=include_solutions,
                        page_format=page_format,
                        print_profile=contrast_profile,
                        design=worksheet_design,
                    )
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

    def refresh_preview(self):
            """Lädt die Vorschau neu, z. B. nach Änderungen an der Markdown-Datei."""

            input_path = self._validate_input()
            if not input_path:
                return

            include_solutions = self.preview_mode_var.get() == "solution"
            page_format = self.preview_page_format_var.get()
            contrast_profile = self.preview_contrast_var.get()

            preserve_position = self._last_preview_input_path == input_path and bool(self.preview_images)
            previous_page_index = self.current_page_index
            x_view_start = self.preview_canvas.xview()[0] if preserve_position else 0.0
            y_view_start = self.preview_canvas.yview()[0] if preserve_position else 0.0

            try:
                self.status_var.set("Erstelle Vorschau…")
                self.root.update_idletasks()
                self._show_document_diagnostics(input_path, "Vorschau")
                self.preview_images = self._render_pdf_pages(input_path, include_solutions, page_format, contrast_profile)
                self._last_preview_input_path = input_path

                if self.preview_images:
                    self.current_page_index = min(previous_page_index, len(self.preview_images) - 1) if preserve_position else 0
                else:
                    self.current_page_index = 0

                if not self.preview_images:
                    self.preview_canvas.itemconfig(self.preview_text_item, text="Keine Seiten erzeugt.")
                    self.preview_canvas.coords(self.preview_text_item, 20, 20)
                    self.preview_canvas.config(scrollregion=(0, 0, 600, 400))
                    self.page_info_var.set("Seite 0/0")
                else:
                    self._show_current_page(
                        reset_scroll=not preserve_position,
                        x_view_start=x_view_start,
                        y_view_start=y_view_start,
                    )

                self._refresh_help_preview(input_path, include_solutions, page_format, contrast_profile)

                self.status_var.set("Vorschau aktualisiert")
            except Exception as error:
                self.status_var.set("Fehler in der Vorschau")
                messagebox.showerror("Fehler", f"Vorschau konnte nicht erstellt werden:\n{error}")

            self._update_nav_buttons()

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
            self.page_info_var.set(f"Seite {self.current_page_index + 1}/{len(self.preview_images)}")
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

    def _on_horizontal_scrollbar(self, *args):
            """Leitet Scrollbar-Scroll weiter und aktualisiert aktive Seite."""

            self.preview_canvas.xview(*args)
            self._update_current_page_from_viewport_center()

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

            state = getattr(event, "state", 0)
            shift_pressed = bool(state & 0x0001)
            control_pressed = bool(state & 0x0004)

            if control_pressed:
                self.change_zoom(10 if direction > 0 else -10)
                return "break"

            scroll_units = -direction
            if shift_pressed:
                self.preview_canvas.xview_scroll(scroll_units, "units")
            else:
                self.preview_canvas.yview_scroll(scroll_units, "units")

            self._update_current_page_from_viewport_center()

            return "break"

    def reset_zoom(self):
            """Setzt den Vorschau-Zoom auf 100%."""

            self.zoom_percent = 100
            self._refresh_zoom_label()
            if self.preview_images:
                self._show_current_page()

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
