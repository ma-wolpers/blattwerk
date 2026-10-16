"""Punkt- und Lösungsdiagnosen (PK001–PK006, SL001/SL004/SL006/SL008, SL014–SL016/SL018).

Liest Punkte nur über `points_model`, Lösungs-Items und ihre Summe nur über
`solution_items` und die Suffix-Grammatik nur über `points_suffix`
(Invariante I4). Gilt für Arbeitsblätter und Klausuren.

Fehler (blockieren den Export wie alle Blattwerk-Fehler): PK001, PK002,
PK004, PK005, SL008, SL014, SL018. Warnungen: PK003, PK006, SL001, SL004,
SL006, SL015, SL016.

Abzüge je Fehler (`(−0,5P)`) zählen in keine Summe; ein Weg-Buchstabe daran
ist wirkungslos (SL016).

Alternative Wege (`(0,5aP)`/`(1bP)`): PK002 vergleicht gemeinsam + bester
Weg exakt mit der Punktzahl. Ein altes (`(x/nP)`, SL014) oder unlesbares
(SL018) Suffix hat keinen Zahlenwert; für dieses Ziel entfallen deshalb
SL006, SL015 und PK002 (keine Doppelmeldung aus derselben Ursache). Die
früheren Teilpunkt-Diagnosen SL009–SL013 entfallen.
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
from .points_suffix import SUFFIX_GRAMMAR_HINT, SUFFIX_INVALID, SUFFIX_LEGACY
from .solution_items import collect_solution_targets, solution_points_total

POINTS_DOCUMENT_TYPES = frozenset({"worksheet", "exam"})


def _diag(code, message, blocks, index, severity="warning") -> BuildDiagnostic:
    """Diagnose am Block `index` mit Region und Anker wie alle Block-Diagnosen."""
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
    """Punktfehler einer Aufgabeneinheit aus `points_model` (PK001, PK003, PK004)."""
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
    """Diagnosen eines Lösungsziels (Aufgabe oder Teilaufgabe), Reihenfolge siehe Moduldocstring."""
    anchor_index = target.block_indices[0]
    label = f"Aufgabe {unit.number}" + (f"{target.subtask_letter}" if target.subtask_letter else "")
    result = []
    if target.misplaced_points:
        result.append(_diag(
            "SL004",
            f"Loesung zu {label}: Punkte `(xP)` zaehlen nur am Ende der ersten Zeile eines Loesungspunkts `1. …`.",
            blocks, anchor_index,
        ))
    unreadable = _unreadable_suffix_diagnostics(target, label, blocks, anchor_index)
    if unreadable:
        return result + unreadable
    for item in target.items:
        if item.is_deduction and item.path:
            result.append(_diag(
                "SL016",
                f"Loesung zu {label}: Abzug `{item.suffix_text}` mit Weg-Buchstabe -- Abzuege gelten fuer die ganze "
                "(Teil-)Aufgabe, der Buchstabe wird ignoriert.",
                blocks, anchor_index,
            ))
    paths = sorted({item.path for item in target.items if item.path and not item.is_deduction})
    if len(paths) == 1:
        result.append(_diag(
            "SL015",
            f"Loesung zu {label}: Nur Weg `{paths[0]}` ist markiert -- ohne zweiten Weg gibt es keine Alternative.",
            blocks, anchor_index,
        ))
    annotated = [item.points for item in target.items if item.points is not None]
    if not annotated:
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
    total = solution_points_total(target.items)
    if total.total != expected and unit.status == STATUS_OK:
        result.append(_diag(
            "PK002",
            f"Loesung zu {label}: Summe der Teilpunkte ({_total_text(total)}) "
            f"weicht von der Punktzahl ({format_points(expected)}) ab.",
            blocks, anchor_index, "error",
        ))
    return result


def _unreadable_suffix_diagnostics(target, label: str, blocks, anchor_index: int) -> list[BuildDiagnostic]:
    """SL014 (alte Schreibweise `(x/nP)`) und SL018 (unlesbares Suffix), je betroffenem Punkt, als Fehler."""
    result = []
    for item in target.items:
        if item.suffix_status == SUFFIX_LEGACY:
            result.append(_diag(
                "SL014",
                f"Loesung zu {label}: `{item.suffix_text}` -- die Teilpunkt-Schreibweise `(x/nP)` gibt es nicht mehr. "
                f"Erlaubt: {SUFFIX_GRAMMAR_HINT}; Punkte ohne Buchstabe gelten fuer alle Wege.",
                blocks, anchor_index, "error",
            ))
        elif item.suffix_status == SUFFIX_INVALID:
            result.append(_diag(
                "SL018",
                f"Loesung zu {label}: Punktangabe `{item.suffix_text}` ist nicht lesbar. Erlaubt: {SUFFIX_GRAMMAR_HINT}.",
                blocks, anchor_index, "error",
            ))
    return result


def _total_text(total) -> str:
    """Summe für PK002: `2` bzw. bei Wegen `gemeinsam 1 + bester Weg a 1 = 2`."""
    if not total.paths:
        return format_points(total.total)
    best = total.paths[total.best_path]
    return (
        f"gemeinsam {format_points(total.shared)} + bester Weg {total.best_path} "
        f"{format_points(best)} = {format_points(total.total)}"
    )
