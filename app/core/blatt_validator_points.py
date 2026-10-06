"""Punkt- und Lösungsdiagnosen (PK001–PK006, SL001/SL004/SL006/SL008).

Liest Punkte nur über `points_model` und Lösungs-Items nur über
`solution_items` (Invariante I4). Gilt für Arbeitsblätter und Klausuren.

Fehler (blockieren den Export wie alle Blattwerk-Fehler): PK001, PK002,
PK004, PK005, SL008. Warnungen: PK003, PK006, SL001, SL004, SL006.
"""

from __future__ import annotations

from decimal import Decimal

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .points_model import (
    STATUS_INCONSISTENT,
    STATUS_NON_NUMERIC,
    STATUS_OK,
    TaskUnit,
    build_points_model,
    format_points,
    subtask_effective,
)
from .solution_items import collect_solution_targets

POINTS_DOCUMENT_TYPES = frozenset({"worksheet", "exam"})


def _diag(code, message, blocks, index, severity="warning") -> BuildDiagnostic:
    block_type, options, _content = blocks[index]
    return BuildDiagnostic(
        code=code,
        message=message,
        severity=severity,
        block_index=index,
        block_type=block_type,
        region_id=compute_block_region_id(block_type, options),
        anchor=code,
    )


def validate_points(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """Prüft Punktangaben und Lösungspunkte (nur Arbeitsblatt und Klausur)."""
    if document_type not in POINTS_DOCUMENT_TYPES:
        return []
    units = build_points_model(blocks)
    diagnostics = [d for unit in units for d in _unit_diagnostics(unit, blocks)]
    targets, issues = collect_solution_targets(blocks)
    for issue in issues:
        severity = "error" if issue.code == "SL008" else "warning"
        diagnostics.append(_diag(issue.code, issue.message, blocks, issue.block_index, severity))
    for target in targets:
        diagnostics.extend(_target_diagnostics(target, units[target.unit_index], blocks))
    return diagnostics


def _unit_diagnostics(unit: TaskUnit, blocks) -> list[BuildDiagnostic]:
    label = f"Aufgabe {unit.number}"
    result = []
    if "PK001" in unit.codes:
        total = sum((sub.value for sub in unit.subtasks), Decimal(0))
        result.append(_diag(
            "PK001",
            f"{label}: `points={unit.raw}` passt nicht zur Summe der Teilaufgaben ({format_points(total)}).",
            blocks, unit.block_index, "error",
        ))
    if "PK004" in unit.codes:
        result.append(_diag(
            "PK004",
            f"{label}: Nur ein Teil der Teilaufgaben hat Punkte -- entweder alle oder keine bepunkten.",
            blocks, unit.block_index, "error",
        ))
    if "PK003" in unit.codes:
        result.append(_diag("PK003", f"{label}: Punktangabe ist keine Zahl.", blocks, unit.block_index))
    return result


def _target_diagnostics(target, unit: TaskUnit, blocks) -> list[BuildDiagnostic]:
    anchor_index = target.block_indices[0]
    label = f"Aufgabe {unit.number}" + (f"{target.subtask_letter}" if target.subtask_letter else "")
    result = []
    if target.misplaced_points:
        result.append(_diag(
            "SL004",
            f"Loesung zu {label}: Punkte `(xP)` zaehlen nur am Ende eines nummerierten Top-Level-Punkts.",
            blocks, anchor_index,
        ))
    annotated = [item.points for item in target.items if item.points is not None]
    if not annotated:
        return result
    if any(not isinstance(value, Decimal) for value in annotated):
        return result
    if target.is_task_level and unit.subtasks_pointed:
        result.append(_diag(
            "PK005",
            f"Loesung zu {label}: Teilpunkte auf Aufgabenebene, obwohl die Teilaufgaben bepunktet sind.",
            blocks, anchor_index, "error",
        ))
        return result
    if len(annotated) < len(target.items):
        result.append(_diag(
            "SL006",
            f"Loesung zu {label}: Nur ein Teil der Erwartungen hat Punkte -- keine Summenpruefung.",
            blocks, anchor_index,
        ))
        return result
    expected = unit.effective if target.is_task_level else subtask_effective(unit, unit.subtasks[target.subtask_position])
    if expected is None:
        if unit.status in (STATUS_INCONSISTENT, STATUS_NON_NUMERIC):
            return result  # Punktfehler der Aufgabe ist bereits gemeldet
        result.append(_diag(
            "PK006", f"Loesung zu {label}: Teilpunkte vergeben, aber {label} hat keine eigene Punktzahl.",
            blocks, anchor_index,
        ))
        return result
    total = sum(annotated, Decimal(0))
    if total != expected and unit.status == STATUS_OK:
        result.append(_diag(
            "PK002",
            f"Loesung zu {label}: Summe der Teilpunkte ({format_points(total)}) "
            f"weicht von der Punktzahl ({format_points(expected)}) ab.",
            blocks, anchor_index, "error",
        ))
    return result
