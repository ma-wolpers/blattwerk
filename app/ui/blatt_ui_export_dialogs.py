"""Exportdialoge fuer Arbeitsblatt/Klausur und Praesentation sowie der Erwartungshorizont.
"""

from __future__ import annotations

from pathlib import Path
from .dialog_services import messagebox
from .export_dialog import PresentationExportDialog, WorksheetExportDialog
from ..core.exam_expectation_horizon import build_expectation_horizon
from ..core.document_type_registry import coerce_preview_variant, spec_for_type
from .export_defaults import (
    _ALLOWED_EXPORT_MODES,
    _ALLOWED_BLACK_SCREEN_MODES,
    _ALLOWED_WORKSHEET_PAGE_FORMATS,
    _ALLOWED_PRESENTATION_PAGE_FORMATS,
    _normalize_choice,
    _resolve_export_default_format,
    _resolve_export_default_page_format,
)


class BlattwerkAppExportDialogsMixin:
    """Oeffnet die Exportdialoge und fuehrt den gewaehlten Export aus."""

    def open_export_dialog(self):
        """Open the worksheet or presentation export dialog based on the document type."""

        input_path = self._validate_input()
        if not input_path:
            return

        document_type = self._detect_document_type(input_path)
        if document_type is None:
            self.status_var.set(f"Unbekannte Dateiendung: {input_path.name}")
            return
        if spec_for_type(document_type).slide_layout:
            self.open_presentation_export_dialog(input_path=input_path)
            return

        self.open_worksheet_export_dialog(input_path=input_path)

    def open_worksheet_export_dialog(self, input_path: Path | None = None):
        """Öffnet den dedizierten Arbeitsblatt-Exportdialog."""

        input_path = input_path if input_path is not None else self._validate_input()
        if not input_path:
            return

        preferences = getattr(self, "user_preferences", {})

        preview_mode = _normalize_choice(
            self.preview_mode_var.get(),
            _ALLOWED_EXPORT_MODES,
            "worksheet",
        )
        document_type = self._detect_document_type(input_path)
        allow_mode_selection = self._solutions_renderable_for_type(document_type)
        # Die Vorschau-Ansicht ist Vorauswahl (gleiche Tokens, inkl. Erwartungshorizont bei Klausuren).
        default_mode = coerce_preview_variant(document_type, preview_mode) if allow_mode_selection else "worksheet"
        default_format = _resolve_export_default_format(preferences, "worksheet")
        default_page_format = _resolve_export_default_page_format(preferences, "worksheet")

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
            allow_expectation_horizon=bool(document_type) and spec_for_type(document_type).expectation_horizon,
        )
        if not dialog.result:
            return

        fmt = dialog.result["format"]
        mode = dialog.result["mode"]
        if mode == "expectation":
            self._export_expectation_horizon(input_path, Path(dialog.result["output_path"]))
            return
        black_screen_mode = "none"
        page_format = str(self.preview_page_format_var.get() or "").strip()
        if page_format not in _ALLOWED_WORKSHEET_PAGE_FORMATS:
            page_format = default_page_format
        contrast_profile = self.preview_contrast_var.get()
        output_path = Path(dialog.result["output_path"])
        self._set_last_dialog_dir("export_output", output_path)

        try:
            self.status_var.set("Export läuft…")
            self.root.update_idletasks()
            self._show_export_diagnostics(input_path)
            compile_diagnostics = []

            if fmt == "pdf":
                out_files = self._export_pdf(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    compile_diagnostics=compile_diagnostics,
                )
            elif fmt == "html":
                out_files = self._export_html(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    compile_diagnostics=compile_diagnostics,
                )
            elif fmt == "png":
                out_files = self._export_png(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    compile_diagnostics=compile_diagnostics,
                )
            else:
                out_files = self._export_png_zip(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    compile_diagnostics=compile_diagnostics,
                )

            self._show_compile_overflow_warnings(compile_diagnostics, "Export")

            self.status_var.set("Export abgeschlossen")
            messagebox.showinfo(
                "Export erfolgreich",
                "Erstellt:\n" + "\n".join(str(path) for path in out_files),
            )
        except Exception as error:
            self.status_var.set("Export fehlgeschlagen")
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{error}")

    def _export_expectation_horizon(self, input_path: Path, output_path: Path) -> None:
        """Exportiert den Erwartungshorizont einer Klausur (PDF/HTML); Punktfehler blockieren."""
        self._set_last_dialog_dir("export_output", output_path)
        try:
            self.status_var.set("Export läuft…")
            self.root.update_idletasks()
            compile_diagnostics = []
            out_file = build_expectation_horizon(
                input_path,
                output_path,
                diagnostics_out=compile_diagnostics,
                target_policy=self._export_target_policy(),
            )
            self._show_compile_overflow_warnings(compile_diagnostics, "Erwartungshorizont")
            self.status_var.set("Export abgeschlossen")
            messagebox.showinfo("Export erfolgreich", f"Erstellt:\n{out_file}")
        except Exception as error:
            self.status_var.set("Export fehlgeschlagen")
            messagebox.showerror("Fehler", f"Erwartungshorizont konnte nicht erstellt werden:\n{error}")

    def open_presentation_export_dialog(self, input_path: Path | None = None):
        """Oeffnet den dedizierten Praesentations-Exportdialog."""

        input_path = input_path if input_path is not None else self._validate_input()
        if not input_path:
            return

        preferences = getattr(self, "user_preferences", {})
        default_black_screen = _normalize_choice(
            self.preview_black_screen_var.get(),
            _ALLOWED_BLACK_SCREEN_MODES,
            "none",
        )
        default_format = _resolve_export_default_format(preferences, "presentation")
        default_page_format = _resolve_export_default_page_format(preferences, "presentation")

        dialog = PresentationExportDialog(
            self.root,
            input_path=input_path,
            default_format=default_format,
            black_screen_default=default_black_screen,
            theme_key=self.theme_var.get(),
            initial_output_dir=self._get_initial_dialog_dir("export_output"),
        )
        if not dialog.result:
            return

        fmt = dialog.result["format"]
        mode = "worksheet"
        black_screen_mode = str(dialog.result.get("black_screen", "none") or "none").strip().lower()
        black_screen_mode = _normalize_choice(
            black_screen_mode,
            _ALLOWED_BLACK_SCREEN_MODES,
            "none",
        )
        ignore_framebreaks = bool(dialog.result.get("ignore_framebreaks", False))
        editable_pptx = bool(dialog.result.get("editable_pptx", False))
        page_format = str(self.preview_page_format_var.get() or "").strip()
        if page_format not in _ALLOWED_PRESENTATION_PAGE_FORMATS:
            page_format = default_page_format
        contrast_profile = self.preview_contrast_var.get()
        output_path = Path(dialog.result["output_path"])
        self._set_last_dialog_dir("export_output", output_path)

        try:
            self.status_var.set("Export läuft…")
            self.root.update_idletasks()
            self._show_export_diagnostics(input_path)
            compile_diagnostics = []

            if fmt == "pdf":
                out_files = self._export_pdf(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=ignore_framebreaks,
                    compile_diagnostics=compile_diagnostics,
                )
            elif fmt == "html":
                out_files = self._export_html(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=ignore_framebreaks,
                    compile_diagnostics=compile_diagnostics,
                )
            elif fmt == "png":
                out_files = self._export_png(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=ignore_framebreaks,
                    compile_diagnostics=compile_diagnostics,
                )
            elif fmt == "pptx":
                out_files = self._export_pptx(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=ignore_framebreaks,
                    compile_diagnostics=compile_diagnostics,
                    editable_pptx=editable_pptx,
                )
            else:
                out_files = self._export_png_zip(
                    input_path,
                    output_path,
                    page_format,
                    mode,
                    contrast_profile,
                    black_screen_mode=black_screen_mode,
                    presentation_ignore_framebreaks=ignore_framebreaks,
                    compile_diagnostics=compile_diagnostics,
                )

            self._show_compile_overflow_warnings(compile_diagnostics, "Export")

            self.status_var.set("Export abgeschlossen")
            messagebox.showinfo(
                "Export erfolgreich",
                "Erstellt:\n" + "\n".join(str(path) for path in out_files),
            )
        except Exception as error:
            self.status_var.set("Export fehlgeschlagen")
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{error}")
