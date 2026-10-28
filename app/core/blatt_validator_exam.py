"""Klausur-Diagnosen: Teil-Trenner `--hm`/`--w` und AFB (KL001–KL012).

Die Struktur der Teile (und jedes Strukturproblem) kommt allein aus
`exam_parts.resolve_exam_parts`, die Blatt-Logik der AFB aus
`exam_analysis.iter_scored_leaves` -- dieselben Funktionen nutzen Renderer und
Auswertung, damit Validator und Darstellung nie auseinanderlaufen. Dieses
Modul übersetzt nur Codes in Meldungen und Schweregrade. KL013 (Lernhilfe
ohne Lernhilfe-Abzug) liegt bei den Lernhilfen-Diagnosen in `blatt_validator_help`.
"""

from __future__ import annotations

from decimal import Decimal

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .exam_analysis import iter_scored_leaves, parse_afb
from .exam_parts import PART_SPLIT_BLOCKS, resolve_exam_parts
from .points_model import STATUS_OK, build_points_model, format_points

_PART_PROBLEMS = {
    "KL001": ("error", "`--hm` darf in einer Klausur hoechstens zweimal vorkommen (Deckblatt | Teil A | Teil B)."),
    "KL002": ("warning", "`--hm` wirkt nur in Klausuren (.kbw) und wird hier ignoriert."),
    "KL004": ("error", "Ein Teil-Trenner muss auf oberster Ebene stehen (nicht in `:::columns`): `--hm` zwischen zwei Aufgaben, `--w` vor einem Wahlteil mit mindestens einer Aufgabe."),
    "KL005": ("error", "Nach einem Teil-Trenner (`--hm`, `--w`) muss eine neue Aufgabe (`:::task`) folgen -- Teilaufgaben oder Loesungen duerfen nicht von ihrer Aufgabe getrennt werden."),
    "KL007": ("error", "Vor dem ersten von zwei `--hm` (Deckblatt) duerfen keine Aufgaben, Teilaufgaben oder Loesungen stehen."),
    "KL008": ("error", "`--w` ohne offenen Wahlbereich: Der erste Wahlteil eines Bereichs braucht die Anzahl, z. B. `--w[1] Titel`."),
    "KL009": ("error", "`--w[k]` in einem offenen Wahlbereich: weitere Wahlteile desselben Bereichs ohne `[k]` schreiben (`--w Titel`); ein neuer Bereich beginnt erst nach `--hm`."),
    "KL010": ("error", "Ungueltige Anzahl in `--w[k]`: k muss eine ganze Zahl von 1 bis (Anzahl der Wahlteile - 1) sein."),
    "KL012": ("error", "`--w` (Wahlteil) gibt es nur in Klausuren (.kbw)."),
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
        region_id=compute_block_region_id(block_type, options) + f":{index}" if block_type in PART_SPLIT_BLOCKS else compute_block_region_id(block_type, options),
        anchor=code,
    )


def validate_exam(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """Prüft die Teil-Trenner (alle Typen) und AFB (nur Klausur)."""
    diagnostics: list[BuildDiagnostic] = []
    resolution = resolve_exam_parts(blocks, document_type)
    for problem in resolution.problems:
        severity, message = _PART_PROBLEMS[problem.code]
        diagnostics.append(_diag(problem.code, message, blocks, problem.block_index, severity))
    if document_type != "exam":
        return diagnostics

    units = build_points_model(blocks)
    if resolution.layout is not None:
        diagnostics.extend(_unequal_choice_points(resolution.layout, units, blocks))
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


def _unequal_choice_points(layout, units, blocks) -> list[BuildDiagnostic]:
    """`KL011`: Alle Wahlteile eines Bereichs müssen dieselbe Punktzahl haben.

    Geprüft wird nur, wenn alle Aufgaben des Bereichs gültige Punkte haben --
    fehlende oder widersprüchliche Punkte melden bereits `PK…`.
    """
    parts = {part.part_id: part for part in layout.parts}
    diagnostics = []
    for group in layout.groups:
        sums = {}
        for part_id in group.part_ids:
            part_units = [unit for unit in units if parts[part_id].contains(unit.block_index)]
            if any(unit.status != STATUS_OK for unit in part_units):
                break
            sums[part_id] = sum((unit.effective for unit in part_units), start=Decimal(0))
        else:
            if len(set(sums.values())) > 1:
                listing = ", ".join(f"{parts[part_id].label}: {format_points(value)} P" for part_id, value in sums.items())
                diagnostics.append(_diag(
                    "KL011", f"Die Wahlteile eines Bereichs muessen gleich viele Punkte haben ({listing}).",
                    blocks, parts[group.part_ids[0]].marker_block, "error",
                ))
    return diagnostics
