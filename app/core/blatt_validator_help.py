"""Lernhilfen-Diagnosen: KL013 (Klausur) und BL012 (Präsentation).

`validate_help_blocks` ist der eine Einstieg aus dem Validator-Orchestrator.

**BL012 (Warnung):** Lernhilfen gibt es nur in Arbeitsblättern und Klausuren.
In Präsentationen (Typen mit `slide_layout`) sind `:::help`/`:::hilfe`
veraltet; sie werden vorerst weiter dargestellt, aber gemeldet.

**KL013 (Warnung):** In Klausuren sind Lernhilfen erlaubt, ihre Nutzung soll aber Punkte kosten.
Deshalb muss jede (Teil-)Aufgabe, an der eine für Schüler:innen sichtbare
Lernhilfe hängt, in ihrer Lösung -- oder in der Lösung der übergeordneten
Aufgabe bzw. einer ihrer Teilaufgaben -- mindestens einen Abzug mit dem
Erwartungstyp „Lernhilfe“ tragen, z. B. ``1. Lernhilfe genutzt (−1P Lh)``.

Die Zuordnung Lernhilfe -> (Teil-)Aufgabe kommt allein aus
`blatt_kern_shared_blocks.assign_help_blocks` (dieselbe wie für die
Verweise „→ Lernhilfe B“), die Lösungspunkte aus `solution_items`, die
Aufgabeneinheiten aus `points_model` -- keine eigene Zählung.
"""

from __future__ import annotations

from .blatt_kern_shared_blocks import assign_help_blocks
from .blatt_kern_shared_data import HELP_BLOCK_TYPES
from .document_type_registry import DOCUMENT_TYPE_EXAM, has_slide_layout
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .expectation_kinds import LERNHILFE_KIND_KEY
from .points_model import build_points_model
from .solution_items import collect_solution_targets


def validate_help_blocks(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """Alle Lernhilfen-Diagnosen eines Dokuments.

    Args:
        blocks: geparste Blockliste.
        document_type: Typ aus der Dateiendung; Präsentationen bekommen BL012,
            Klausuren KL013, andere Typen nichts.
    """
    if has_slide_layout(document_type or ""):
        return [
            _diag(
                index,
                blocks,
                "BL012",
                f"`:::{block_type}` ist in Praesentationen veraltet -- Lernhilfen gibt es nur in "
                "Arbeitsblaettern und Klausuren. Der Block wird noch dargestellt; bitte als normalen "
                "Folieninhalt umsetzen oder entfernen.",
            )
            for index, (block_type, _options, _content) in enumerate(blocks)
            if block_type in HELP_BLOCK_TYPES
        ]
    if document_type == DOCUMENT_TYPE_EXAM:
        return help_deduction_diagnostics(blocks)
    return []


def help_deduction_diagnostics(blocks) -> list[BuildDiagnostic]:
    """KL013-Warnungen, je (Teil-)Aufgabe mit Lernhilfe höchstens eine.

    Args:
        blocks: geparste Blockliste einer Klausur.

    Returns:
        Warnungen am Aufgaben- bzw. Teilaufgabenblock, dem die Lernhilfe
        zugeordnet ist. Lernhilfen vor der ersten Aufgabe gehören zu keiner
        Aufgabe und werden nicht geprüft.
    """
    owners = []
    for assignment in assign_help_blocks(blocks, include_solutions=False, document_type="exam"):
        if assignment.target_index is not None and assignment.target_index not in owners:
            owners.append(assignment.target_index)
    if not owners:
        return []

    units = build_points_model(blocks)
    targets, _issues = collect_solution_targets(blocks)
    diagnostics = []
    for owner_index in owners:
        position = _unit_position(units, owner_index)
        if position is None:
            continue
        unit_index, subtask_position = position
        if _has_help_deduction(targets, unit_index, subtask_position):
            continue
        unit = units[unit_index]
        letter = unit.subtasks[subtask_position].letter if subtask_position is not None else None
        label = f"Aufgabe {unit.number}{letter or ''}"
        diagnostics.append(
            _diag(
                owner_index,
                blocks,
                "KL013",
                f"{label} hat eine Lernhilfe, aber ihre Loesung enthaelt keinen Lernhilfe-Abzug -- "
                "z. B. `1. Lernhilfe genutzt (−1P Lh)`, damit die Nutzung in der Wertung zaehlt.",
            )
        )
    return diagnostics


def _unit_position(units, block_index):
    """``(unit_index, subtask_position)`` des Aufgaben-/Teilaufgabenblocks `block_index`, sonst ``None``."""
    for unit_index, unit in enumerate(units):
        if unit.block_index == block_index:
            return unit_index, None
        for subtask_position, subtask in enumerate(unit.subtasks):
            if subtask.block_index == block_index:
                return unit_index, subtask_position
    return None


def _has_help_deduction(targets, unit_index, subtask_position) -> bool:
    """Ob eine passende Lösung einen Abzug vom Typ „Lernhilfe“ enthält.

    Passend sind bei einer Teilaufgabe ihre eigene Lösung und die der Aufgabe,
    bei einer Aufgabe ihre eigene und die jeder ihrer Teilaufgaben.
    """
    for target in targets:
        if target.unit_index != unit_index:
            continue
        if subtask_position is not None and not target.is_task_level and target.subtask_position != subtask_position:
            continue
        if any(item.is_deduction and item.kind == LERNHILFE_KIND_KEY for item in target.items):
            return True
    return False


def _diag(index, blocks, code, message) -> BuildDiagnostic:
    """Warnung `code` am Block `index` mit Region und Anker wie alle Block-Diagnosen."""
    block_type, options, _content = blocks[index]
    return BuildDiagnostic(
        code=code,
        message=message,
        severity="warning",
        block_index=index,
        block_type=block_type,
        region_id=compute_block_region_id(block_type, options),
        anchor=code,
    )
