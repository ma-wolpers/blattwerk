"""Export-Hilfen: Dokumenttyp, Lernhilfen-Zustand, Metadaten-/Copyright-Vorgaben,
Diagnose-Hinweise, Loesungs-Dateinamen und Build-Requests.
"""

from __future__ import annotations

from pathlib import Path
from .dialog_services import messagebox
from ..core.build_requests import HelpCardsBuildRequest, WorksheetBuildRequest
from ..core.blatt_kern_help_render import collect_help_blocks
from ..core.blatt_validator import inspect_markdown_text
from ..core.diagnostic_warnings import build_warning_payload
from ..core.export_path_guardrails import LOCK_POLICIES, LOCK_POLICY_ERROR, ExportTargetPolicy
from ..storage import acknowledged_warnings_store
from ..storage.file_lock_probe_adapter import default_lock_probe
from .export_defaults import _ALLOWED_SECTION_SEPARATOR_MODES, _normalize_choice


class BlattwerkAppExportSupportMixin:
    """Gemeinsame Hilfen fuer alle Exportwege."""

    def _current_presentation_footer_export_options(self):
        """Returns normalized presentation footer options from current preview controls."""

        separator_value = str(
            getattr(self, "preview_section_separator_var", None).get()
            if getattr(self, "preview_section_separator_var", None) is not None
            else "dot"
        ).strip().lower()
        separator_value = _normalize_choice(
            separator_value,
            _ALLOWED_SECTION_SEPARATOR_MODES,
            "dot",
        )

        hide_future_var = getattr(self, "preview_hide_future_sections_var", None)
        hide_future_value = hide_future_var.get() if hide_future_var is not None else False
        if isinstance(hide_future_value, str):
            hide_future_value = hide_future_value.strip().lower() in {
                "1",
                "true",
                "yes",
                "ja",
                "on",
            }

        return separator_value, bool(hide_future_value)

    def _detect_document_type(self, input_path: Path) -> str | None:
        """Typ des Dokuments für Exporte (delegiert an die eine UI-Typquelle, I1)."""
        return self._read_document_type(input_path)

    def _count_visible_lernhilfen(self, input_path: Path, include_solutions: bool) -> int:
        """Counts currently visible lernhilfen blocks for a given document and mode."""

        try:
            text = input_path.read_text(encoding="utf-8")
            inspected = inspect_markdown_text(text)
        except Exception:
            return 0

        return len(
            collect_help_blocks(
                inspected.blocks,
                include_solutions=include_solutions,
            )
        )

    def _update_lernhilfen_action_state(self, input_path: Path | None = None, include_solutions: bool | None = None):
        """Updates the main preview-row lernhilfen action button state."""

        button = getattr(self, "lernhilfen_action_btn", None)
        if button is None:
            return

        active_input_path = input_path if input_path is not None else self._validate_input()
        if not active_input_path:
            button.config(state="disabled")
            self._active_lernhilfen_available = False
            return

        spec = self._document_spec_for_path(active_input_path)
        if spec is None or not spec.blocks:
            # Intentional gate, not just the incidental "0 :::-blocks found" side
            # effect below -- Kurzentwurf and plain Markdown have no `:::` block
            # semantics and therefore no Lernhilfen concept at all.
            button.config(state="disabled")
            self._active_lernhilfen_available = False
            return

        if include_solutions is None:
            include_solutions = self.preview_mode_var.get() == "solution"

        has_lernhilfen = self._count_visible_lernhilfen(active_input_path, include_solutions=include_solutions) > 0
        self._active_lernhilfen_available = has_lernhilfen
        button.config(state="normal" if has_lernhilfen else "disabled")

    def _current_preview_has_lernhilfen(self, input_path: Path | None = None) -> bool:
        """Returns whether current document has visible lernhilfen in active preview mode."""

        active_input_path = input_path if input_path is not None else self._validate_input()
        if not active_input_path:
            return False

        include_solutions = self.preview_mode_var.get() == "solution"
        return self._count_visible_lernhilfen(active_input_path, include_solutions=include_solutions) > 0

    def _metadata_defaults_from_preferences(self):
        preferences = getattr(self, "user_preferences", {})
        defaults = {
            "Autor": str(preferences.get("default_document_author", "") or "").strip(),
            "Schule": str(preferences.get("default_school_name", "") or "").strip(),
            "Fach": str(preferences.get("default_subject", "") or "").strip(),
            "Klassenstufe": str(preferences.get("default_grade_level", "") or "").strip(),
            "Sprache": str(preferences.get("language_variant", "") or "").strip(),
            "Datumsformat": str(preferences.get("date_format", "") or "").strip(),
        }
        return {key: value for key, value in defaults.items() if value}

    def _copyright_text_from_preferences(self):
        preferences = getattr(self, "user_preferences", {})
        holder = str(preferences.get("copyright_holder", "") or "").strip()
        mode = str(preferences.get("copyright_year_mode", "current") or "current").strip()
        fixed_year = int(str(preferences.get("copyright_year_fixed", 2026) or 2026))
        footer_extra = str(preferences.get("footer_extra_text", "") or "").strip()

        if not holder:
            return ""

        from datetime import datetime

        current_year = datetime.now().year
        if mode == "fixed":
            year_text = str(fixed_year)
        elif mode == "span":
            year_text = f"{fixed_year}-{current_year}" if fixed_year <= current_year else str(current_year)
        else:
            year_text = str(current_year)

        base = f"{holder} · {year_text}"
        if footer_extra:
            return f"{base} · {footer_extra}"
        return base

    def _show_export_diagnostics(self, input_path: Path):
        """Zeigt nicht-blockierende Warnungen vor dem Export an."""
        preferences = getattr(self, "user_preferences", {})
        if not bool(preferences.get("pre_export_diagnostics_enabled", True)):
            return

        warning_payload = build_warning_payload(
            input_path, "Export", acknowledged_repo=acknowledged_warnings_store
        )
        if warning_payload is None or warning_payload["count"] <= 0:
            return

        messagebox.showwarning(
            warning_payload["title"],
            "Export laeuft weiter, aber es gibt Warnungen:\n\n" + warning_payload["message"],
        )

    def _show_compile_overflow_warnings(self, diagnostics, context_label: str = "Export"):
        """Zeigt PT002-/PPTX001-/PPTX002-Warnungen aus dem Compile-/Render-Schritt."""

        overflow_warnings = [
            diag for diag in (diagnostics or [])
            if str(getattr(diag, "code", "")) in self._SURFACED_COMPILE_WARNING_CODES
        ]
        if not overflow_warnings:
            return

        lines = [f"- {diag.code}: {diag.message}" for diag in overflow_warnings]
        messagebox.showwarning(
            f"Blattwerk-Warnungen ({context_label})",
            "Export lief weiter, aber es gibt Compile-Warnungen:\n\n" + "\n".join(lines),
        )

    def _with_solution_suffix(self, path_obj: Path):
        """With solution suffix."""
        suffix = str(getattr(self, "user_preferences", {}).get("solution_suffix", "_loesung") or "_loesung")
        if path_obj.stem.endswith(suffix):
            return path_obj
        return path_obj.with_name(path_obj.stem + suffix + path_obj.suffix)

    def _without_solution_suffix(self, path_obj: Path):
        """Without solution suffix."""
        suffix = str(getattr(self, "user_preferences", {}).get("solution_suffix", "_loesung") or "_loesung")
        if path_obj.stem.endswith(suffix):
            base_stem = path_obj.stem[: -len(suffix)]
            return path_obj.with_name(base_stem + path_obj.suffix)
        return path_obj

    def _computation_cache_for(self, input_path: Path):
        """Hasattr-guarded lookup of `_resolve_computation_cache` (defined in the
        preview mixin, `blatt_ui_preview.py`) -- keeps this mixin usable on its
        own (e.g. in tests that only combine `BlattwerkAppExportMixin`) without
        requiring every test double to also implement the preview mixin.
        `None` is always a safe fallback (every downstream consumer treats it
        as "no cache, compute directly")."""
        resolver = getattr(self, "_resolve_computation_cache", None)
        return resolver(input_path) if resolver is not None else None

    def _export_target_policy(self) -> ExportTargetPolicy:
        """Policy fuer gesperrte Zieldateien: Einstellung plus OS-Probe (UI injiziert Adapter).

        `app/core` importiert `app/storage` nie; deshalb erzeugt die UI hier die Probe
        und gibt sie ueber die Build-Requests (bzw. direkt) an jeden Exporteur weiter.
        """
        preferences = getattr(self, "user_preferences", {}) or {}
        lock_policy = _normalize_choice(
            str(preferences.get("export_locked_target_policy", LOCK_POLICY_ERROR)),
            set(LOCK_POLICIES),
            LOCK_POLICY_ERROR,
        )
        return ExportTargetPolicy(lock_policy=lock_policy, probe=default_lock_probe())

    def _worksheet_build_request(
        self,
        *,
        input_path: Path,
        output_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
        black_screen_mode: str = "none",
        presentation_section_separator: str | None = None,
        presentation_hide_future_sections: bool | None = None,
        presentation_ignore_framebreaks: bool = False,
        diagnostics_out=None,
    ):
        default_separator, default_hide_future = (
            self._current_presentation_footer_export_options()
        )
        return WorksheetBuildRequest(
            input_path=input_path,
            output_path=output_path,
            include_solutions=include_solutions,
            page_format=page_format,
            print_profile=contrast_profile,
            design=self._worksheet_design_options(),
            metadata_defaults=self._metadata_defaults_from_preferences(),
            copyright_text_override=self._copyright_text_from_preferences() or None,
            black_screen_mode=black_screen_mode,
            presentation_section_separator=(
                presentation_section_separator
                if presentation_section_separator is not None
                else default_separator
            ),
            presentation_hide_future_sections=(
                bool(presentation_hide_future_sections)
                if presentation_hide_future_sections is not None
                else default_hide_future
            ),
            presentation_ignore_framebreaks=bool(presentation_ignore_framebreaks),
            diagnostics_out=diagnostics_out,
            computation_cache=self._computation_cache_for(input_path),
            target_policy=self._export_target_policy(),
        )

    def _help_cards_build_request(
        self,
        *,
        input_path: Path,
        output_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
        add_running_elements: bool = True,
    ):
        return HelpCardsBuildRequest(
            input_path=input_path,
            output_path=output_path,
            include_solutions=include_solutions,
            page_format=page_format,
            print_profile=contrast_profile,
            design=self._worksheet_design_options(),
            add_running_elements=add_running_elements,
            metadata_defaults=self._metadata_defaults_from_preferences(),
            copyright_text_override=self._copyright_text_from_preferences() or None,
            computation_cache=self._computation_cache_for(input_path),
            target_policy=self._export_target_policy(),
        )
