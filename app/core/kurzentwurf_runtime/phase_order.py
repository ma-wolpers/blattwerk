"""Kurzentwurf: Prüfungen zur Reihenfolge der Phasen (`KZF049`).

Eigenes Modul statt `validator.py`, weil dieser bereits über der
300-Zeilen-Konvention liegt (siehe `ARCHITEKTUR.md`). Welche Phase wohin
gehört, steht nur in `model.PHASE_SPECS` (`PhaseSpec.placement`); diese
Datei kennt keine Phasennamen.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import PHASE_PLACEMENT_AFTER_LESSON, PHASE_PLACEMENT_BUFFER, PHASE_SPECS, Diagnostic
from .region import compute_phase_region_id

_PLACEMENT_BY_PHASE = {spec.display_name: spec.placement for spec in PHASE_SPECS}


def collect_phase_order_diagnostics(blocks: Sequence[dict[str, object]]) -> list[Diagnostic]:
    """Warnt (`KZF049`), wenn eine Puffer-Phase (Didaktische Reserve) den Stundenverlauf beendet.

    Eine Reserve gehört an die Stelle im Verlauf, an der sie inhaltlich
    stattfinden würde, nicht pauschal ans Ende. Phasen nach der Stunde
    (Hausaufgabe) zählen beim Suchen der letzten Phase nicht mit, sonst
    würde "Reserve, dann Hausaufgabe" die Prüfung umgehen.

    Args:
        blocks: Normalisierte Phasenblöcke aus `validator.inspect_kurzentwerfer_text`
            (Schlüssel `phase`, `duration_minutes`, `start_time`, `line`).

    Returns:
        Höchstens eine abhakbare Warnung, verankert an der Reserve-Phase.
    """
    lesson_blocks = [
        block for block in blocks if _PLACEMENT_BY_PHASE.get(str(block["phase"])) != PHASE_PLACEMENT_AFTER_LESSON
    ]
    if not lesson_blocks:
        return []

    last = lesson_blocks[-1]
    phase = str(last["phase"])
    if _PLACEMENT_BY_PHASE.get(phase) != PHASE_PLACEMENT_BUFFER:
        return []

    return [
        Diagnostic(
            code="KZF049",
            severity="warning",
            message=(
                f"{phase} steht am Ende des Stundenverlaufs. Setze sie an die Stelle, an der sie "
                "inhaltlich stattfinden würde, z. B. vor die Phase, deren Aufgabe auf sie folgt."
            ),
            line=int(last["line"]),
            region_id=compute_phase_region_id(phase, last["duration_minutes"], last["start_time"]),
            anchor=phase,
        )
    ]
