"""Diagnosen der Bewertungstabelle `:::evaluation` (EV001).

* EV001 (Warnung): Das Dokument enthält eine Bewertungstabelle, aber
  bepunktbare Aufgaben ohne Punkte (Zelle „–“).
* EV002 (Bewertungstabelle in einem Typ ohne diese Funktion) meldet die
  gemeinsame Verfügbarkeitstabelle `block_availability`.
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .document_type_registry import has_evaluation
from .points_model import STATUS_MISSING, build_points_model


def validate_evaluation(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """EV001 am ersten `:::evaluation`-Block, wenn der Typ die Tabelle hat."""
    indices = [index for index, (block_type, _o, _c) in enumerate(blocks) if block_type == "evaluation"]
    if not indices or not has_evaluation(document_type):
        return []

    def diag(code, message, index):
        block_type, options, _content = blocks[index]
        return BuildDiagnostic(
            code=code, message=message, block_index=index, block_type=block_type,
            region_id=compute_block_region_id(block_type, options), anchor=code,
        )

    missing = [unit.number for unit in build_points_model(blocks) if unit.status == STATUS_MISSING]
    if not missing:
        return []
    return [diag("EV001", f"Bewertungstabelle: Aufgabe(n) {', '.join(missing)} ohne Punkte (Zelle `–`).", indices[0])]
