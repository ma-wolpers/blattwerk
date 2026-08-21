"""Orchestriert den Export der Lernhilfen aller aktuell geöffneten Dokument-Tabs.

Trennt bewusst drei Verantwortlichkeiten von der bestehenden
Einzel-Dokument-Exportlogik (`blatt_ui_export.py`, unverändert
wiederverwendet über `self._help_cards_build_request`/
`build_help_cards_from_request`): Tabs einsammeln, pro Dokument bauen
und erst bei vollständigem Erfolg ein ZIP atomar an den Zielpfad
verschieben. Kein UI-Code -- die Dialog-Checkbox lebt in
`export_dialog.py`, der Aufruf-Einstieg in `open_lernhilfen_export_dialog`
(`blatt_ui_export.py`).
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from ..core.build_requests import build_help_cards_from_request
from ..core.export_path_guardrails import validate_export_output_path


class BlattwerkAppExportMultiMixin:
    """Sammelt offene Tabs ein und exportiert ihre Lernhilfen atomar als ein ZIP."""

    def _collect_open_document_paths(self) -> list[Path]:
        """Liefert die Pfade aller aktuell in Tabs geöffneten Dokumente, in Tab-Reihenfolge.

        Bewusst ohne Deduplizierung: zeigen zwei Tabs auf dieselbe Datei,
        werden beide berücksichtigt (spiegelt den tatsächlichen Tab-Zustand,
        nicht eine bereinigte Dateimenge).
        """
        paths: list[Path] = []
        for tab_id in self._document_tab_order:
            tab_state = self.document_tabs.get(tab_id)
            if not tab_state:
                continue
            raw_path = tab_state.get("path")
            if not raw_path:
                continue
            paths.append(Path(raw_path))
        return paths

    def _export_help_cards_for_multiple_documents(
        self,
        input_paths: list[Path],
        output_zip_path: Path,
        page_format: str,
        contrast_profile: str,
    ) -> list[Path]:
        """Exportiert die Lernhilfen aller übergebenen Dokumente als ein ZIP mit je einer PDF-Datei.

        Atomarer Ablauf: zuerst wird der aktive Tab auf die Platte
        durchgereicht (falls gerade ungespeicherte Änderungen im
        Editor-Puffer stehen -- der aktive Tab ist der einzige, der von der
        Festplatte abweichen kann, da nicht-aktive Tabs keinen eigenen
        In-Memory-Puffer haben, siehe `_save_editor_content`). Danach wird
        JEDES Dokument gebaut, BEVOR irgendeine Zieldatei entsteht: schlägt
        auch nur ein Build fehl (z. B. blockierende Validierungsfehler),
        bricht der gesamte Vorgang ohne sichtbares Teilartefakt ab. Ein
        Dokument ohne Lernhilfen-Blöcke ist dagegen kein Fehler und wird
        übersprungen. Erst wenn alle Builds erfolgreich sind, wird das ZIP
        vollständig in einem Temp-Verzeichnis geschrieben und danach in
        einem Zug an den Zielpfad verschoben.
        """
        if getattr(self, "_editor_has_unsaved_changes", False):
            self._save_editor_content()

        include_solutions = self.preview_mode_var.get() == "solution"

        buildable_paths: list[Path] = []
        skipped_names: list[str] = []
        for input_path in input_paths:
            if self._count_visible_lernhilfen(input_path, include_solutions=include_solutions) == 0:
                skipped_names.append(input_path.name)
                continue
            buildable_paths.append(input_path)

        if not buildable_paths:
            raise ValueError("Keines der offenen Dokumente enthält Lernhilfen.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)

            built_files: list[tuple[Path, Path]] = []
            for input_path in buildable_paths:
                target_pdf = tmp_dir_path / f"{input_path.stem}_lernhilfen.pdf"
                try:
                    out_file = build_help_cards_from_request(
                        self._help_cards_build_request(
                            input_path=input_path,
                            output_path=target_pdf,
                            include_solutions=include_solutions,
                            page_format=page_format,
                            contrast_profile=contrast_profile,
                            add_running_elements=False,
                        )
                    )
                except Exception as error:
                    raise RuntimeError(
                        f"Lernhilfen-Export für '{input_path.name}' fehlgeschlagen: {error}"
                    ) from error
                built_files.append((input_path, Path(out_file)))

            tmp_zip_path = tmp_dir_path / "bundle.zip"
            used_arcnames: set[str] = set()
            with zipfile.ZipFile(tmp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for input_path, built_file in built_files:
                    arcname = self._resolve_unique_zip_arcname(input_path.stem, used_arcnames)
                    used_arcnames.add(arcname)
                    archive.write(built_file, arcname=arcname)

            output_zip_path = validate_export_output_path(
                Path(output_zip_path).with_suffix(".zip"),
                allowed_suffixes={".zip"},
            )
            output_zip_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_zip_path), str(output_zip_path))

        if skipped_names:
            self.status_var.set(
                f"{len(built_files)} Dokument(e) exportiert, "
                f"{len(skipped_names)} ohne Lernhilfen übersprungen."
            )
        else:
            self.status_var.set(f"{len(built_files)} Dokument(e) exportiert.")

        return [output_zip_path]

    @staticmethod
    def _resolve_unique_zip_arcname(stem: str, used_arcnames: set[str]) -> str:
        """Liefert einen im ZIP eindeutigen Dateinamen, auch bei gleichnamigen Stems aus unterschiedlichen Ordnern."""

        base_arcname = f"{stem}_lernhilfen.pdf"
        arcname = base_arcname
        suffix_counter = 2
        while arcname in used_arcnames:
            arcname = f"{stem}_lernhilfen_{suffix_counter}.pdf"
            suffix_counter += 1
        return arcname
