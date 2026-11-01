"""Vorschau-Rendering: Cache-Schluessel, Rechen-Cache, PDF-Seiten erzeugen und
`refresh_preview` als Einstieg fuer jede Aktualisierung.
"""

from __future__ import annotations

import logging
from pathlib import Path
from .dialog_services import messagebox
from .preview_page_cache import CachedPreview, FileDependencyCollector
from ..core.block_computation_cache import open_block_computation_cache
from ..core.document_preview_build import build_preview_images_for_document, preview_environment_stamp
from ..core.kurzentwurf_settings import (
    kurzentwurf_runtime_options_from_preferences,
)
from ..core.document_type_registry import (
    PREVIEW_VARIANT_SOLUTION,
    PREVIEW_VARIANT_WORKSHEET,
    coerce_preview_variant,
    has_slide_layout,
)
from ..core.render_job import run_observed
from ..storage.user_preferences_specs import PREFERENCE_SPECS
from ..styles.blatt_styles import invalidate_stylesheet_template_cache

_LOG = logging.getLogger(__name__)


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

            options = self._preview_build_options(
                document_type, include_solutions, page_format, contrast_profile, preview_variant
            )
            return (
                str(input_path),
                input_path.read_bytes(),
                repr(sorted(options.items())),
                preview_environment_stamp(),
            )


    def _preview_build_options(self, document_type, include_solutions, page_format, contrast_profile, preview_variant):
            """Sammelt alle Render-Optionen der Vorschau an einer Stelle.

            Einzige Quelle für den Render-Aufruf (`_render_pdf_pages`) und den Cache-Schlüssel
            (`_build_preview_cache_key`). Liest beide getrennt, fehlt im Schlüssel leicht eine
            Option, und nach einer Änderung erscheint ein veralteter Stand. Genau so fehlten
            früher Copyright und Metadaten-Vorgaben.

            Args:
                document_type: Kanonischer Dokumenttyp.
                include_solutions: Lösungsfassung rendern.
                page_format: Seitenformat.
                contrast_profile: Druck-/Kontrastprofil.
                preview_variant: Ansicht (`document_type_registry.preview_variants`).

            Returns:
                Schlüsselwortargumente für `build_preview_images_for_document`, ohne den
                Rechen-Cache, der das Ergebnis nicht verändert.
            """
            metadata_defaults = {}
            if hasattr(self, "_metadata_defaults_from_preferences"):
                metadata_defaults = self._metadata_defaults_from_preferences()
            copyright_override = None
            if hasattr(self, "_copyright_text_from_preferences"):
                copyright_override = self._copyright_text_from_preferences() or None

            return {
                "document_type": document_type,
                "include_solutions": include_solutions,
                "page_format": page_format,
                "contrast_profile": contrast_profile,
                "worksheet_design": self._worksheet_design_options(),
                "metadata_defaults": metadata_defaults,
                "copyright_override": copyright_override,
                "black_screen_mode": str(self.preview_black_screen_var.get() or "none").strip().lower(),
                "presentation_section_separator": self._normalize_presentation_section_separator(
                    self.preview_section_separator_var.get()
                ),
                "presentation_hide_future_sections": self._parse_bool_setting(
                    self.preview_hide_future_sections_var.get()
                ),
                "kurzentwurf_options": kurzentwurf_runtime_options_from_preferences(
                    getattr(self, "user_preferences", {})
                ),
                "preview_variant": preview_variant,
                "help_appendix": self._effective_help_appendix(),
            }


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
            """Refreshes active tab preview while favoring cached pages when possible.

            Die Einstellung `preview_auto_refresh_on_tab_switch` erzwingt auf Wunsch den Neubau.
            Nötig ist das selten: Der Cache-Schlüssel erkennt Änderungen an Inhalt und Optionen.
            """

            preferences = getattr(self, "user_preferences", {})
            setting = "preview_auto_refresh_on_tab_switch"
            raw_value = preferences.get(setting, PREFERENCE_SPECS[setting]["default"])
            self.refresh_preview(force_rebuild=self._parse_bool_setting(raw_value))


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

            document_type = "worksheet"
            if hasattr(self, "_read_document_type"):
                document_type = self._read_document_type(input_path)

            return build_preview_images_for_document(
                input_path,
                computation_cache=self._resolve_computation_cache(input_path),
                **self._preview_build_options(
                    document_type, include_solutions, page_format, contrast_profile, preview_variant
                ),
            )


    def _refresh_help_preview_if_changed(self, cache_key, force_rebuild, input_path, include_solutions, contrast_profile):
            """Aktualisiert ein offenes Lernhilfen-Fenster, wenn sich der Stand geändert hat.

            Das Fenster druckt sonst bei jeder Aktualisierung neu, auch wenn die Hauptvorschau
            aus dem Cache kommt.

            Args:
                cache_key: Schlüssel des aktuellen Vorschau-Stands; None erzwingt das Neuzeichnen.
                force_rebuild: Der Nutzer hat ausdrücklich einen Neubau verlangt.
                input_path: Quelldatei.
                include_solutions: Kartensichtbarkeit wie in der Lösungsfassung.
                contrast_profile: Druck-/Kontrastprofil.
            """
            if self.help_preview_window is None or not self.help_preview_window.winfo_exists():
                return
            if not force_rebuild and cache_key is not None and cache_key == getattr(self, "_help_preview_cache_key", None):
                return
            self._refresh_help_preview(input_path, include_solutions, contrast_profile)
            self._help_preview_cache_key = cache_key


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
                        _LOG.warning("Vorschau-Cache-Schlüssel nicht bestimmbar: %s", input_path, exc_info=True)
                        cache_key = None

                cached = None
                if not force_rebuild and tab_state is not None and cache_key is not None:
                    cached = self._preview_page_cache.get(cache_key)

                if cached is not None and cached.images:
                    self.preview_images = list(cached.images)
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
                    self._refresh_help_preview_if_changed(
                        cache_key, force_rebuild, input_path, include_solutions, contrast_profile
                    )
                    self._show_compile_overflow_warnings(cached.diagnostics, "Vorschau")
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
                    file_dependencies = FileDependencyCollector()
                    self.preview_images, compile_diagnostics = run_observed(
                        lambda: self._render_pdf_pages(
                            input_path,
                            include_solutions,
                            page_format,
                            contrast_profile,
                            preview_variant,
                        ),
                        file_dependencies,
                    )
                    self._show_compile_overflow_warnings(compile_diagnostics, "Vorschau")
                    self._last_preview_input_path = input_path

                    if tab_state is not None and cache_key is not None:
                        self._preview_page_cache.put(
                            cache_key,
                            CachedPreview(
                                images=tuple(self.preview_images),
                                diagnostics=tuple(compile_diagnostics),
                                dependencies=file_dependencies.dependencies,
                                path=str(input_path),
                            ),
                        )

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

                    self._refresh_help_preview_if_changed(
                        cache_key, force_rebuild, input_path, include_solutions, contrast_profile
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
