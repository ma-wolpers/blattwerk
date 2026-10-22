"""Klausur-Diagnosen: Teil-Trenner `--hm` und AFB (KL001–KL007).

Die Struktur der Teile (und jedes Strukturproblem) kommt allein aus
`exam_parts.resolve_exam_parts`, die Blatt-Logik der AFB aus
`exam_analysis.iter_scored_leaves` -- dieselben Funktionen nutzen Renderer und
Auswertung, damit Validator und Darstellung nie auseinanderlaufen. Dieses
Modul übersetzt nur Codes in Meldungen und Schweregrade.
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .exam_analysis import iter_scored_leaves, parse_afb
from .exam_parts import AID_SPLIT_BLOCK, resolve_exam_parts
from .points_model import build_points_model

_PART_PROBLEMS = {
    "KL001": ("error", "`--hm` darf in einer Klausur hoechstens zweimal vorkommen (Deckblatt | Teil A | Teil B)."),
    "KL002": ("warning", "`--hm` wirkt nur in Klausuren (.kbw) und wird hier ignoriert."),
    "KL004": ("error", "`--hm` muss zwischen zwei Aufgaben auf oberster Ebene stehen (Aufgabe davor und danach, nicht in `:::columns`)."),
    "KL005": ("error", "Nach `--hm` muss eine neue Aufgabe (`:::task`) folgen -- Teilaufgaben oder Loesungen duerfen nicht von ihrer Aufgabe getrennt werden."),
    "KL007": ("error", "Vor dem ersten von zwei `--hm` (Deckblatt) duerfen keine Aufgaben, Teilaufgaben oder Loesungen stehen."),
}
"""Meldung und Schwere je Strukturproblem; Fehler blockieren den Export (nie still „kein Split“)."""


def _diag(code, message, blocks, index, severity="warning") -> BuildDiagnostic:
    block_type, options, _content = blocks[index]
    return BuildDiagnostic(
        code=code,
        message=message,
        severity=severity,
        block_index=index,
        block_type=block_type,
        region_id=compute_block_region_id(block_type, options) + f":{index}" if block_type == AID_SPLIT_BLOCK else compute_block_region_id(block_type, options),
        anchor=code,
    )


def validate_exam(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """Prüft die Teil-Trenner (alle Typen) und AFB (nur Klausur)."""
    diagnostics: list[BuildDiagnostic] = []
    for problem in resolve_exam_parts(blocks, document_type).problems:
        severity, message = _PART_PROBLEMS[problem.code]
        diagnostics.append(_diag(problem.code, message, blocks, problem.block_index, severity))
    if document_type != "exam":
        return diagnostics

    units = build_points_model(blocks)
    for _unit, leaf, _reason in iter_scored_leaves(units):
        if leaf is not None and leaf.afb is None:
            diagnostics.append(_diag("KL003", f"{leaf.label}: Anforderungsbereich fehlt (`afb=1|2|3`).", blocks, leaf.block_index))
    for unit in units:
        if unit.subtasks_pointed:
            continue
        for sub in unit.subtasks:
            if parse_afb(sub.options) is not None:
                diagnostics.append(_diag(
                    "KL006", f"Aufgabe {unit.number}{sub.letter or ''}: `afb` wirkt nicht, weil die Teilaufgaben keine eigenen Punkte haben.",
                    blocks, sub.block_index,
                ))
    return diagnostics
