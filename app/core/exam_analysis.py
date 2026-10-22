"""AFB- und Punkteauswertung einer Klausur (Nutzerentscheidungen R1-C16, R5-1, R5-5, R6-5).

Grundlage sind ausschließlich `points_model` (Punkte) und `exam_parts.resolve_exam_parts`
(Teile); die Gesamtpunktzahl einer Klausur mit Teilen kommt aus `exam_parts.exam_max_points`. Gezählt werden **Blätter**: bei vollständig bepunkteten Teilaufgaben
jede Teilaufgabe (mit eigener oder vom Task geerbter AFB), sonst der Task.

* **Prozente beziehen sich immer auf die Gesamtpunktzahl der Klausur** --
  auch in den Zeilen für Teil A/B: `AFB-x-Anteil = AFB-x-Punkte / Gesamtpunkte × 100`.
* Prozente gibt es nur, wenn die Gesamtauswertung vollständig ist und die
  Gesamtpunktzahl > 0 ist; sonst nur Absolutwerte und markierte Gründe.
* Ohne gültige Teilstruktur gibt es keine Teile; Teile ohne Aufgaben (z. B.
  ein Pflichtteil, der nur eine Einleitung enthält) erscheinen nicht.
* Mit Wahlteilen (Nutzerentscheidung Schritt 6b) gibt es **keine Gesamt-AFB**:
  Die Gesamtzeile zeigt nur die erreichbaren Punkte (`exam_max_points`, k ×
  Punkte eines Wahlteils), die AFB-Verteilung steht nur je Teil.
* Bonuspunkte (`bonus=true`) zählen weder zur Punktzahl noch zur AFB-Verteilung;
  sie werden je Teil getrennt als `bonus_points` geführt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .exam_parts import exam_max_points, resolve_exam_parts
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
    """Auswertung eines Klausurteils oder der ganzen Klausur."""

    label: str
    points: Decimal = Decimal(0)
    afb_points: dict[int, Decimal] = field(default_factory=lambda: {level: Decimal(0) for level in AFB_LEVELS})
    unassigned_points: Decimal = Decimal(0)
    reasons: list[str] = field(default_factory=list)
    leaf_count: int = 0
    bonus_points: Decimal = Decimal(0)

    @property
    def complete(self) -> bool:
        """Ob die Auswertung dieses Teils ohne fehlende Angaben ist."""
        return not self.reasons


@dataclass
class ExamAnalysis:
    """Gesamtergebnis; `parts` (je Klausurteil) ist leer ohne gültige Teilstruktur."""

    total: PartResult
    parts: list[PartResult]
    has_choices: bool = False

    def percent(self, points: Decimal) -> Decimal | None:
        """Anteil an der Gesamtpunktzahl (``None`` bei unvollständiger Auswertung oder 0 Punkten)."""
        if not self.total.complete or self.total.points <= 0:
            return None
        return (points / self.total.points * 100).quantize(Decimal("0.1"))


def parse_afb(options: dict) -> int | None:
    """AFB-Stufe aus `afb=1|2|3` (sonst ``None``)."""
    raw = str((options or {}).get("afb") or "").strip()
    return int(raw) if raw in {"1", "2", "3"} else None


def iter_scored_leaves(units: list[TaskUnit]):
    """Liefert `(unit, leaf | None, grund | None)` für jede Einheit bzw. jedes reguläre Blatt.

    Bonus-Aufgaben und Bonus-Teilaufgaben sind keine Blätter (siehe `bonus_points`).
    """
    for unit in units:
        task_afb = parse_afb(unit.options)
        if unit.status == STATUS_OK and unit.is_bonus:
            continue
        if unit.status != STATUS_OK:
            reason = f"Aufgabe {unit.number} ohne Punkte" if unit.status == STATUS_MISSING else f"Aufgabe {unit.number} inkonsistent"
            yield unit, None, reason
            continue
        if unit.subtasks_pointed:
            for sub in unit.subtasks:
                if sub.is_bonus:
                    continue
                afb = parse_afb(sub.options) or task_afb
                yield unit, ScoredLeaf(sub.block_index, f"Aufgabe {unit.number}{sub.letter or ''}", sub.value, afb), None
        else:
            yield unit, ScoredLeaf(unit.block_index, f"Aufgabe {unit.number}", unit.effective, task_afb), None


def analyze_exam(blocks, document_type: str) -> ExamAnalysis:
    """Wertet Punkte und AFB-Verteilung aus (gesamt und, falls vorhanden, je Teil)."""
    units = build_points_model(blocks)
    layout = resolve_exam_parts(blocks, document_type).layout
    total = PartResult("Gesamt")
    parts = [PartResult(part.label) for part in layout.parts] if layout else []
    for unit in units:
        for part in [total] + ([parts[layout.part_for_block(unit.block_index).order]] if layout else []):
            part.bonus_points += unit.bonus_points
    for unit, leaf, reason in iter_scored_leaves(units):
        targets = [total] + ([parts[layout.part_for_block(unit.block_index).order]] if layout else [])
        for part in targets:
            part.leaf_count += 1
            if reason:
                part.reasons.append(reason)
                continue
            part.points += leaf.points
            if leaf.afb is None:
                part.unassigned_points += leaf.points
            else:
                part.afb_points[leaf.afb] += leaf.points
    if layout is not None:
        total.points = exam_max_points(layout, {part.part_id: result.points for part, result in zip(layout.parts, parts)})
    for part in [total] + parts:
        if part.unassigned_points:
            part.reasons.append(f"{format_points(part.unassigned_points)} P ohne AFB")
    return ExamAnalysis(total, parts, has_choices=bool(layout and layout.groups))


def format_analysis_lines(analysis: ExamAnalysis) -> list[str]:
    """Textzeilen für Editor-Panel und Erwartungshorizont (gleiche Definition überall)."""
    lines = []
    shown_parts = [part for part in analysis.parts if part.leaf_count]
    for part in ([analysis.total] if not analysis.parts else shown_parts + [analysis.total]):
        bonus = f" + {format_points(part.bonus_points)} Bonuspunkte" if part.bonus_points else ""
        lines.append(f"{part.label}: {format_points(part.points)} P{bonus}")
        if part is analysis.total and analysis.has_choices:
            lines.append("  AFB nur je Teil (Wahlteile)")
        for level in AFB_LEVELS if not (part is analysis.total and analysis.has_choices) else ():
            share = analysis.percent(part.afb_points[level])
            suffix = f" · {format_points(share)} %" if share is not None else ""
            lines.append(f"  AFB {'I' * level}: {format_points(part.afb_points[level])} P{suffix}")
        if part.reasons and part is analysis.total:
            lines.append("  unvollständig: " + "; ".join(dict.fromkeys(part.reasons)))
    if analysis.total.complete and analysis.total.points <= 0:
        lines.append("Keine Punkte vergeben.")
    return lines
