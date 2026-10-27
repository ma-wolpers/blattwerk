"""Lernhilfen-Export: Karten als PNG, PDF oder PNG-ZIP und der Lernhilfen-Exportdialog.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile
import fitz
from PIL import Image
from .dialog_services import messagebox
from .export_dialog import LernhilfenExportDialog
from ..core.build_requests import build_help_cards_from_request
from ..core.blatt_kern_help_render import (
    collect_labeled_help_blocks,
    render_help_cards_html,
)
from ..core.blatt_validator import inspect_markdown_text
from ..core.blatt_kern_shared import split_front_matter
from ..core.blatt_kern_io_html import (
    absolutize_local_image_sources,
    apply_image_size_options,
)
from ..core.blatt_kern_io_pdf import write_pdf_from_html
from ..core.export_path_guardrails import validate_export_output_path
from .help_card_image_trim import trim_lernhilfe_image
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

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            card_images = self._render_lernhilfe_card_images(
                input_path=input_path,
                page_format=page_format,
                contrast_profile=contrast_profile,
                tmp_dir_path=tmp_dir_path,
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
                page_format=page_format,
                contrast_profile=contrast_profile,
                tmp_dir_path=tmp_dir_path,
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

    def _render_lernhilfe_card_images(
        self,
        *,
        input_path: Path,
        page_format: str,
        contrast_profile: str,
        tmp_dir_path: Path,
    ):
        """Render each visible lernhilfe card as its own trimmed PNG-ready image.

        `page_format` (Aufrufer-Präferenz, i. d. R. a4/a5) wird hier bewusst
        ignoriert: Einzelkarten werden immer in DIN-A6-Breite gerendert
        (steuert u. a. `document_header_size`/`solution_badge_size` über
        `PAGE_LAYOUTS["a6_portrait"]`), unabhängig vom allgemeinen
        Seitenformat-Preference des Nutzers. Der kombinierte Mehrkarten-PDF-
        Export (`_export_help_cards_pdf`) behält dagegen das gewählte Format
        für die physische Seite bei.
        """
        page_format = "a6_portrait"

        text = input_path.read_text(encoding="utf-8")
        meta, _content = split_front_matter(text)
        inspected = inspect_markdown_text(text)
        help_cards = collect_labeled_help_blocks(
            meta,
            inspected.blocks,
            include_solutions=False,
            document_type="worksheet",
        )
        if not help_cards:
            return []

        worksheet_design = self._worksheet_design_options()
        color_profile = worksheet_design.color_profile
        font_profile = worksheet_design.font_profile
        font_size_profile = worksheet_design.font_size_profile

        images = []
        for index, card in enumerate(help_cards, start=1):
            options = dict(card.get("options") or {})
            label = str(card.get("label") or "").strip()
            if label:
                options["tag"] = label

            block_type = str(card.get("block_type") or "help").strip() or "help"
            block_content = str(card.get("content") or "")
            html = render_help_cards_html(
                meta,
                [(block_type, options, block_content)],
                include_solutions=False,
                page_format=page_format,
                print_profile=contrast_profile,
                color_profile=color_profile,
                font_profile=font_profile,
                font_size_profile=font_size_profile,
            )
            html = absolutize_local_image_sources(html, input_path.parent)
            html = apply_image_size_options(html)

            temp_pdf = tmp_dir_path / f"help_card_{index:03d}.pdf"
            write_pdf_from_html(html, temp_pdf)

            with fitz.open(temp_pdf) as doc:
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=200, alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                images.append(trim_lernhilfe_image(image))

        return images

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
