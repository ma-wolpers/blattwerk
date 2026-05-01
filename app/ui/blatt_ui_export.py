"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile
import fitz
from PIL import Image
from tkinter import messagebox

from .export_dialog import LernhilfenExportDialog, WorksheetExportDialog
from ..core.build_requests import (
    HelpCardsBuildRequest,
    WorksheetBuildRequest,
    build_help_cards_from_request,
    build_worksheet_from_request,
)
from ..core.blatt_kern_help_render import collect_help_blocks
from ..core.blatt_validator import inspect_markdown_text
from ..core.blatt_kern_shared import normalize_document_mode, split_front_matter
from ..core.diagnostic_warnings import build_warning_payload
from ..core.export_path_guardrails import validate_export_output_path
from .help_card_image_trim import trim_lernhilfe_image


class BlattwerkAppExportMixin:
    """Stellt Export-Workflows für PDF/HTML/PNG/ZIP bereit."""

    def _detect_document_mode(self, input_path: Path) -> str:
        """Resolve document mode from frontmatter with robust fallback."""
        try:
            text = input_path.read_text(encoding="utf-8")
            meta, _content = split_front_matter(text)
        except Exception:
            return "worksheet"
        return normalize_document_mode((meta or {}).get("mode"), default="worksheet")

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

        warning_payload = build_warning_payload(input_path, "Export")
        if warning_payload is None or warning_payload["count"] <= 0:
            return

        messagebox.showwarning(
            warning_payload["title"],
            "Export laeuft weiter, aber es gibt Warnungen:\n\n" + warning_payload["message"],
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

    def _worksheet_build_request(
        self,
        *,
        input_path: Path,
        output_path: Path,
        include_solutions: bool,
        page_format: str,
        contrast_profile: str,
        black_screen_mode: str = "none",
    ):
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
        )

    def _export_pdf(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        mode: str,
        contrast_profile: str,
        black_screen_mode: str = "none",
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
                    black_screen_mode=black_screen_mode,
                )
            )
            out_solution = build_worksheet_from_request(
                self._worksheet_build_request(
                    input_path=input_path,
                    output_path=solution_path,
                    include_solutions=True,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                    black_screen_mode=black_screen_mode,
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
                black_screen_mode=black_screen_mode,
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
        black_screen_mode: str = "none",
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
                    black_screen_mode=black_screen_mode,
                )
            )
            out_solution = build_worksheet_from_request(
                self._worksheet_build_request(
                    input_path=input_path,
                    output_path=solution_path,
                    include_solutions=True,
                    page_format=page_format,
                    contrast_profile=contrast_profile,
                    black_screen_mode=black_screen_mode,
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
                black_screen_mode=black_screen_mode,
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
        black_screen_mode: str = "none",
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
                    metadata_defaults=self._metadata_defaults_from_preferences(),
                    copyright_text_override=self._copyright_text_from_preferences() or None,
                    black_screen_mode=black_screen_mode,
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
        black_screen_mode: str = "none",
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
                black_screen_mode=black_screen_mode,
            )
            self._export_png_zip_single(
                input_path,
                solution_path,
                include_solutions=True,
                page_format=page_format,
                contrast_profile=contrast_profile,
                worksheet_design=worksheet_design,
                black_screen_mode=black_screen_mode,
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
            black_screen_mode=black_screen_mode,
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
                    add_running_elements=False,
                )
            )

            created_files = []
            with fitz.open(temp_pdf) as doc:
                page_count = len(doc)
                for index in range(page_count):
                    page = doc.load_page(index)
                    pix = page.get_pixmap(dpi=200, alpha=False)
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    image = trim_lernhilfe_image(image)

                    if page_count == 1:
                        target_file = output_path
                    else:
                        target_file = output_path.with_name(
                            f"{output_path.stem}_{index + 1:02d}{output_path.suffix}"
                        )

                    image.save(target_file)
                    created_files.append(target_file)

        return created_files

    def _export_help_cards_pdf(
        self,
        input_path: Path,
        output_path: Path,
        page_format: str,
        contrast_profile: str,
    ):
        """Export help cards pdf as one paginated document."""

        output_path = validate_export_output_path(
            output_path.with_suffix(".pdf"),
            allowed_suffixes={".pdf"},
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_file = build_help_cards_from_request(
            self._help_cards_build_request(
                input_path=input_path,
                output_path=output_path,
                include_solutions=False,
                page_format=page_format,
                contrast_profile=contrast_profile,
                add_running_elements=False,
            )
        )
        return [out_file]

    def _export_help_cards_png_zip(
        self,
        input_path: Path,
        output_zip_path: Path,
        page_format: str,
        contrast_profile: str,
    ):
        """Export help cards as PNG files bundled in one ZIP archive."""

        output_zip_path = validate_export_output_path(
            output_zip_path.with_suffix(".zip"),
            allowed_suffixes={".zip"},
        )
        output_zip_path.parent.mkdir(parents=True, exist_ok=True)

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
                    add_running_elements=False,
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
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    image = trim_lernhilfe_image(image)
                    image.save(png_path)
                    archive.write(png_path, arcname=png_name)

        return [output_zip_path]

    def open_export_dialog(self):
        """Compatibility wrapper that opens worksheet export dialog."""

        self.open_worksheet_export_dialog()

    def open_worksheet_export_dialog(self):
        """Öffnet den dedizierten Arbeitsblatt-Exportdialog."""

        input_path = self._validate_input()
        if not input_path:
            return

        default_mode = "both"
        preferences = getattr(self, "user_preferences", {})
        default_mode = str(preferences.get("default_export_mode", default_mode) or default_mode)
        if default_mode not in {"worksheet", "solution", "both"}:
            default_mode = "both"
        document_mode = self._detect_document_mode(input_path)
        allow_mode_selection = document_mode != "presentation"
        if not allow_mode_selection:
            default_mode = "worksheet"

        default_black_screen = str(
            preferences.get("default_export_black_screen", "none") or "none"
        ).strip().lower()
        if default_black_screen not in {"none", "before", "after", "both"}:
            default_black_screen = "none"
        default_format = str(preferences.get("default_export_format", preferences.get("default_export_page_format", "pdf")) or "pdf")
        if default_format not in {"pdf", "html", "png", "pngzip"}:
            default_format = "pdf"

        dialog = WorksheetExportDialog(
            self.root,
            input_path=input_path,
            default_format=default_format,
            default_mode=default_mode,
            theme_key=self.theme_var.get(),
            initial_output_dir=self._get_initial_dialog_dir("export_output"),
            worksheet_label=str(preferences.get("worksheet_label", "Aufgaben") or "Aufgaben"),
            solution_label=str(preferences.get("solution_label", "Loesung") or "Loesung"),
            solution_suffix=str(preferences.get("solution_suffix", "_loesung") or "_loesung"),
            allow_mode_selection=allow_mode_selection,
            black_screen_default=default_black_screen,
        )
        if not dialog.result:
            return

        fmt = dialog.result["format"]
        mode = dialog.result["mode"]
        black_screen_mode = str(dialog.result.get("black_screen", "none") or "none").strip().lower()
        if black_screen_mode not in {"none", "before", "after", "both"}:
            black_screen_mode = "none"
        preferences = getattr(self, "user_preferences", {})
        preferred_page_format = str(preferences.get("default_export_page_format", "") or "").strip()
        if preferred_page_format in {
            "a4_portrait",
            "a5_landscape",
            "presentation_16_9",
            "presentation_16_10",
            "presentation_4_3",
        }:
            page_format = preferred_page_format
        else:
            page_format = self.preview_page_format_var.get()

        if document_mode == "presentation":
            mode = "worksheet"
            if page_format not in {
                "presentation_16_9",
                "presentation_16_10",
                "presentation_4_3",
            }:
                page_format = "presentation_16_9"
        contrast_profile = self.preview_contrast_var.get()
        output_path = Path(dialog.result["output_path"])
        self._set_last_dialog_dir("export_output", output_path)

        try:
            self.status_var.set("Export läuft…")
            self.root.update_idletasks()
            self._show_export_diagnostics(input_path)

            if fmt == "pdf":
                out_files = self._export_pdf(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                )
            elif fmt == "html":
                out_files = self._export_html(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                )
            else:
                out_files = self._export_png_zip(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                )

            self.status_var.set("Export abgeschlossen")
            messagebox.showinfo(
                "Export erfolgreich",
                "Erstellt:\n" + "\n".join(str(path) for path in out_files),
            )
        except Exception as error:
            self.status_var.set("Export fehlgeschlagen")
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{error}")

    def open_lernhilfen_export_dialog(self):
        """Öffnet den dedizierten Lernhilfen-Exportdialog."""

        input_path = self._validate_input()
        if not input_path:
            return

        if not self._current_preview_has_lernhilfen(input_path):
            return

        preferences = getattr(self, "user_preferences", {})
        default_format = str(preferences.get("default_export_format", preferences.get("default_export_page_format", "pdf")) or "pdf")
        if default_format not in {"pdf", "png", "pngzip"}:
            default_format = "pdf"

        dialog = LernhilfenExportDialog(
            self.root,
            input_path=input_path,
            default_format=default_format,
            theme_key=self.theme_var.get(),
            initial_output_dir=self._get_initial_dialog_dir("export_output"),
        )
        if not dialog.result:
            return

        fmt = dialog.result["format"]
        preferences = getattr(self, "user_preferences", {})
        preferred_page_format = str(preferences.get("default_export_page_format", "") or "").strip()
        if preferred_page_format in {"a4_portrait", "a5_landscape"}:
            page_format = preferred_page_format
        else:
            page_format = self.preview_page_format_var.get()
        contrast_profile = self.preview_contrast_var.get()
        output_path = Path(dialog.result["output_path"])
        self._set_last_dialog_dir("export_output", output_path)

        try:
            self.status_var.set("Lernhilfen-Export läuft…")
            self.root.update_idletasks()
            self._show_export_diagnostics(input_path)

            if fmt == "pdf":
                out_files = self._export_help_cards_pdf(
                    input_path, output_path, page_format, contrast_profile
                )
            elif fmt == "png":
                out_files = self._export_help_cards_png(
                    input_path, output_path, page_format, contrast_profile
                )
            elif fmt == "pngzip":
                out_files = self._export_help_cards_png_zip(
                    input_path, output_path, page_format, contrast_profile
                )
            else:
                raise ValueError("Lernhilfen unterstützen nur PDF, PNG oder PNG (ZIP).")

            self.status_var.set("Lernhilfen-Export abgeschlossen")
            messagebox.showinfo(
                "Export erfolgreich",
                "Erstellt:\n" + "\n".join(str(path) for path in out_files),
            )
        except Exception as error:
            self.status_var.set("Lernhilfen-Export fehlgeschlagen")
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{error}")
