"""Einzige UI-Stelle, die den Dokumenttyp eines Tabs bestimmt (Invariante I1).

Gespeicherte Dateien bekommen ihren Typ allein aus der Endung
(`document_semantics.type_for_tab`). Für eine unbekannte Endung fragt die UI
beim Öffnen, ob die Datei als Markdown interpretiert werden soll. Diese
Entscheidung ist **temporär**: Sie lebt nur in `_interpreted_as_markdown_paths`
dieser Sitzung, wird nie persistiert, und Speichern erzwingt `.md`
(siehe `_requires_markdown_save_as`).
"""

from __future__ import annotations

from pathlib import Path
from .dialog_services import messagebox

from ..core.document_semantics import type_for_path, type_for_tab
from ..core.document_type_registry import DOCUMENT_TYPE_MARKDOWN, DocumentTypeSpec, spec_for_type


class BlattwerkDocumentTypeMixin:
    """Liefert Typ und Capabilities des aktiven bzw. eines gegebenen Dokuments."""

    def _interpreted_markdown_paths(self) -> set[str]:
        """Pfade (normalisiert), die in dieser Sitzung als Markdown interpretiert werden."""
        paths = getattr(self, "_interpreted_as_markdown_paths", None)
        if paths is None:
            paths = set()
            self._interpreted_as_markdown_paths = paths
        return paths

    @staticmethod
    def _document_type_path_key(input_path) -> str:
        return str(Path(input_path).expanduser().resolve())

    def _read_document_type(self, input_path) -> str | None:
        """Typ eines Dokuments: Endung, sonst die temporäre Markdown-Interpretation.

        Returns:
            Kanonischer Typ oder ``None`` für eine unbekannte Endung ohne
            Markdown-Interpretation (dann darf nichts gerendert werden).
        """
        if input_path is None:
            return None
        interpreted = self._document_type_path_key(input_path) in self._interpreted_markdown_paths()
        return type_for_tab(input_path, DOCUMENT_TYPE_MARKDOWN if interpreted else None)

    def _document_spec_for_path(self, input_path) -> DocumentTypeSpec | None:
        """Registry-Spec eines Dokuments oder ``None`` (unbekannte Endung)."""
        document_type = self._read_document_type(input_path)
        return spec_for_type(document_type) if document_type else None

    @staticmethod
    def _solutions_renderable_for_type(document_type: str | None) -> bool:
        """Ob für den Typ eine Lösungsfassung gewählt werden kann (``None``: nein)."""
        return bool(document_type) and spec_for_type(document_type).solutions_renderable

    def _confirm_open_unknown_extension(self, input_path) -> bool:
        """Fragt bei unbekannter Endung, ob die Datei als Markdown interpretiert werden soll.

        Returns:
            ``True``, wenn geöffnet werden darf (bekannte Endung oder Zustimmung).
        """
        if type_for_path(input_path) is not None:
            return True
        key = self._document_type_path_key(input_path)
        if key in self._interpreted_markdown_paths():
            return True
        accepted = messagebox.askyesno(
            "Unbekannte Dateiendung",
            f"Die Endung von „{Path(input_path).name}“ gehört zu keinem Blattwerk-Dokumenttyp.\n\n"
            "Als schlichtes Markdown interpretieren?\n"
            "(Beim Speichern wird dann eine .md-Datei angelegt; die Originaldatei bleibt unverändert.)",
        )
        if accepted:
            self._interpreted_markdown_paths().add(key)
        return bool(accepted)

    def _prompt_markdown_save_as_once(self, input_path) -> None:
        """Öffnet beim ersten Speicherversuch Speichern-unter (`.md` vorbelegt).

        Weitere (automatische) Speicherversuche desselben Tabs zeigen nur einen
        Statushinweis, damit das verzögerte Autosave nicht ständig Dialoge öffnet.
        """
        prompted = getattr(self, "_markdown_save_as_prompted", None)
        if prompted is None:
            prompted = set()
            self._markdown_save_as_prompted = prompted
        key = self._document_type_path_key(input_path)
        if key in prompted:
            self.status_var.set("Ungespeichert – bitte per „Speichern unter“ als .md speichern")
            return
        prompted.add(key)
        self.save_markdown_file_as()

    def _requires_markdown_save_as(self, input_path) -> bool:
        """Ob Speichern zwingend als `.md` per Speichern-unter erfolgen muss.

        Gilt für Dateien mit unbekannter Endung, die nur vorübergehend als
        Markdown interpretiert werden: Es entsteht nie eine gespeicherte
        Datei mit unbekannter Endung, die semantisch Markdown ist.
        """
        if input_path is None or type_for_path(input_path) is not None:
            return False
        return self._document_type_path_key(input_path) in self._interpreted_markdown_paths()
