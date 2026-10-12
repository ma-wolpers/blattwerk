"""Dokumentdatei-Workflows der Vorschau: neues Dokument, Speichern unter, Datei waehlen,
Eingabe pruefen und Diagnose-/Overflow-Hinweise anzeigen.
"""

from __future__ import annotations

from pathlib import Path
from .dialog_services import filedialog, messagebox
from .document_type_dialog import prompt_new_document_type
from ..core.document_semantics import type_for_path
from ..core.document_type_registry import DOCUMENT_TYPE_MARKDOWN, spec_for_type
from ..core.document_type_templates import (
    build_new_document_content,
    get_new_document_dialog_defaults,
)
from .document_file_dialogs import (
    confirm_and_stage_save_as,
    open_dialog_filetypes,
    save_as_filetypes,
)
from ..core.diagnostic_warnings import build_warning_payload
from ..storage import acknowledged_warnings_store


class BlattwerkAppPreviewFilesMixin:
    """Datei-Workflows rund um das aktive Vorschau-Dokument."""


    def _default_markdown_content(self, document_type="worksheet"):
            """Liefert den Standardinhalt für neu erzeugte Dokumente."""

            preferences = getattr(self, "user_preferences", {})
            return build_new_document_content(document_type, preferences)


    def _select_new_document_type(self):
            """Opens modal selection dialog for the next document to create."""

            preferences = getattr(self, "user_preferences", {})
            initial_value = str(preferences.get("last_new_document_type", "worksheet") or "worksheet")
            selected_document_type = prompt_new_document_type(self, initial_value=initial_value)
            if selected_document_type:
                preferences["last_new_document_type"] = selected_document_type
            return selected_document_type


    def create_new_markdown_file(self):
            """Erzeugt ein neues Dokument über Typauswahl und Dateidialog."""

            document_type = self._select_new_document_type()
            if not document_type:
                return

            dialog_title, initial_name = get_new_document_dialog_defaults(document_type)
            spec = spec_for_type(document_type)

            dialog_kwargs = {
                "title": dialog_title,
                "defaultextension": spec.extension,
                "initialfile": initial_name,
                "filetypes": [(f"{spec.label} (*{spec.extension})", f"*{spec.extension}")],
            }
            initial_dir = self._get_initial_dialog_dir("input_markdown")
            if initial_dir:
                dialog_kwargs["initialdir"] = initial_dir

            selected = filedialog.asksaveasfilename(**dialog_kwargs)
            if not selected:
                return

            target_path = Path(selected)
            if type_for_path(target_path) != document_type:
                # Die Endung ist die Typidentität (I1): sie muss zum gewählten Typ passen.
                target_path = target_path.with_suffix(spec.extension)

            if target_path.exists():
                messagebox.showerror(
                    "Datei existiert bereits",
                    "Bitte wähle einen neuen Dateinamen, damit keine bestehende Datei überschrieben wird.",
                )
                return

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(self._default_markdown_content(document_type), encoding="utf-8")
            except Exception as error:
                messagebox.showerror("Datei konnte nicht erstellt werden", str(error))
                self.status_var.set("Neue Datei konnte nicht erstellt werden")
                return

            self._set_last_dialog_dir("input_markdown", str(target_path))
            self.status_var.set(f"Neues Dokument erstellt: {target_path.name}")
            self._open_input_path(target_path, add_recent=True)


    def save_markdown_file_as(self):
            """Speichert die aktuelle Markdown-Datei unter neuem Pfad als Kopie."""

            source_path = self._validate_input()
            if source_path is None:
                return

            if self.editor_widget is not None:
                content = self.editor_widget.get("1.0", "end-1c")
            else:
                try:
                    content = source_path.read_text(encoding="utf-8")
                except Exception as error:
                    messagebox.showerror("Datei konnte nicht gelesen werden", str(error))
                    self.status_var.set("Speichern unter fehlgeschlagen")
                    return

            source_type = self._read_document_type(source_path) or DOCUMENT_TYPE_MARKDOWN
            source_spec = spec_for_type(source_type)
            dialog_kwargs = {
                "title": "Speichern unter",
                "defaultextension": source_spec.extension,
                "filetypes": save_as_filetypes(source_type),
                "initialdir": str(source_path.parent),
                "initialfile": f"{source_path.stem}{source_spec.extension}",
            }
            selected = filedialog.asksaveasfilename(**dialog_kwargs)
            if not selected:
                return

            target_path = Path(selected)
            if type_for_path(target_path) is None:
                target_path = target_path.with_suffix(source_spec.extension)
            target_type = type_for_path(target_path)
            content = confirm_and_stage_save_as(content, source_type, target_type)
            if content is None:
                return

            if target_path == source_path:
                messagebox.showwarning(
                    "Speichern unter",
                    "Bitte wähle einen anderen Pfad als die aktuell geöffnete Datei.",
                )
                return

            if target_path.exists() and not messagebox.askyesno(
                "Datei überschreiben?",
                f"Die Datei existiert bereits und wird überschrieben:\n{target_path}\n\nMöchtest du fortfahren?",
            ):
                return

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
            except Exception as error:
                messagebox.showerror("Datei konnte nicht gespeichert werden", str(error))
                self.status_var.set("Speichern unter fehlgeschlagen")
                return

            self._set_last_dialog_dir("input_markdown", str(target_path))
            self.status_var.set(f"Datei gespeichert unter: {target_path}")
            self._open_input_path(target_path, add_recent=True)


    def _show_document_diagnostics(self, input_path: Path, context_label: str):
            """Zeigt nicht-blockierende Blattwerk-Warnungen einmalig pro Dokumentzustand."""
            warning_payload = build_warning_payload(
                input_path,
                context_label,
                acknowledged_repo=acknowledged_warnings_store,
                document_type=self._read_document_type(input_path),
            )
            if warning_payload is None:
                return

            signature = warning_payload["signature"]
            if signature == self._last_diagnostics_signature:
                return

            self._last_diagnostics_signature = signature
            if warning_payload["count"] <= 0:
                return

            messagebox.showwarning(
                warning_payload["title"],
                "Das Dokument wurde trotzdem verarbeitet.\n\n" + warning_payload["message"],
            )


    def _show_compile_overflow_warnings(self, diagnostics, context_label: str):
            """Zeigt PT002-/IM003-Warnungen aus dem Compile-/Render-Schritt einmalig pro Zustand."""

            overflow_warnings = [
                diag for diag in (diagnostics or [])
                if str(getattr(diag, "code", "")) in {"PT002", "IM003"}
            ]
            if not overflow_warnings:
                return

            signature = (
                context_label,
                tuple(str(getattr(diag, "message", "")) for diag in overflow_warnings),
            )
            if signature == getattr(self, "_last_compile_overflow_warning_signature", None):
                return
            self._last_compile_overflow_warning_signature = signature

            lines = [
                f"- {diag.code}: {diag.message}"
                for diag in overflow_warnings
            ]
            messagebox.showwarning(
                f"Blattwerk-Warnungen ({context_label})",
                "Rendern lief weiter, aber es gibt Compile-Warnungen:\n\n"
                + "\n".join(lines),
            )


    def pick_input(self):
            """Öffnet den Dateidialog für Blattwerk-, Markdown- und sonstige Dateien."""
            dialog_kwargs = {
                "title": "Dokument öffnen",
                "filetypes": open_dialog_filetypes(),
            }
            initial_dir = self._get_initial_dialog_dir("input_markdown")
            if initial_dir:
                dialog_kwargs["initialdir"] = initial_dir

            selected_paths = list(filedialog.askopenfilenames(**dialog_kwargs) or ())
            if not selected_paths:
                return

            max_open_count = 8
            truncated_paths = selected_paths[:max_open_count]
            self._set_last_dialog_dir("input_markdown", truncated_paths[0])

            if len(selected_paths) > max_open_count:
                messagebox.showinfo(
                    "Auswahl begrenzt",
                    "Es werden maximal 8 Dateien gleichzeitig geöffnet.",
                )

            for path_text in truncated_paths:
                self._open_input_path(Path(path_text), add_recent=True)


    def _validate_input(self):
            """Validate input."""
            input_text = self._clean_path_text(self.input_var.get())
            if not input_text:
                messagebox.showwarning("Fehlende Eingabe", "Bitte wähle eine Markdown-Datei aus.")
                return None

            path = Path(input_text)
            if not path.exists():
                messagebox.showerror("Datei nicht gefunden", f"Die Datei existiert nicht:\n{path}")
                return None

            return path
