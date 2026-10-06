"""Speichern-unter mit Typwechsel: Inhalt vorbereiten, ohne den Buffer anzufassen.

Regeln (Nutzerentscheidungen R3-1.5, R5-4):

* **Blattwerk → anderer Blattwerk-Typ:** `document_type` wird über die
  gemeinsame Edit-Engine (`frontmatter_edit.FrontmatterEditor`) auf den
  kanonischen Wert des Zieltyps gesetzt, damit die Anwendung selbst keine
  FM008-Inkonsistenz erzeugt.
* **`.md` → Blattwerk-Typ:** ebenso, weil der Marker dort Pflicht ist.
* **Blattwerk → `.md`:** `document_type` bleibt **unverändert** (weder
  gesetzt, ersetzt noch ergänzt). Ein vorhandener Blattwerk-Marker löst danach
  in der `.md` ganz normal FM008 aus -- das ist gewollt.
* **Gleicher Typ:** keine Änderung.

Die Funktion ist rein: Sie liefert den zu schreibenden Inhalt; der Aufrufer
schreibt ihn und übernimmt erst nach Erfolg irgendeinen UI-Zustand.
"""

from __future__ import annotations

from dataclasses import dataclass

from .document_semantics import DOCUMENT_TYPE_KEY
from .document_type_registry import spec_for_type
from .frontmatter_edit import EditUnsafe, FrontmatterEditor


@dataclass(frozen=True)
class StagedSaveAs:
    """Ergebnis der Vorbereitung.

    Attributes:
        content: Zu schreibender Inhalt (bei `edit_unsafe` der unveränderte Text).
        type_changed: Ob sich der Dokumenttyp ändert (UI fragt dann nach).
        marker_updated: Ob `document_type` automatisch gesetzt wurde.
        edit_unsafe: Ob der Marker-Edit nicht sicher möglich war (UI fragt,
            ob trotzdem ohne Marker-Anpassung gespeichert werden soll).
    """

    content: str
    type_changed: bool
    marker_updated: bool
    edit_unsafe: bool


def stage_save_as_content(content: str, source_type: str, target_type: str) -> StagedSaveAs:
    """Bereitet den Inhalt für Speichern-unter von `source_type` nach `target_type` vor."""
    if source_type == target_type:
        return StagedSaveAs(content, type_changed=False, marker_updated=False, edit_unsafe=False)
    target_spec = spec_for_type(target_type)
    if not target_spec.marker_required:
        return StagedSaveAs(content, type_changed=True, marker_updated=False, edit_unsafe=False)
    editor = FrontmatterEditor(content)
    try:
        editor.ensure_frontmatter()
        editor.set_scalar(DOCUMENT_TYPE_KEY, target_spec.id)
        staged = editor.result()
    except EditUnsafe:
        return StagedSaveAs(content, type_changed=True, marker_updated=False, edit_unsafe=True)
    return StagedSaveAs(staged, type_changed=True, marker_updated=staged != content, edit_unsafe=False)
