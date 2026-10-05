"""Diagnosen der Bewertungstabelle `:::evaluation` (EV001, EV002).

* EV001 (Warnung): Das Dokument enthält eine Bewertungstabelle, aber
  bepunktbare Aufgaben ohne Punkte (Zelle „–“).
* EV002 (Warnung): Bewertungstabelle in einem Dokumenttyp ohne diese
  Funktion (z. B. Präsentation); sie wird dort nicht dargestellt.
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .document_type_registry import spec_for_type
from .points_model import STATUS_MISSING, build_points_model


def validate_evaluation(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    indices = [index for index, (block_type, _o, _c) in enumerate(blocks) if block_type == "evaluation"]
    if not indices:
        return []

    def diag(code, message, index):
        block_type, options, _content = blocks[index]
        return BuildDiagnostic(
            code=code, message=message, block_index=index, block_type=block_type,
            region_id=compute_block_region_id(block_type, options), anchor=code,
        )

    try:
        available = spec_for_type(document_type).evaluation
    except KeyError:
        available = False
    if not available:
        return [diag("EV002", "Die Bewertungstabelle gibt es nur in Arbeitsblaettern und Klausuren; sie wird hier nicht angezeigt.", index) for index in indices]
    missing = [unit.number for unit in build_points_model(blocks) if unit.status == STATUS_MISSING]
    if not missing:
        return []
    return [diag("EV001", f"Bewertungstabelle: Aufgabe(n) {', '.join(missing)} ohne Punkte (Zelle `–`).", indices[0])]
