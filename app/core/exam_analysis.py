"""AFB- und Punkteauswertung einer Klausur (Nutzerentscheidungen R1-C16, R5-1, R5-5, R6-5).

Grundlage sind ausschließlich `points_model` (Punkte) und `resolve_aid_split`
(Teile). Gezählt werden **Blätter**: bei vollständig bepunkteten Teilaufgaben
jede Teilaufgabe (mit eigener oder vom Task geerbter AFB), sonst der Task.

* **Prozente beziehen sich immer auf die Gesamtpunktzahl der Klausur** --
  auch in den Zeilen für Teil A/B: `AFB-x-Anteil = AFB-x-Punkte / Gesamtpunkte × 100`.
* Prozente gibt es nur, wenn die Gesamtauswertung vollständig ist und die
  Gesamtpunktzahl > 0 ist; sonst nur Absolutwerte und markierte Gründe.
* Ohne gültigen Hilfsmittel-Trenner gibt es keine Teile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .document_semantics import resolve_aid_split
from .points_model import STATUS_MISSING, STATUS_OK, TaskUnit, build_points_model, format_points

AFB_LEVELS = (1, 2, 3)


@dataclass(frozen=True)
class ScoredLeaf:
    """Eine gezählte (Teil-)Aufgabe mit Punkten und AFB (``None`` = fehlt)."""

    block_index: int
    label: str
    points: Decimal
    afb: int | None


@dataclass
class PartResult:
    """Auswertung eines Teils (A/B) oder der ganzen Klausur."""

    label: str
    points: Decimal = Decimal(0)
    afb_points: dict[int, Decimal] = field(default_factory=lambda: {level: Decimal(0) for level in AFB_LEVELS})
    unassigned_points: Decimal = Decimal(0)
    reasons: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.reasons


@dataclass
class ExamAnalysis:
    """Gesamtergebnis; `parts` ist leer ohne gültigen Hilfsmittel-Trenner."""

    total: PartResult
    parts: list[PartResult]

    def percent(self, points: Decimal) -> Decimal | None:
        """Anteil an der Gesamtpunktzahl (``None`` bei unvollständiger Auswertung oder 0 Punkten)."""
        if not self.total.complete or self.total.points <= 0:
            return None
        return (points / self.total.points * 100).quantize(Decimal("0.1"))


def parse_afb(options: dict) -> int | None:
    raw = str((options or {}).get("afb") or "").strip()
    return int(raw) if raw in {"1", "2", "3"} else None


def iter_scored_leaves(units: list[TaskUnit]):
    """Liefert `(unit, leaf | None, grund | None)` für jede Einheit bzw. jedes Blatt."""
    for unit in units:
        task_afb = parse_afb(unit.options)
        if unit.status != STATUS_OK:
            reason = f"Aufgabe {unit.number} ohne Punkte" if unit.status == STATUS_MISSING else f"Aufgabe {unit.number} inkonsistent"
            yield unit, None, reason
            continue
        if unit.subtasks_pointed:
            for sub in unit.subtasks:
                afb = parse_afb(sub.options) or task_afb
                yield unit, ScoredLeaf(sub.block_index, f"Aufgabe {unit.number}{sub.letter or ''}", sub.value, afb), None
        else:
            yield unit, ScoredLeaf(unit.block_index, f"Aufgabe {unit.number}", unit.effective, task_afb), None


def analyze_exam(blocks, document_type: str) -> ExamAnalysis:
    """Wertet Punkte und AFB-Verteilung aus (gesamt und, falls vorhanden, je Teil)."""
    units = build_points_model(blocks)
    split = resolve_aid_split(blocks, document_type)
    total = PartResult("Gesamt")
    parts = [PartResult("Teil A"), PartResult("Teil B")] if split else []
    for unit, leaf, reason in iter_scored_leaves(units):
        targets = [total] + ([parts[0] if unit.block_index < split.index else parts[1]] if split else [])
        for part in targets:
            if reason:
                part.reasons.append(reason)
                continue
            part.points += leaf.points
            if leaf.afb is None:
                part.unassigned_points += leaf.points
            else:
                part.afb_points[leaf.afb] += leaf.points
    for part in [total] + parts:
        if part.unassigned_points:
            part.reasons.append(f"{format_points(part.unassigned_points)} P ohne AFB")
    return ExamAnalysis(total, parts)


def format_analysis_lines(analysis: ExamAnalysis) -> list[str]:
    """Textzeilen für Editor-Panel und Erwartungshorizont (gleiche Definition überall)."""
    lines = []
    for part in ([analysis.total] if not analysis.parts else analysis.parts + [analysis.total]):
        lines.append(f"{part.label}: {format_points(part.points)} P")
        for level in AFB_LEVELS:
            share = analysis.percent(part.afb_points[level])
            suffix = f" · {format_points(share)} %" if share is not None else ""
            lines.append(f"  AFB {'I' * level}: {format_points(part.afb_points[level])} P{suffix}")
        if part.reasons and part is analysis.total:
            lines.append("  unvollständig: " + "; ".join(dict.fromkeys(part.reasons)))
    if analysis.total.complete and analysis.total.points <= 0:
        lines.append("Keine Punkte vergeben.")
    return lines
