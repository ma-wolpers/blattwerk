"""Lernhilfen-Export: Karten als PNG, PDF oder PNG-ZIP und der Lernhilfen-Exportdialog.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile
from .dialog_services import messagebox
from .export_dialog import LernhilfenExportDialog
from .help_card_images import render_help_card_images
from ..core.build_requests import build_help_cards_from_request
from ..core.export_path_guardrails import validate_export_output_path
from .export_defaults import (
    _ALLOWED_LERNHILFEN_EXPORT_FORMATS,
    _ALLOWED_WORKSHEET_PAGE_FORMATS,
    _normalize_choice,
)


class BlattwerkAppExportHelpCardsMixin:
    """Exportiert Lernhilfe-Karten."""

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
            target_policy=self._export_target_policy(),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        card_images = self._render_lernhilfe_card_images(
            input_path=input_path,
            contrast_profile=contrast_profile,
        )

        created_files = []
        card_count = len(card_images)
        for index, image in enumerate(card_images, start=1):
            if card_count == 1:
                target_file = output_path
            else:
                target_file = output_path.with_name(
                    f"{output_path.stem}_{index:02d}{output_path.suffix}"
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
            target_policy=self._export_target_policy(),
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
            target_policy=self._export_target_policy(),
        )
        output_zip_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            card_images = self._render_lernhilfe_card_images(
                input_path=input_path,
                contrast_profile=contrast_profile,
            )

            with zipfile.ZipFile(
                output_zip_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for idx, image in enumerate(card_images, start=1):
                    png_name = f"lernhilfe_{idx:03d}.png"
                    png_path = tmp_dir_path / png_name
                    image.save(png_path)
                    archive.write(png_path, arcname=png_name)

        return [output_zip_path]

    def _render_lernhilfe_card_images(self, *, input_path: Path, contrast_profile: str):
        """Rendert jede sichtbare Lernhilfe als eigenes, beschnittenes Bild (200 dpi).

        Das Seitenformat wählt `help_card_images.render_help_card_images` je
        Karte selbst (kleinstes passendes aus A6/A5/A4), unabhängig vom
        Seitenformat des Arbeitsblatts -- lange Karten werden so nicht mehr
        nach der ersten A6-Seite abgeschnitten. Der kombinierte
        Mehrkarten-PDF-Export (`_export_help_cards_pdf`) behält dagegen das
        gewählte Format für die physische Seite bei.
        """
        return render_help_card_images(
            input_path,
            include_solutions=False,
            contrast_profile=contrast_profile,
            design=self._worksheet_design_options(),
            dpi=200,
            block_on_critical=True,
        )

    def open_lernhilfen_export_dialog(self):
        """Öffnet den dedizierten Lernhilfen-Exportdialog."""

        input_path = self._validate_input()
        if not input_path:
            return

        if not self._current_preview_has_lernhilfen(input_path):
            return

        preferences = getattr(self, "user_preferences", {})
        default_format = _normalize_choice(
            preferences.get("default_export_format_worksheet", preferences.get("default_export_format", "pdf")),
            _ALLOWED_LERNHILFEN_EXPORT_FORMATS,
            "pdf",
        )

        open_tab_paths = self._collect_open_document_paths()

        dialog = LernhilfenExportDialog(
            self.root,
            input_path=input_path,
            default_format=default_format,
            theme_key=self.theme_var.get(),
            initial_output_dir=self._get_initial_dialog_dir("export_output"),
            allow_all_tabs_export=len(open_tab_paths) > 1,
        )
        if not dialog.result:
            return

        fmt = dialog.result["format"]
        preferences = getattr(self, "user_preferences", {})
        preferred_page_format = str(
            preferences.get(
                "default_export_page_format_worksheet",
                preferences.get("default_export_page_format", ""),
            )
            or ""
        ).strip()
        if preferred_page_format in _ALLOWED_WORKSHEET_PAGE_FORMATS:
            page_format = preferred_page_format
        else:
            page_format = self.preview_page_format_var.get()
        contrast_profile = self.preview_contrast_var.get()
        output_path = Path(dialog.result["output_path"])
        self._set_last_dialog_dir("export_output", output_path)

        try:
            self.status_var.set("Lernhilfen-Export läuft…")
            self.root.update_idletasks()

            if dialog.result.get("export_all_tabs"):
                out_files = self._export_help_cards_for_multiple_documents(
                    open_tab_paths, output_path, page_format, contrast_profile
                )
            else:
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
