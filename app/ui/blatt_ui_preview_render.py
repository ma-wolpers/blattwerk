"""Vorschau-Rendering: Cache-Schluessel, Rechen-Cache, PDF-Seiten erzeugen und
`refresh_preview` als Einstieg fuer jede Aktualisierung.
"""

from __future__ import annotations

from pathlib import Path
from .dialog_services import messagebox
from ..core.block_computation_cache import open_block_computation_cache
from ..core.document_preview_build import build_preview_images_for_document
from ..core.kurzentwurf_settings import (
    kurzentwurf_runtime_options_from_preferences,
)
from ..core.document_type_registry import (
    DOCUMENT_TYPE_KURZENTWURF,
    PREVIEW_VARIANT_SOLUTION,
    PREVIEW_VARIANT_WORKSHEET,
    coerce_preview_variant,
    has_slide_layout,
)
from ..styles.blatt_styles import invalidate_stylesheet_template_cache


class BlattwerkAppPreviewRenderMixin:
    """Erzeugt die Vorschauseiten (gerasterte Export-PDF) und verwaltet ihre Caches."""


    def _build_preview_cache_key(
            self,
            input_path: Path,
            include_solutions: bool,
            page_format: str,
            contrast_profile: str,
            *,
            document_type: str = "worksheet",
            preview_variant: str | None = None,
    ):
            """Builds a deterministic cache key for rendered preview pages.

            The view (`preview_variant`, see `document_type_registry.preview_variants`)
            is part of the key, so Lösung and Erwartungshorizont never share a
            cached page set even though both render with ``include_solutions``
            off/on independently. Without an explicit view it is derived from
            ``include_solutions`` (callers that only know the old flag).
            """
            if preview_variant is None:
                preview_variant = PREVIEW_VARIANT_SOLUTION if include_solutions else PREVIEW_VARIANT_WORKSHEET

            stats = input_path.stat()
            kurzentwurf_runtime_key = None
            if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
                preferences = getattr(self, "user_preferences", {})
                options = kurzentwurf_runtime_options_from_preferences(preferences)
                kurzentwurf_runtime_key = tuple(sorted((str(k), repr(v)) for k, v in options.items()))

            return (
                str(input_path),
                int(getattr(stats, "st_mtime_ns", int(stats.st_mtime * 1_000_000_000))),
                int(stats.st_size),
                str(preview_variant),
                str(self.preview_black_screen_var.get()),
                self._normalize_presentation_section_separator(self.preview_section_separator_var.get()),
                self._parse_bool_setting(self.preview_hide_future_sections_var.get()),
                str(page_format),
                str(contrast_profile),
                str(self.design_color_profile_var.get()),
                str(self.design_font_profile_var.get()),
                str(self.design_font_size_profile_var.get()),
                kurzentwurf_runtime_key,
            )


    def _active_document_tab_state(self):
            """Returns mutable state dict for the currently active tab when available."""

            tab_id = getattr(self, "_active_document_tab_id", None)
            if tab_id is None:
                return None
            return self.document_tabs.get(tab_id)


    def _resolve_computation_cache(self, input_path):
            """Returns the `BlockComputationCache` for the tab holding `input_path`.

            Ownership lives here (the application/GUI layer), never in
            `build_worksheet()`/`build_help_cards()` -- see
            `app/core/block_computation_cache.py`. Deliberately looks the
            tab up **by path** across all open tabs rather than assuming
            "the active tab", since callers such as the multi-document
            Lernhilfen export (`blatt_ui_export_multi.py`) resolve a cache
            for one document at a time while a *different* tab is active.
            One instance is kept per matching tab in
            `tab_state["_computation_cache"]` so that a worksheet export
            followed by a solution export for the same document (or the
            validation pass followed by rendering within a single build)
            can reuse the same cached results. Returns `None` when no open
            tab matches `input_path` (e.g. a headless/CLI-style call, or a
            test double without a real `document_tabs`), which every
            downstream consumer already treats as "no cache, compute
            directly".
            """

            document_tabs = getattr(self, "document_tabs", None)
            if not document_tabs:
                return None

            normalized_path = str(input_path)
            tab_state = None
            for candidate in document_tabs.values():
                if str(candidate.get("path", "")) == normalized_path:
                    tab_state = candidate
                    break
            if tab_state is None:
                return None

            cached = tab_state.get("_computation_cache")
            if cached is not None:
                return cached

            preferences = getattr(self, "user_preferences", {})
            persist = str(preferences.get("computation_cache_lifetime", "session")) == "persistent"
            cache = open_block_computation_cache(input_path, persist=persist)
            tab_state["_computation_cache"] = cache
            return cache


    def _refresh_preview_for_active_tab(self):
            """Refreshes active tab preview while favoring cached pages when possible."""

            preferences = getattr(self, "user_preferences", {})
            raw_value = preferences.get("preview_auto_refresh_on_tab_switch", True)
            if isinstance(raw_value, str):
                auto_refresh = raw_value.strip().lower() in {"1", "true", "yes", "ja", "on"}
            else:
                auto_refresh = bool(raw_value)

            self.refresh_preview(force_rebuild=auto_refresh)


    def _render_pdf_pages(
            self,
            input_path: Path,
            include_solutions: bool,
            page_format: str,
            contrast_profile: str,
            preview_variant: str = PREVIEW_VARIANT_WORKSHEET,
    ):
            """Erzeugt Vorschauseiten als PIL-Bilder aus temporärer PDF-Datei.

            `preview_variant` wählt die Ansicht (`document_type_registry.preview_variants`);
            bei `expectation` rastert der Core den Erwartungshorizont statt des Dokuments.
            """

            invalidate_stylesheet_template_cache()

            worksheet_design = self._worksheet_design_options()
            black_screen_mode = str(self.preview_black_screen_var.get() or "none").strip().lower()
            section_separator = self._normalize_presentation_section_separator(
                self.preview_section_separator_var.get()
            )
            hide_future_sections = self._parse_bool_setting(
                self.preview_hide_future_sections_var.get()
            )
            metadata_defaults = {}
            if hasattr(self, "_metadata_defaults_from_preferences"):
                metadata_defaults = self._metadata_defaults_from_preferences()
            copyright_override = None
            if hasattr(self, "_copyright_text_from_preferences"):
                copyright_override = self._copyright_text_from_preferences() or None

            document_type = "worksheet"
            if hasattr(self, "_read_document_type"):
                document_type = self._read_document_type(input_path)

            preferences = getattr(self, "user_preferences", {})
            kurzentwurf_options = kurzentwurf_runtime_options_from_preferences(preferences)

            return build_preview_images_for_document(
                input_path,
                document_type=document_type,
                include_solutions=include_solutions,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=section_separator,
                presentation_hide_future_sections=hide_future_sections,
                kurzentwurf_options=kurzentwurf_options,
                computation_cache=self._resolve_computation_cache(input_path),
                preview_variant=preview_variant,
            )


    def refresh_preview(self, force_rebuild=False):
            """Lädt die Vorschau neu, z. B. nach Änderungen an der Markdown-Datei."""

            if getattr(self, "_preview_refresh_in_progress", False):
                return
            self._preview_refresh_in_progress = True

            try:
                input_path = self._validate_input()
                if not input_path:
                    return

                page_format = self.preview_page_format_var.get()
                contrast_profile = self.preview_contrast_var.get()
                document_type = self._read_document_type(input_path)
                if document_type is None:
                    self.status_var.set(f"Unbekannte Dateiendung: {input_path.name}")
                    return
                self._current_preview_document_type = document_type
                # Nur Ansichten, die der Typ hat (Registry); daraus folgt auch die Lösungsfassung.
                preview_variant = coerce_preview_variant(document_type, self.preview_mode_var.get())
                if self.preview_mode_var.get() != preview_variant:
                    self.preview_mode_var.set(preview_variant)
                include_solutions = preview_variant == PREVIEW_VARIANT_SOLUTION
                self._apply_preview_mode_controls(document_type, preview_variant)
                if hasattr(self, "_sync_font_profile_combo"):
                    # Schriftmenue zeigt den `font_profile` des aktiven Dokuments.
                    self._sync_font_profile_combo()
                self._apply_preview_page_format_controls(document_type, preview_variant)
                if hasattr(self, "_refresh_migration_bar"):
                    self._refresh_migration_bar()

                resolved_page_format = self._resolve_preview_page_format_for_document_type(
                    page_format,
                    document_type,
                )
                if page_format != resolved_page_format:
                    page_format = resolved_page_format
                    self.preview_page_format_var.set(page_format)

                tab_state = self._active_document_tab_state()

                cache_key = None
                if tab_state is not None:
                    try:
                        cache_key = self._build_preview_cache_key(
                            input_path,
                            include_solutions,
                            page_format,
                            contrast_profile,
                            document_type=document_type,
                            preview_variant=preview_variant,
                        )
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
                    self.preview_images, compile_diagnostics = self._render_pdf_pages(
                        input_path,
                        include_solutions,
                        page_format,
                        contrast_profile,
                        preview_variant,
                    )
                    self._show_compile_overflow_warnings(compile_diagnostics, "Vorschau")
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
                            if has_slide_layout(getattr(self, "_current_preview_document_type", None) or "")
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
