"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile
import fitz
from tkinter import messagebox

from .export_dialog import ExportDialog
from ..core.build_requests import (
    HelpCardsBuildRequest,
    WorksheetBuildRequest,
    build_help_cards_from_request,
    build_worksheet_from_request,
)
from ..core.diagnostic_warnings import build_warning_payload
from ..core.export_path_guardrails import validate_export_output_path


class BlattwerkAppExportMixin:
    """Stellt Export-Workflows für PDF/HTML/PNG/ZIP bereit."""

    def _show_export_diagnostics(self, input_path: Path):
        """Zeigt nicht-blockierende Warnungen vor dem Export an."""
        warning_payload = build_warning_payload(input_path, "Export")
        if warning_payload is None or warning_payload["count"] <= 0:
            return

        messagebox.showwarning(
            warning_payload["title"],
            "Export laeuft weiter, aber es gibt Warnungen:\n\n" + warning_payload["message"],
        )

    @staticmethod
    def _with_solution_suffix(path_obj: Path):
        """With solution suffix."""
        if path_obj.stem.endswith("_loesung"):
            return path_obj
        return path_obj.with_name(path_obj.stem + "_loesung" + path_obj.suffix)

    @staticmethod
    def _without_solution_suffix(path_obj: Path):
        """Without solution suffix."""
        if path_obj.stem.endswith("_loesung"):
            base_stem = path_obj.stem[: -len("_loesung")]
            return path_obj.with_name(base_stem + path_obj.suffix)
        return path_obj

    def _worksheet_build_request(
        self,
        *,
        input_path: Path,
        output_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
    ):
        return WorksheetBuildRequest(
            input_path=input_path,
            output_path=output_path,
            include_solutions=include_solutions,
            page_format=page_format,
            print_profile=contrast_profile,
            design=self._worksheet_design_options(),
        )

    def _help_cards_build_request(
        self,
        *,
        input_path: Path,
        output_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
    ):
        return HelpCardsBuildRequest(
            input_path=input_path,
            output_path=output_path,
            include_solutions=include_solutions,
            page_format=page_format,
            print_profile=contrast_profile,
            design=self._worksheet_design_options(),
        )

    def _export_pdf(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
    ):
        """Export pdf."""
        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)

            out_worksheet = build_worksheet_from_request(
                self._worksheet_build_request(
                    input_path=input_path,
                    output_path=worksheet_path,
                    include_solutions=False,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                )
            )
            out_solution = build_worksheet_from_request(
                self._worksheet_build_request(
                    input_path=input_path,
                    output_path=solution_path,
                    include_solutions=True,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                )
            )
            return [out_worksheet, out_solution]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)

        out_file = build_worksheet_from_request(
            self._worksheet_build_request(
                input_path=input_path,
                output_path=target,
                include_solutions=include_solutions,
                page_format=page_format,
                contrast_profile=contrast_profile,
            )
        )
        return [out_file]

    def _export_html(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
    ):
        """Export html."""
        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)

            out_worksheet = build_worksheet_from_request(
                self._worksheet_build_request(
                    input_path=input_path,
                    output_path=worksheet_path,
                    include_solutions=False,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                )
            )
            out_solution = build_worksheet_from_request(
                self._worksheet_build_request(
                    input_path=input_path,
                    output_path=solution_path,
                    include_solutions=True,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                )
            )
            return [out_worksheet, out_solution]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)

        out_file = build_worksheet_from_request(
            self._worksheet_build_request(
                input_path=input_path,
                output_path=target,
                include_solutions=include_solutions,
                page_format=page_format,
                contrast_profile=contrast_profile,
            )
        )
        return [out_file]

    def _export_png_zip_single(
        self,
        input_path: Path,
        output_zip_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
        worksheet_design,
    ):
        """Exports one worksheet variant as PNG files inside a ZIP archive."""
        output_zip_path = validate_export_output_path(
            output_zip_path,
            allowed_suffixes={".zip"},
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            temp_pdf = tmp_dir_path / "source.pdf"
            build_worksheet_from_request(
                WorksheetBuildRequest(
                    input_path=input_path,
                    output_path=temp_pdf,
                    include_solutions=include_solutions,
                    page_format=page_format,
                    print_profile=contrast_profile,
                    design=worksheet_design,
                )
            )

            with (
                fitz.open(temp_pdf) as doc,
                zipfile.ZipFile(
                    output_zip_path, "w", compression=zipfile.ZIP_DEFLATED
                ) as archive,
            ):
                for idx in range(len(doc)):
                    page = doc.load_page(idx)
                    pix = page.get_pixmap(dpi=200, alpha=False)
                    png_name = f"page_{idx + 1:03d}.png"
                    png_path = tmp_dir_path / png_name
                    pix.save(png_path)
                    archive.write(png_path, arcname=png_name)

    def _export_png_zip(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
    ):
        """Export png zip."""
        worksheet_design = self._worksheet_design_options()
        if mode == "both":
            worksheet_path = self._without_solution_suffix(output_path)
            solution_path = self._with_solution_suffix(worksheet_path)

            self._export_png_zip_single(
                input_path,
                worksheet_path,
                include_solutions=False,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
            )
            self._export_png_zip_single(
                input_path,
                solution_path,
                include_solutions=True,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
            )
            return [worksheet_path, solution_path]

        include_solutions = mode == "solution"
        target = output_path
        if include_solutions:
            target = self._with_solution_suffix(target)

        self._export_png_zip_single(
            input_path,
            target,
            include_solutions=include_solutions,
            page_format=page_format,
            contrast_profile=contrast_profile,
            worksheet_design=worksheet_design,
        )
        return [target]

    def _export_help_cards_png(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        contrast_profile: str,
    ):
        """Export help cards png."""
        output_path = validate_export_output_path(
            output_path.with_suffix(".png"),
            allowed_suffixes={".png"},
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            temp_pdf = tmp_dir_path / "help_cards.pdf"
            build_help_cards_from_request(
                self._help_cards_build_request(
                    input_path=input_path,
                    output_path=temp_pdf,
                    include_solutions=False,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                )
            )

            created_files = []
            with fitz.open(temp_pdf) as doc:
                page_count = len(doc)
                for index in range(page_count):
                    page = doc.load_page(index)
                    pix = page.get_pixmap(dpi=200, alpha=False)

                    if page_count == 1:
                        target_file = output_path
                    else:
                        target_file = output_path.with_name(
                            f"{output_path.stem}_{index + 1:02d}{output_path.suffix}"
                        )

                    pix.save(target_file)
                    created_files.append(target_file)

        return created_files

    def open_export_dialog(self):
        """Öffnet den Exportdialog erst bei explizitem Klick auf Exportieren."""

        input_path = self._validate_input()
        if not input_path:
            return

        default_mode = "both"
        dialog = ExportDialog(
            self.root,
            input_path=input_path,
            default_format="pdf",
            default_mode=default_mode,
            theme_key=self.theme_var.get(),
            initial_output_dir=self._get_initial_dialog_dir("export_output"),
        )
        if not dialog.result:
            return

        fmt = dialog.result["format"]
        mode = dialog.result["mode"]
        page_format = self.preview_page_format_var.get()
        contrast_profile = self.preview_contrast_var.get()
        output_path = Path(dialog.result["output_path"])
        self._set_last_dialog_dir("export_output", output_path)

        try:
            self.status_var.set("Export läuft…")
            self.root.update_idletasks()
            self._show_export_diagnostics(input_path)

            if fmt == "pdf":
                out_files = self._export_pdf(
                    input_path, output_path, page_format, mode, contrast_profile
                )
            elif fmt == "html":
                out_files = self._export_html(
                    input_path, output_path, page_format, mode, contrast_profile
                )
            elif fmt == "png" and mode == "help_cards":
                out_files = self._export_help_cards_png(
                    input_path, output_path, page_format, contrast_profile
                )
            else:
                out_files = self._export_png_zip(
                    input_path, output_path, page_format, mode, contrast_profile
                )

            self.status_var.set("Export abgeschlossen")
            messagebox.showinfo(
                "Export erfolgreich",
                "Erstellt:\n" + "\n".join(str(path) for path in out_files),
            )
        except Exception as error:
            self.status_var.set("Export fehlgeschlagen")
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{error}")
