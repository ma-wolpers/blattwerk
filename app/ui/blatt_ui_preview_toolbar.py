"""Vorschau-Toolbar: Capabilities je Dokumenttyp und Sichtbarkeit/Zustand der Optionsgruppen
(Seitenformat, Ansicht Aufgabe/Loesung/Erwartungshorizont, Black-Screen, Phasen, Gestaltung).
"""

from __future__ import annotations

from ..styles.blatt_styles import (
    DEFAULT_PRESENTATION_PAGE_FORMAT,
    DEFAULT_WORKSHEET_PAGE_FORMAT,
    PRESENTATION_PAGE_FORMATS,
    WORKSHEET_PAGE_FORMATS,
)
from ..core.help_cards_appendix import HELP_APPENDIX_NONE, coerce_help_appendix, help_appendix_supported
from ..core.document_type_registry import (
    PIPELINE_WORKSHEET,
    PREVIEW_VARIANT_EXPECTATION,
    PREVIEW_VARIANT_SOLUTION,
    PREVIEW_VARIANT_WORKSHEET,
    coerce_preview_variant,
    has_slide_layout,
    preview_variants,
    spec_for_type,
)


class BlattwerkAppPreviewToolbarMixin:
    """Steuert, welche Vorschau-Optionen fuer den aktiven Dokumenttyp sichtbar und aktiv sind."""


    @staticmethod
    def _normalize_presentation_section_separator(value) -> str:
            candidate = str(value or "dot").strip().lower()
            if candidate in {"dot", "arrow"}:
                return candidate
            return "dot"


    @staticmethod
    def _parse_bool_setting(value) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "ja", "on"}
            return bool(value)


    def _resolve_preview_page_format_for_document_type(self, page_format: str, document_type: str | None) -> str:
            """Resolves a valid page format and remembers the last used format per layout family."""
            mode_key = "presentation" if has_slide_layout(document_type or "") else "worksheet"
            if mode_key == "presentation":
                allowed_formats = set(PRESENTATION_PAGE_FORMATS)
                default_format = DEFAULT_PRESENTATION_PAGE_FORMAT
            else:
                allowed_formats = set(WORKSHEET_PAGE_FORMATS)
                default_format = DEFAULT_WORKSHEET_PAGE_FORMAT

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


    @staticmethod
    def _preview_toolbar_capabilities(document_type: str | None, preview_variant: str | None = None) -> dict[str, bool]:
            """Decides which preview-toolbar controls are meaningful for the active tab.

            Centralizes the document-type gating in one place: the toolbar shows
            only options that mean something for the active document type.

            * Page format and design controls: worksheet pipeline only
              (Arbeitsblatt/Praesentation/Klausur); Kurzentwurf, Schild and plain
              Markdown render through their own pipelines (see
              `app/core/document_preview_build.py`). Also hidden while the
              expectation-horizon view is shown: it has its own fixed layout.
            * Phasen (section footer) and Black-Screen: slide layout only
              (Praesentation). On Arbeitsblatt/Klausur they are hidden, not just
              disabled, because they have no effect there.
            * View choice (Aufgabe/Loesung/Erwartungshorizont, key
              ``show_solution_toggle``): only where the type has more than one
              view (`document_type_registry.preview_variants`).
            * Lernhilfen-Anhang (``show_help_appendix``): types with
              `help_appendix_supported` (Arbeitsblatt/Klausur), not in the
              expectation-horizon view.

            Folien-Layout and the available views come from the registry, never
            from a frontmatter `mode`. Shortcut handlers use the same answer via
            `_preview_capability_active`.

            Args:
                document_type: Canonical type of the active tab, or ``None``.
                preview_variant: The requested view; coerced to one the type
                    has (``None`` counts as `worksheet`).
            """
            spec = spec_for_type(document_type) if document_type else None
            worksheet_pipeline = spec is not None and spec.pipeline == PIPELINE_WORKSHEET
            is_presentation = worksheet_pipeline and spec.slide_layout
            own_layout = coerce_preview_variant(document_type, preview_variant) == PREVIEW_VARIANT_EXPECTATION
            return {
                "show_solution_toggle": len(preview_variants(document_type)) > 1,
                "show_page_format": worksheet_pipeline and not own_layout,
                "show_phase_controls": is_presentation,
                "show_black_screen": is_presentation,
                "show_design_controls": worksheet_pipeline and not own_layout,
                "show_help_appendix": help_appendix_supported(document_type) and not own_layout,
            }

    def _preview_capability_active(self, capability: str) -> bool:
            """Tell whether a toolbar capability applies to the document shown in the preview.

            Used by keyboard handlers (e.g. K for Black-Screen, 4/5 for the page
            format) so a shortcut never changes an option the toolbar hides for the
            current document type. Uses the type of the last refresh
            (`_current_preview_document_type`); without a document nothing applies.

            Args:
                capability: A key of `_preview_toolbar_capabilities`, e.g.
                    ``"show_black_screen"``.
            """
            document_type = getattr(self, "_current_preview_document_type", None)
            if not document_type:
                return False
            preview_mode_var = getattr(self, "preview_mode_var", None)
            variant = preview_mode_var.get() if preview_mode_var is not None else None
            return bool(self._preview_toolbar_capabilities(document_type, variant).get(capability, False))


    def _effective_help_appendix(self) -> str:
            """Die Anhang-Variante, die Vorschau und Export tatsächlich verwenden.

            Einzige Quelle für beide: der Wert der Vorschau-Radios, aber
            `HELP_APPENDIX_NONE`, solange die Gruppe für den aktiven Typ bzw. die
            Ansicht nicht gilt. Ob Lernhilfen vorhanden sind, spielt hier bewusst
            keine Rolle -- ohne sichtbare Karte hängt der Core nichts an, und so
            bleibt die gewählte Variante beim Hinzufügen der ersten Karte erhalten.
            """
            if not self._preview_capability_active("show_help_appendix"):
                return HELP_APPENDIX_NONE
            return coerce_help_appendix(self.preview_help_appendix_var.get())


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


    def _apply_preview_page_format_controls(self, document_type: str | None, preview_variant: str | None = None):
            """Shows only valid page-format options for the active document type and view."""
            capabilities = self._preview_toolbar_capabilities(document_type, preview_variant)
            buttons = getattr(self, "preview_page_format_buttons", {}) or {}
            if not capabilities["show_page_format"]:
                visible_formats = ()
            elif has_slide_layout(document_type or ""):
                visible_formats = PRESENTATION_PAGE_FORMATS
            else:
                visible_formats = WORKSHEET_PAGE_FORMATS
            first_visible = True
            for page_format, button in buttons.items():
                visible = page_format in visible_formats
                self._toggle_preview_page_format_button(
                    button,
                    visible,
                    padx=(0, 0) if first_visible else (10, 0),
                )
                if visible:
                    first_visible = False


    def _apply_preview_mode_controls(self, document_type: str | None, preview_variant: str | None = None):
            """Adapts the view radios, Phasen, Black-Screen and Gestaltung controls to the active tab."""
            capabilities = self._preview_toolbar_capabilities(document_type, preview_variant)
            static_label = getattr(self, "preview_mode_static_label", None)
            phase_controls = [
                getattr(self, "preview_phase_separator_btn_dot", None),
                getattr(self, "preview_phase_separator_btn_arrow", None),
                getattr(self, "preview_phase_hide_future_check", None),
            ]
            black_screen_buttons = getattr(self, "preview_black_screen_buttons", [])

            static_text = spec_for_type(document_type).label if document_type else "Unbekannter Typ"
            if capabilities["show_solution_toggle"]:
                if static_label is not None and static_label.winfo_manager():
                    static_label.pack_forget()
            elif static_label is not None:
                static_label.configure(text=static_text)
                if not static_label.winfo_manager():
                    static_label.pack(side="left")
            self._apply_preview_variant_buttons(
                preview_variants(document_type) if capabilities["show_solution_toggle"] else ()
            )

            format_group_phase = getattr(self, "format_group_phase", None)
            if format_group_phase is not None:
                self._set_responsive_group_hidden(format_group_phase, not capabilities["show_phase_controls"])
            for control in phase_controls:
                if control is None:
                    continue
                control.configure(state="normal")

            format_group_black = getattr(self, "format_group_black", None)
            if format_group_black is not None:
                self._set_responsive_group_hidden(format_group_black, not capabilities["show_black_screen"])
            for button in black_screen_buttons:
                button.configure(state="normal")

            self._apply_design_section_visibility(capabilities["show_design_controls"])
            self._apply_preview_help_appendix_controls(capabilities["show_help_appendix"])


    def _apply_preview_variant_buttons(self, visible_variants: tuple[str, ...]) -> None:
            """Packs exactly the view radios in `visible_variants`, in registry order.

            All radios are unpacked first and re-packed in order, so Aufgabe |
            Lösung | Erwartungshorizont never ends up shuffled after switching
            between an Arbeitsblatt and a Klausur tab. Hidden radios are also
            disabled, so no keyboard focus lands on them.

            Args:
                visible_variants: Views to show (from `preview_variants`), or an
                    empty tuple when the type has only one view.
            """
            buttons = {
                PREVIEW_VARIANT_WORKSHEET: getattr(self, "preview_mode_btn_worksheet", None),
                PREVIEW_VARIANT_SOLUTION: getattr(self, "preview_mode_btn_solution", None),
                PREVIEW_VARIANT_EXPECTATION: getattr(self, "preview_mode_btn_expectation", None),
            }
            for button in buttons.values():
                if button is not None and button.winfo_manager():
                    button.pack_forget()
            first = True
            for variant, button in buttons.items():
                if button is None:
                    continue
                visible = variant in visible_variants
                button.configure(state="normal" if visible else "disabled")
                if visible:
                    button.pack(side="left", padx=(0, 0) if first else (10, 0))
                    first = False


    def _apply_design_section_visibility(self, visible: bool) -> None:
            """Shows/hides the whole Gestaltung row (Kontrast/Farbprofil/Schrift/Größe) as one unit."""
            design_section = getattr(self, "design_section", None)
            if design_section is None:
                return
            if visible:
                if not design_section.winfo_manager():
                    design_section.pack(fill="x", pady=(0, 8), before=self.actions_section)
            else:
                if design_section.winfo_manager():
                    design_section.pack_forget()
