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
from ..core.blatt_kern_shared import normalize_document_mode, split_front_matter
from ..core.diagnostic_warnings import build_warning_payload
from ..styles.blatt_styles import invalidate_stylesheet_template_cache

class BlattwerkAppPreviewMixin:
    """Rendert, skaliert und navigiert die Arbeitsblatt-Vorschau."""

    def _resolve_preview_page_format_for_document_mode(self, page_format: str, document_mode: str) -> str:
            """Resolves a valid page format and remembers last used format per mode family."""
            worksheet_formats = {"a4_portrait", "a5_landscape"}
            presentation_formats = {
                "presentation_16_9",
                "presentation_16_10",
                "presentation_4_3",
            }
            mode_key = "presentation" if document_mode == "presentation" else "worksheet"
            allowed_formats = presentation_formats if mode_key == "presentation" else worksheet_formats
            default_format = "presentation_16_9" if mode_key == "presentation" else "a4_portrait"

            remembered = getattr(self, "_last_preview_page_format_by_mode", None)
            if not isinstance(remembered, dict):
                remembered = {}

            candidate = str(page_format or "").strip()
            remembered_value = str(remembered.get(mode_key, "") or "").strip()
            if candidate in allowed_formats:
                resolved = candidate
            elif remembered_value in allowed_formats:
                resolved = remembered_value
            else:
                resolved = default_format

            remembered[mode_key] = resolved
            self._last_preview_page_format_by_mode = remembered
            return resolved

    def _toggle_preview_page_format_button(self, button, visible: bool, *, padx=(10, 0)):
            """Shows or hides a page-format radiobutton without breaking pack order."""
            if button is None:
                return

            if visible:
                if not button.winfo_manager():
                    button.pack(side="left", padx=padx)
                return

            if button.winfo_manager():
                button.pack_forget()

    def _apply_preview_page_format_controls_for_document_mode(self, document_mode: str):
            """Shows only valid page-format options for the active document mode."""
            is_presentation = document_mode == "presentation"

            self._toggle_preview_page_format_button(
                getattr(self, "preview_page_format_btn_a4", None),
                not is_presentation,
                padx=(0, 0),
            )
            self._toggle_preview_page_format_button(
                getattr(self, "preview_page_format_btn_a5", None),
                not is_presentation,
                padx=(10, 0),
            )
            self._toggle_preview_page_format_button(
                getattr(self, "preview_page_format_btn_16_9", None),
                is_presentation,
                padx=(10, 0),
            )
            self._toggle_preview_page_format_button(
                getattr(self, "preview_page_format_btn_16_10", None),
                is_presentation,
                padx=(10, 0),
            )
            self._toggle_preview_page_format_button(
                getattr(self, "preview_page_format_btn_4_3", None),
                is_presentation,
                padx=(10, 0),
            )

    def _apply_preview_mode_controls_for_document_mode(self, document_mode: str):
            """Enable/disable worksheet-solution controls based on document mode."""
            worksheet_btn = getattr(self, "preview_mode_btn_worksheet", None)
            solution_btn = getattr(self, "preview_mode_btn_solution", None)
            static_label = getattr(self, "preview_mode_static_label", None)
            controls = [worksheet_btn, solution_btn]

            if document_mode == "presentation":
                for control in controls:
                    if control is None:
                        continue
                    control.configure(state="disabled")
                    if control.winfo_manager():
                        control.pack_forget()

                if static_label is not None and not static_label.winfo_manager():
                    static_label.pack(side="left")
                return

            if static_label is not None and static_label.winfo_manager():
                static_label.pack_forget()

            if worksheet_btn is not None and not worksheet_btn.winfo_manager():
                worksheet_btn.pack(side="left")
            if solution_btn is not None and not solution_btn.winfo_manager():
                solution_btn.pack(side="left", padx=(10, 0))

            for control in controls:
                if control is None:
                    continue
                control.configure(state="normal")

    def _build_preview_cache_key(self, input_path: Path, include_solutions: bool, page_format: str, contrast_profile: str):
            """Builds a deterministic cache key for rendered preview pages."""

            stats = input_path.stat()
            return (
                str(input_path),
                int(getattr(stats, "st_mtime_ns", int(stats.st_mtime * 1_000_000_000))),
                int(stats.st_size),
                bool(include_solutions),
                str(self.preview_black_screen_var.get()),
                str(page_format),
                str(contrast_profile),
                str(self.design_color_profile_var.get()),
                str(self.design_font_profile_var.get()),
                str(self.design_font_size_profile_var.get()),
            )

    def _read_document_mode(self, input_path: Path) -> str:
            """Reads current document mode from frontmatter."""
            try:
                text = input_path.read_text(encoding="utf-8")
                meta, _content = split_front_matter(text)
            except Exception:
                return "worksheet"
            return normalize_document_mode((meta or {}).get("mode"), default="worksheet")

    def _active_document_tab_state(self):
            """Returns mutable state dict for the currently active tab when available."""

            tab_id = getattr(self, "_active_document_tab_id", None)
            if tab_id is None:
                return None
            return self.document_tabs.get(tab_id)

    def _refresh_preview_for_active_tab(self):
            """Refreshes active tab preview while favoring cached pages when possible."""

            self.refresh_preview(force_rebuild=False)

    def _default_markdown_content(self):
            """Liefert den Standardinhalt für neu erzeugte Markdown-Dateien."""

            preferences = getattr(self, "user_preferences", {})
            title_prefix = str(preferences.get("new_doc_title_prefix", "") or "").strip()
            default_subject = str(preferences.get("default_subject", "") or "").strip() or "Fach eintragen"
            author = str(preferences.get("default_document_author", "") or "").strip()
            school = str(preferences.get("default_school_name", "") or "").strip()
            language_variant = str(preferences.get("language_variant", "") or "").strip()
            date_format = str(preferences.get("date_format", "") or "").strip()
            worksheet_label = str(preferences.get("worksheet_label", "") or "").strip()
            default_grade = str(preferences.get("default_grade_level", "") or "").strip()
            work_emoji_visible = bool(preferences.get("default_work_emoji_visible", True))

            title = "Neues Arbeitsblatt"
            if title_prefix:
                title = f"{title_prefix} {title}".strip()

            metadata_lines = [
                "---",
                f"Titel: {title}",
                f"Fach: {default_subject}",
                "Thema: Thema eintragen",
            ]
            if author:
                metadata_lines.append(f"Autor: {author}")
            if school:
                metadata_lines.append(f"Schule: {school}")
            if default_grade:
                metadata_lines.append(f"Klassenstufe: {default_grade}")
            if language_variant:
                metadata_lines.append(f"Sprache: {language_variant}")
            if date_format:
                metadata_lines.append(f"Datumsformat: {date_format}")
            if worksheet_label:
                metadata_lines.append(f"LabelAufgaben: {worksheet_label}")
            if not work_emoji_visible:
                metadata_lines.append("mode: test")
            metadata_lines.append("---")

            return (
                "\n".join(metadata_lines)
                + "\n\n"
                + ":::material title=\"Hinweis\"\n"
                + "Arbeite sauber und lies jede Aufgabe genau.\n"
                + ":::\n\n"
                + ":::task points=2 work=single action=read\n"
                + "Formuliere hier deine erste Aufgabe.\n"
                + ":::\n"
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

    def save_markdown_file_as(self):
            """Speichert die aktuelle Markdown-Datei unter neuem Pfad als Kopie."""

            source_path = self._validate_input()
            if source_path is None:
                return

            if self.editor_widget is not None:
                content = self.editor_widget.get("1.0", "end-1c")
            else:
                try:
                    content = source_path.read_text(encoding="utf-8")
                except Exception as error:
                    messagebox.showerror("Datei konnte nicht gelesen werden", str(error))
                    self.status_var.set("Speichern unter fehlgeschlagen")
                    return

            dialog_kwargs = {
                "title": "Markdown-Datei speichern unter",
                "defaultextension": ".md",
                "filetypes": [("Markdown", "*.md"), ("Alle Dateien", "*.*")],
                "initialdir": str(source_path.parent),
                "initialfile": source_path.name,
            }
            selected = filedialog.asksaveasfilename(**dialog_kwargs)
            if not selected:
                return

            target_path = Path(selected)
            if target_path.suffix.lower() != ".md":
                target_path = target_path.with_suffix(".md")

            if target_path == source_path:
                messagebox.showwarning(
                    "Speichern unter",
                    "Bitte wähle einen anderen Pfad als die aktuell geöffnete Datei.",
                )
                return

            if target_path.exists() and not messagebox.askyesno(
                "Datei überschreiben?",
                f"Die Datei existiert bereits und wird überschrieben:\n{target_path}\n\nMöchtest du fortfahren?",
            ):
                return

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
            except Exception as error:
                messagebox.showerror("Datei konnte nicht gespeichert werden", str(error))
                self.status_var.set("Speichern unter fehlgeschlagen")
                return

            self._set_last_dialog_dir("input_markdown", str(target_path))
            self.status_var.set(f"Datei gespeichert unter: {target_path}")
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

            selected_paths = list(filedialog.askopenfilenames(**dialog_kwargs) or ())
            if not selected_paths:
                return

            max_open_count = 8
            truncated_paths = selected_paths[:max_open_count]
            self._set_last_dialog_dir("input_markdown", truncated_paths[0])

            if len(selected_paths) > max_open_count:
                messagebox.showinfo(
                    "Auswahl begrenzt",
                    "Es werden maximal 8 Dateien gleichzeitig geöffnet.",
                )

            for path_text in truncated_paths:
                self._open_input_path(Path(path_text), add_recent=True)

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
            black_screen_mode = str(self.preview_black_screen_var.get() or "none").strip().lower()
            metadata_defaults = {}
            if hasattr(self, "_metadata_defaults_from_preferences"):
                metadata_defaults = self._metadata_defaults_from_preferences()
            copyright_override = None
            if hasattr(self, "_copyright_text_from_preferences"):
                copyright_override = self._copyright_text_from_preferences() or None

            try:
                build_worksheet_from_request(
                    WorksheetBuildRequest(
                        input_path=input_path,
                        output_path=temp_pdf_path,
                        include_solutions=include_solutions,
                        page_format=page_format,
                        print_profile=contrast_profile,
                        design=worksheet_design,
                        metadata_defaults=metadata_defaults,
                        copyright_text_override=copyright_override,
                        black_screen_mode=black_screen_mode,
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

    def refresh_preview(self, force_rebuild=False):
            """Lädt die Vorschau neu, z. B. nach Änderungen an der Markdown-Datei."""

            if getattr(self, "_preview_refresh_in_progress", False):
                return
            self._preview_refresh_in_progress = True

            try:
                input_path = self._validate_input()
                if not input_path:
                    return

                include_solutions = self.preview_mode_var.get() == "solution"
                page_format = self.preview_page_format_var.get()
                contrast_profile = self.preview_contrast_var.get()
                document_mode = self._read_document_mode(input_path)
                self._current_preview_document_mode = document_mode
                self._apply_preview_mode_controls_for_document_mode(document_mode)
                self._apply_preview_page_format_controls_for_document_mode(document_mode)

                if document_mode == "presentation":
                    include_solutions = False
                    if self.preview_mode_var.get() != "worksheet":
                        self.preview_mode_var.set("worksheet")

                resolved_page_format = self._resolve_preview_page_format_for_document_mode(
                    page_format,
                    document_mode,
                )
                if page_format != resolved_page_format:
                    page_format = resolved_page_format
                    self.preview_page_format_var.set(page_format)

                tab_state = self._active_document_tab_state()

                cache_key = None
                if tab_state is not None:
                    try:
                        cache_key = self._build_preview_cache_key(input_path, include_solutions, page_format, contrast_profile)
                    except Exception:
                        cache_key = None

                cached_images = tab_state.get("preview_images") if isinstance(tab_state, dict) else None
                
                last_cached_page_format = tab_state.get("_preview_page_format") if tab_state else None
                page_format_changed = page_format != last_cached_page_format
                
                if (
                    not force_rebuild
                    and not page_format_changed
                    and tab_state is not None
                    and cache_key is not None
                    and tab_state.get("preview_cache_key") == cache_key
                    and isinstance(cached_images, list)
                    and bool(cached_images)
                ):
                    self.preview_images = cached_images
                    self._last_preview_input_path = input_path
                    self.current_page_index = max(
                        0,
                        min(int(tab_state.get("current_page_index", 0)), len(self.preview_images) - 1),
                    )
                    self.zoom_percent = int(str(tab_state.get("zoom_percent", self.zoom_percent) or self.zoom_percent))
                    x_view_start = float(tab_state.get("x_view_start", 0.0) or 0.0)
                    y_view_start = float(tab_state.get("y_view_start", 0.0) or 0.0)

                    self._show_current_page(
                        reset_scroll=False,
                        x_view_start=x_view_start,
                        y_view_start=y_view_start,
                    )
                    if hasattr(self, "_update_lernhilfen_action_state"):
                        self._update_lernhilfen_action_state(
                            input_path=input_path,
                            include_solutions=include_solutions,
                        )
                    if (
                        self.help_preview_window is not None
                        and self.help_preview_window.winfo_exists()
                    ):
                        self._refresh_help_preview(
                            input_path,
                            include_solutions,
                            page_format,
                            contrast_profile,
                        )
                    self._refresh_zoom_label()
                    self.status_var.set("Vorschau aus Cache geladen")
                    self._update_nav_buttons()
                    return

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

                    if tab_state is not None and cache_key is not None:
                        tab_state["preview_cache_key"] = cache_key
                        tab_state["preview_images"] = list(self.preview_images)
                        tab_state["_preview_page_format"] = page_format

                    if self.preview_images:
                        self.current_page_index = min(previous_page_index, len(self.preview_images) - 1) if preserve_position else 0
                    else:
                        self.current_page_index = 0

                    if not self.preview_images:
                        self.preview_canvas.itemconfig(self.preview_text_item, text="Keine Seiten erzeugt.")
                        self.preview_canvas.coords(self.preview_text_item, 20, 20)
                        self.preview_canvas.config(scrollregion=(0, 0, 600, 400))
                        page_label = (
                            "Folie"
                            if getattr(self, "_current_preview_document_mode", "worksheet") == "presentation"
                            else "Seite"
                        )
                        self.page_info_var.set(f"{page_label} 0/0")
                    else:
                        self._show_current_page(
                            reset_scroll=not preserve_position,
                            x_view_start=x_view_start,
                            y_view_start=y_view_start,
                        )

                    if hasattr(self, "_update_lernhilfen_action_state"):
                        self._update_lernhilfen_action_state(
                            input_path=input_path,
                            include_solutions=include_solutions,
                        )

                    if (
                        self.help_preview_window is not None
                        and self.help_preview_window.winfo_exists()
                    ):
                        self._refresh_help_preview(
                            input_path,
                            include_solutions,
                            page_format,
                            contrast_profile,
                        )

                    self.status_var.set("Vorschau aktualisiert")
                except Exception as error:
                    self.status_var.set("Fehler in der Vorschau")
                    messagebox.showerror("Fehler", f"Vorschau konnte nicht erstellt werden:\n{error}")

                if hasattr(self, "_persist_active_document_tab_state"):
                    self._persist_active_document_tab_state()
                self._update_nav_buttons()
            finally:
                self._preview_refresh_in_progress = False

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
                if getattr(self, "_current_preview_document_mode", "worksheet") == "presentation"
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
