"""Dateifilter und Speichern-unter-Rückfragen für die typgebundenen Endungen.

Die Filterlisten kommen aus der Registry, damit neue Typen automatisch in
Öffnen- und Speichern-Dialogen erscheinen. Die fachliche Vorbereitung des
Inhalts liegt in `app/core/save_as_staging.py`; hier sind nur die Rückfragen.
"""

from __future__ import annotations

from .dialog_services import messagebox

from ..core.document_type_registry import (
    BLATTWERK_DOCUMENT_TYPES,
    BLATTWERK_EXTENSIONS,
    DOCUMENT_TYPE_MARKDOWN,
    spec_for_type,
)
from ..core.save_as_staging import stage_save_as_content


def _filetype_entry(document_type: str) -> tuple[str, str]:
    spec = spec_for_type(document_type)
    return (f"{spec.label} (*{spec.extension})", f"*{spec.extension}")


def open_dialog_filetypes() -> list[tuple[str, str]]:
    """Filter des Öffnen-Dialogs: alle Blattwerk-Dateien, je Typ, Markdown, alle Dateien."""
    blattwerk_pattern = " ".join(f"*{ext}" for ext in BLATTWERK_EXTENSIONS)
    return (
        [("Blattwerk-Dateien", blattwerk_pattern)]
        + [_filetype_entry(document_type) for document_type in BLATTWERK_DOCUMENT_TYPES]
        + [_filetype_entry(DOCUMENT_TYPE_MARKDOWN), ("Alle Dateien", "*.*")]
    )


def save_as_filetypes(current_type: str) -> list[tuple[str, str]]:
    """Filter des Speichern-unter-Dialogs, der aktuelle Typ zuerst."""
    ordered = [current_type] + [
        document_type
        for document_type in (*BLATTWERK_DOCUMENT_TYPES, DOCUMENT_TYPE_MARKDOWN)
        if document_type != current_type
    ]
    return [_filetype_entry(document_type) for document_type in ordered]


def confirm_and_stage_save_as(content: str, source_type: str, target_type: str) -> str | None:
    """Fragt bei Typwechsel nach und liefert den zu schreibenden Inhalt (``None`` = Abbruch)."""
    staged = stage_save_as_content(content, source_type, target_type)
    if not staged.type_changed:
        return staged.content
    target_label = spec_for_type(target_type).label
    if not messagebox.askyesno(
        "Dokumenttyp ändern?",
        f"Durch die neue Dateiendung wird das Dokument zu: {target_label}.\n\nFortfahren?",
    ):
        return None
    if staged.edit_unsafe and not messagebox.askyesno(
        "Typ-Marker nicht angepasst",
        "Der Frontmatter-Eintrag `document_type` konnte nicht automatisch angepasst werden "
        "(das Frontmatter lässt sich nicht sicher bearbeiten).\n\nTrotzdem speichern?",
    ):
        return None
    return staged.content
