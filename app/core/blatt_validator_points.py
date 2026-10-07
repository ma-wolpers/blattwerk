"""Punkt- und Lösungsdiagnosen (PK001–PK006, SL001/SL004/SL006/SL008–SL013).

Liest Punkte nur über `points_model` und Lösungs-Items nur über
`solution_items` (Invariante I4). Gilt für Arbeitsblätter und Klausuren.

Fehler (blockieren den Export wie alle Blattwerk-Fehler): PK001, PK002,
PK004, PK005, SL008, SL009, SL010, SL011. Warnungen: PK003, PK006, SL001,
SL004, SL006, SL012, SL013.

Teilpunkte `(x/nP)` (alternative Lösungswege, nicht summativ) ersetzen für
ihr Ziel die Summenprüfung PK002 durch SL009–SL012.
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
    has_partial = any(item.of_total is not None for item in target.items)
    if has_partial and any(item.points is not None and item.of_total is None for item in target.items):
        result.append(_diag(
            "SL013",
            f"Loesung zu {label}: `(xP)` und Teilpunkte `(x/nP)` gemischt -- alternative Wege einheitlich "
            "als `(x/nP)` angeben.",
            blocks, anchor_index,
        ))
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
    if has_partial:
        # Alternative Wege sind nicht summativ: PK002 entfällt, stattdessen SL009–SL012.
        if unit.status == STATUS_OK:
            result.extend(_partial_points_diagnostics(target, expected, label, blocks, anchor_index))
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


def _partial_points_diagnostics(target, expected: Decimal, label: str, blocks, anchor_index: int) -> list[BuildDiagnostic]:
    """Prüft Teilpunkte `(x/nP)` alternativer Lösungswege eines Ziels.

    Semantik: „x von n erreichbaren Punkten“, n ist die Punktzahl des Ziels.
    Alternative Wege sind nicht summativ, eine Überzahl (Σx > n) ist daher
    der beabsichtigte Normalfall und bleibt ohne Diagnose. Gemeldet werden:

    * SL009 (Fehler): ein Nenner n weicht von der Punktzahl des Ziels ab.
    * SL010 (Fehler): ein einzelner Zähler x ist größer als sein Nenner.
    * SL011 (Fehler): Σx < Punktzahl -- erreichbares Punktpotenzial fehlt.
    * SL012 (Warnung): Σx = Punktzahl -- die k/n-Notation ist redundant,
      dieselben Angaben gingen auch als gewöhnliche `(xP)`.

    Die Summenregeln SL011/SL012 gelten nur, wenn ausschließlich `(x/nP)`
    verwendet wird; bei Mischung meldet der Aufrufer bereits SL013.
    """
    result = []
    partial_items = [item for item in target.items if item.of_total is not None]
    for item in partial_items:
        if not isinstance(item.of_total, Decimal) or not isinstance(item.points, Decimal):
            continue
        if item.of_total != expected:
            result.append(_diag(
                "SL009",
                f"Loesung zu {label}: Teilpunkte `({format_points(item.points)}/{format_points(item.of_total)}P)` -- "
                f"der Nenner muss die Punktzahl von {label} sein ({format_points(expected)}).",
                blocks, anchor_index, "error",
            ))
        if item.points > item.of_total:
            result.append(_diag(
                "SL010",
                f"Loesung zu {label}: `({format_points(item.points)}/{format_points(item.of_total)}P)` -- "
                "ein Loesungsschritt kann nicht mehr Punkte bringen als erreichbar sind.",
                blocks, anchor_index, "error",
            ))
    if len(partial_items) != len(target.items):
        return result
    total = sum((item.points for item in partial_items if isinstance(item.points, Decimal)), Decimal(0))
    if total < expected:
        result.append(_diag(
            "SL011",
            f"Loesung zu {label}: Summe der Teilpunkte ({format_points(total)}) ist kleiner als die "
            f"Punktzahl ({format_points(expected)}) -- erreichbare Punkte fehlen.",
            blocks, anchor_index, "error",
        ))
    elif total == expected:
        result.append(_diag(
            "SL012",
            f"Loesung zu {label}: Summe der Teilpunkte entspricht genau der Punktzahl -- die Schreibweise "
            "`(x/nP)` ist hier unnoetig, `(xP)` genuegt.",
            blocks, anchor_index,
        ))
    return result
