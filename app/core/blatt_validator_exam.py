"""Klausur-Diagnosen: Hilfsmittel-Trenner `--hm` und AFB (KL001–KL006).

Die Positionsregel kommt aus `document_semantics.aid_split_position_problem`,
die Blatt-Logik der AFB aus `exam_analysis.iter_scored_leaves` -- dieselben
Funktionen nutzen Renderer und Auswertung, damit Validator und Darstellung
nie auseinanderlaufen.
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .document_semantics import (
    AID_SPLIT_BLOCK,
    MAX_AID_SPLITS,
    aid_cover_position_problem,
    aid_split_indices,
    aid_split_position_problem,
)
from .exam_analysis import iter_scored_leaves, parse_afb
from .points_model import build_points_model


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
    """Prüft `--hm` (alle Typen) und AFB (nur Klausur)."""
    diagnostics: list[BuildDiagnostic] = []
    split_indices = aid_split_indices(blocks)
    if document_type != "exam":
        for index in split_indices:
            diagnostics.append(_diag("KL002", "`--hm` wirkt nur in Klausuren (.kbw) und wird hier ignoriert.", blocks, index))
        return diagnostics

    # Zwei Marker = Deckblatt | Teil A | Teil B. Jede ungültige Konstellation ist ein
    # Fehler (blockiert den Export) -- nie still „kein Split“.
    has_cover = len(split_indices) == MAX_AID_SPLITS
    for position, index in enumerate(split_indices):
        if position >= MAX_AID_SPLITS:
            diagnostics.append(_diag(
                "KL001", "`--hm` darf in einer Klausur hoechstens zweimal vorkommen (Deckblatt | Teil A | Teil B).",
                blocks, index, "error",
            ))
            continue
        if has_cover and position == 0:
            problem = aid_cover_position_problem(blocks, index)
        else:
            start = split_indices[0] + 1 if has_cover else 0
            problem = aid_split_position_problem(blocks, index, start=start)
        if problem == "KL007":
            diagnostics.append(_diag(
                "KL007", "Vor dem ersten von zwei `--hm` (Deckblatt) duerfen keine Aufgaben, Teilaufgaben oder Loesungen stehen.",
                blocks, index, "error",
            ))
        elif problem == "KL004":
            diagnostics.append(_diag(
                "KL004", "`--hm` muss zwischen zwei Aufgaben auf oberster Ebene stehen (Aufgabe davor und danach, nicht in `:::columns`).",
                blocks, index, "error",
            ))
        elif problem == "KL005":
            diagnostics.append(_diag(
                "KL005", "Nach `--hm` muss eine neue Aufgabe (`:::task`) folgen -- Teilaufgaben oder Loesungen duerfen nicht von ihrer Aufgabe getrennt werden.",
                blocks, index, "error",
            ))

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
