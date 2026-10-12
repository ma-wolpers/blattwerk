"""Dokument-Exporte als Seiten: PDF und HTML.
"""

from __future__ import annotations

from pathlib import Path
from ..core.document_export_build import export_document_html, export_document_pdf
from ..core.kurzentwurf_settings import (
    kurzentwurf_runtime_options_from_preferences,
)


class BlattwerkAppExportDocumentsMixin:
    """Schreibt ein Dokument als PDF oder HTML."""

    def _export_pdf(
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
        """Export pdf."""
        document_type = self._detect_document_type(input_path)
        preferences = getattr(self, "user_preferences", {})
        kurzentwurf_options = kurzentwurf_runtime_options_from_preferences(preferences)
        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)

            out_worksheet = export_document_pdf(
                input_path=input_path,
                output_path=worksheet_path,
                document_type=document_type,
                include_solutions=False,
                kurzentwurf_options=kurzentwurf_options,
                worksheet_request=self._worksheet_build_request(
                    input_path=input_path,
                    output_path=worksheet_path,
                    include_solutions=False,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                    diagnostics_out=compile_diagnostics,
                ),
            )
            out_solution = export_document_pdf(
                input_path=input_path,
                output_path=solution_path,
                document_type=document_type,
                include_solutions=True,
                kurzentwurf_options=kurzentwurf_options,
                worksheet_request=self._worksheet_build_request(
                    input_path=input_path,
                    output_path=solution_path,
                    include_solutions=True,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                    diagnostics_out=compile_diagnostics,
                ),
            )
            return [out_worksheet, out_solution]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)

        out_file = export_document_pdf(
            input_path=input_path,
            output_path=target,
            document_type=document_type,
            include_solutions=include_solutions,
            kurzentwurf_options=kurzentwurf_options,
            worksheet_request=self._worksheet_build_request(
                input_path=input_path,
                output_path=target,
                include_solutions=include_solutions,
                page_format=page_format,
                contrast_profile=contrast_profile,
                black_screen_mode=black_screen_mode,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
            ),
        )
        return [out_file]

    def _export_html(
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
        """Export html."""
        document_type = self._detect_document_type(input_path)
        preferences = getattr(self, "user_preferences", {})
        kurzentwurf_options = kurzentwurf_runtime_options_from_preferences(preferences)
        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)

            out_worksheet = export_document_html(
                input_path=input_path,
                output_path=worksheet_path,
                document_type=document_type,
                include_solutions=False,
                kurzentwurf_options=kurzentwurf_options,
                worksheet_request=self._worksheet_build_request(
                    input_path=input_path,
                    output_path=worksheet_path,
                    include_solutions=False,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                    diagnostics_out=compile_diagnostics,
                ),
            )
            out_solution = export_document_html(
                input_path=input_path,
                output_path=solution_path,
                document_type=document_type,
                include_solutions=True,
                kurzentwurf_options=kurzentwurf_options,
                worksheet_request=self._worksheet_build_request(
                    input_path=input_path,
                    output_path=solution_path,
                    include_solutions=True,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                    diagnostics_out=compile_diagnostics,
                ),
            )
            return [out_worksheet, out_solution]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)

        out_file = export_document_html(
            input_path=input_path,
            output_path=target,
            document_type=document_type,
            include_solutions=include_solutions,
            kurzentwurf_options=kurzentwurf_options,
            worksheet_request=self._worksheet_build_request(
                input_path=input_path,
                output_path=target,
                include_solutions=include_solutions,
                page_format=page_format,
                contrast_profile=contrast_profile,
                black_screen_mode=black_screen_mode,
                presentation_ignore_framebreaks=presentation_ignore_framebreaks,
                diagnostics_out=compile_diagnostics,
            ),
        )
        return [out_file]
