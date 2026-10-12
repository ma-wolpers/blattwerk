"""Dokument-Exporte als Bilder und Folien: PNG, PNG-ZIP und PPTX.
"""

from __future__ import annotations

from pathlib import Path
from ..core.document_export_build import (
    export_document_png,
    export_document_png_zip,
)
from ..core.kurzentwurf_settings import (
    kurzentwurf_runtime_options_from_preferences,
)
from ..core.export_path_guardrails import validate_export_output_path
from ..core.blatt_kern_pptx_export import build_presentation_pptx


class BlattwerkAppExportImagesMixin:
    """Schreibt ein Dokument als PNG, PNG-ZIP oder PPTX."""

    def _export_png(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
        black_screen_mode: str = "none",
        presentation_ignore_framebreaks: bool = False,
        compile_diagnostics=None,
    ):
        """Export png."""
        worksheet_design = self._worksheet_design_options()
        document_type = self._detect_document_type(input_path)
        preferences = getattr(self, "user_preferences", {})
        kurzentwurf_options = kurzentwurf_runtime_options_from_preferences(preferences)
        metadata_defaults = self._metadata_defaults_from_preferences()
        copyright_override = self._copyright_text_from_preferences() or None
        section_separator, hide_future_sections = self._current_presentation_footer_export_options()

        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)
            computation_cache = self._computation_cache_for(input_path)
            out_worksheet = export_document_png(
                input_path=input_path,
                output_path=worksheet_path,
                document_type=document_type,
                include_solutions=False,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=section_separator,
                presentation_hide_future_sections=hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
                kurzentwurf_options=kurzentwurf_options,
                computation_cache=computation_cache,
            )
            out_solution = export_document_png(
                input_path=input_path,
                output_path=solution_path,
                document_type=document_type,
                include_solutions=True,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=section_separator,
                presentation_hide_future_sections=hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
                kurzentwurf_options=kurzentwurf_options,
                computation_cache=computation_cache,
            )
            return [*out_worksheet, *out_solution]

        include_solutions = mode == "solution"
        target = self._with_solution_suffix(output_path) if include_solutions else output_path
        return export_document_png(
            input_path=input_path,
            output_path=target,
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
            presentation_ignore_framebreaks=presentation_ignore_framebreaks,
            diagnostics_out=compile_diagnostics,
            kurzentwurf_options=kurzentwurf_options,
            computation_cache=self._computation_cache_for(input_path),
        )

    def _export_png_zip(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
        black_screen_mode: str = "none",
        presentation_ignore_framebreaks: bool = False,
        compile_diagnostics=None,
    ):
        """Export png zip."""
        worksheet_design = self._worksheet_design_options()
        document_type = self._detect_document_type(input_path)
        preferences = getattr(self, "user_preferences", {})
        kurzentwurf_options = kurzentwurf_runtime_options_from_preferences(preferences)
        metadata_defaults = self._metadata_defaults_from_preferences()
        copyright_override = self._copyright_text_from_preferences() or None
        section_separator, hide_future_sections = self._current_presentation_footer_export_options()
        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)

            computation_cache = self._computation_cache_for(input_path)
            export_document_png_zip(
                input_path=input_path,
                output_path=worksheet_path,
                document_type=document_type,
                include_solutions=False,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=section_separator,
                presentation_hide_future_sections=hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
                kurzentwurf_options=kurzentwurf_options,
                computation_cache=computation_cache,
            )
            export_document_png_zip(
                input_path=input_path,
                output_path=solution_path,
                document_type=document_type,
                include_solutions=True,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
                metadata_defaults=metadata_defaults,
                copyright_override=copyright_override,
                black_screen_mode=black_screen_mode,
                presentation_section_separator=section_separator,
                presentation_hide_future_sections=hide_future_sections,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
                kurzentwurf_options=kurzentwurf_options,
                computation_cache=computation_cache,
            )
            return [worksheet_path, solution_path]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)

        out_file = export_document_png_zip(
            input_path=input_path,
            output_path=target,
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
            presentation_ignore_framebreaks=presentation_ignore_framebreaks,
            diagnostics_out=compile_diagnostics,
            kurzentwurf_options=kurzentwurf_options,
            computation_cache=self._computation_cache_for(input_path),
        )
        return [out_file]

    def _export_pptx(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
        black_screen_mode: str = "none",
        presentation_ignore_framebreaks: bool = False,
        compile_diagnostics=None,
        editable_pptx: bool = False,
    ):
        """Export as PPTX. `editable_pptx=True` attempts the experimental
        editable export (real text-boxes/image-shapes, see
        `blatt_kern_pptx_export_editable.py`) with an automatic fallback
        to the raster path (one slide-image per page, 200 DPI) -- default
        `False` always uses the raster path directly."""
        worksheet_design = self._worksheet_design_options()
        section_separator, hide_future_sections = (
            self._current_presentation_footer_export_options()
        )
        metadata_defaults = {}
        if hasattr(self, "_metadata_defaults_from_preferences"):
            metadata_defaults = self._metadata_defaults_from_preferences()
        copyright_override = None
        if hasattr(self, "_copyright_text_from_preferences"):
            copyright_override = self._copyright_text_from_preferences() or None

        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)
            for target, include_sol in [(worksheet_path, False), (solution_path, True)]:
                if target.suffix.lower() != ".pptx":
                    target = target.with_suffix(".pptx")
                validate_export_output_path(target, allowed_suffixes={".pptx"})
                build_presentation_pptx(
                    input_path=input_path,
                    output_path=target,
                    page_format=page_format,
                    print_profile=contrast_profile,
                    design=worksheet_design,
                    include_solutions=include_sol,
                    black_screen_mode=black_screen_mode,
                    presentation_section_separator=section_separator,
                    presentation_hide_future_sections=hide_future_sections,
                    presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                    metadata_defaults=metadata_defaults,
                    copyright_text_override=copyright_override,
                    diagnostics_out=compile_diagnostics,
                    editable=editable_pptx,
                )
            return [worksheet_path, solution_path]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)
        if target.suffix.lower() != ".pptx":
            target = target.with_suffix(".pptx")
        validate_export_output_path(target, allowed_suffixes={".pptx"})
        build_presentation_pptx(
            input_path=input_path,
            output_path=target,
            page_format=page_format,
            print_profile=contrast_profile,
            design=worksheet_design,
            include_solutions=include_solutions,
            black_screen_mode=black_screen_mode,
            presentation_section_separator=section_separator,
            presentation_hide_future_sections=hide_future_sections,
            presentation_ignore_framebreaks=presentation_ignore_framebreaks,
            metadata_defaults=metadata_defaults,
            copyright_text_override=copyright_override,
            diagnostics_out=compile_diagnostics,
            editable=editable_pptx,
        )
        return [target]
