"""Bewertungstabelle `:::evaluation:::` (Plan Phase 7): eine Semantik für alle Renderpfade.

`build_evaluation_table` liefert die fachliche Tabelle (Datenklasse), die
Vorschau, HTML, PDF und PNG identisch über `render_evaluation_html` ausgeben.
Punkte kommen ausschließlich aus `points_model`, Teile aus `resolve_aid_split`.

* `level=task` (Standard): eine Spalte je Aufgabe mit ihren effektiven Punkten
  (bei nur bepunkteten Teilaufgaben deren Summe).
* `level=subtask`: je Aufgabe mit bepunkteten Teilaufgaben die Spalten 1a, 1b, …,
  sonst eine Spalte für die Aufgabe.
* Fehlende Punkte zeigen „–“ (EV001), inkonsistente „?“.
* Σ nur, wenn alle Zellen bekannt sind, sonst „–“ mit Fußnote.
* `parts=true` gruppiert bei gültigem Hilfsmittel-Trenner nach Teil A/B.
* `grade=true` hängt unter die Tabelle rechtsbündig leere Felder „Dies sind ___ %“
  und „Note: ___“ an -- genau einmal je Block (auch bei `parts=true`). Die
  Option gilt pro `evaluation`-Block; Blöcke ohne `grade` bekommen keine Felder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from html import escape

from .document_semantics import resolve_aid_split
from .document_type_registry import spec_for_type
from .points_model import STATUS_MISSING, STATUS_OK, build_points_model, format_points, subtask_effective

CELL_MISSING = "–"
CELL_INCONSISTENT = "?"


@dataclass(frozen=True)
class EvaluationCell:
    label: str
    points: Decimal | None
    marker: str | None  # None, "–" oder "?"


@dataclass
class EvaluationGroup:
    title: str | None
    cells: list[EvaluationCell] = field(default_factory=list)

    @property
    def total(self) -> Decimal | None:
        if any(cell.points is None for cell in self.cells):
            return None
        return sum((cell.points for cell in self.cells), Decimal(0))


@dataclass
class EvaluationTable:
    title: str | None
    groups: list[EvaluationGroup]
    missing_units: list[str] = field(default_factory=list)
    grade: bool = False

    @property
    def grand_total(self) -> Decimal | None:
        totals = [group.total for group in self.groups]
        return None if any(total is None for total in totals) else sum(totals, Decimal(0))


def _unit_cells(unit, level: str) -> list[EvaluationCell]:
    if unit.status == STATUS_OK and level == "subtask" and unit.subtasks_pointed:
        return [
            EvaluationCell(f"{unit.number}{sub.letter or ''}", subtask_effective(unit, sub), None)
            for sub in unit.subtasks
        ]
    if unit.status == STATUS_OK:
        return [EvaluationCell(unit.number, unit.effective, None)]
    marker = CELL_MISSING if unit.status == STATUS_MISSING else CELL_INCONSISTENT
    return [EvaluationCell(unit.number, None, marker)]


def build_evaluation_table(blocks, options: dict, document_type: str) -> EvaluationTable:
    """Baut die Tabelle für einen `:::evaluation`-Block aus dem ganzen Dokument."""
    level = "subtask" if str((options or {}).get("level") or "task").strip().lower() == "subtask" else "task"
    title = str((options or {}).get("title") or "").strip() or None
    units = build_points_model(blocks)
    split = resolve_aid_split(blocks, document_type)
    use_parts = split is not None and _option_true(options, "parts")
    groups = [EvaluationGroup("Teil A"), EvaluationGroup("Teil B")] if use_parts else [EvaluationGroup(None)]
    missing = []
    for unit in units:
        group = groups[0] if not use_parts or unit.block_index < split.index else groups[1]
        group.cells.extend(_unit_cells(unit, level))
        if unit.status == STATUS_MISSING:
            missing.append(unit.number)
    return EvaluationTable(title, groups, missing, grade=_option_true(options, "grade"))


def _option_true(options: dict | None, key: str) -> bool:
    """Ob eine boolesche Block-Option gesetzt ist (`true`, `1`, `ja`, `yes`)."""
    return str((options or {}).get(key) or "").strip().lower() in {"true", "1", "ja", "yes"}


def _grade_html() -> str:
    """Leere Felder für Prozent und Note, rechtsbündig unter der Tabelle."""
    return (
        "<div class='evaluation-grade'>"
        "<div class='evaluation-grade-row'>Dies sind <span class='evaluation-blank'></span> %</div>"
        "<div class='evaluation-grade-row'>Note: <span class='evaluation-blank'></span></div>"
        "</div>"
    )


def _group_html(group: EvaluationGroup) -> str:
    total = group.total
    header = "".join(f"<th>{escape(cell.label)}</th>" for cell in group.cells)
    maxima = "".join(
        f"<td>{escape(cell.marker) if cell.marker else format_points(cell.points)}</td>" for cell in group.cells
    )
    empty = "<td></td>" * len(group.cells)
    total_text = format_points(total) if total is not None else f"{CELL_MISSING}*"
    caption = f"<div class='evaluation-group-title'>{escape(group.title)}</div>" if group.title else ""
    return (
        f"{caption}<table class='evaluation-table'>"
        f"<tr><th>Aufgabe</th>{header}<th>Σ</th></tr>"
        f"<tr><th>max. Punkte</th>{maxima}<td>{total_text}</td></tr>"
        f"<tr><th>erreicht</th>{empty}<td></td></tr></table>"
    )


def render_evaluation_html(table: EvaluationTable) -> str:
    """HTML der Bewertungstabelle (für alle Renderpfade gleich)."""
    parts = [f"<div class='evaluation-title'>{escape(table.title)}</div>"] if table.title else []
    parts.extend(_group_html(group) for group in table.groups)
    if len(table.groups) > 1:
        grand = table.grand_total
        parts.append(f"<div class='evaluation-grand-total'>Gesamt: {format_points(grand) if grand is not None else CELL_MISSING + '*'} P</div>")
    if any(group.total is None for group in table.groups):
        parts.append("<div class='evaluation-footnote'>* Summe nicht ausgewiesen, weil nicht alle Punktzahlen bekannt sind.</div>")
    if table.grade:
        parts.append(_grade_html())
    return f"<div class='evaluation'>{''.join(parts)}</div>"


def annotate_evaluation_blocks(blocks, document_type: str):
    """Hängt an jeden `evaluation`-Block das fertige HTML (`_evaluation_html`) an.

    Nur für Typen mit Capability `evaluation` (Arbeitsblatt, Klausur); sonst
    bleibt der Block ohne Annotation und rendert nichts.
    """
    if not document_type or not spec_for_type(document_type).evaluation:
        return blocks
    if not any(block_type == "evaluation" for block_type, _o, _c in blocks):
        return blocks
    result = []
    for block_type, options, content in blocks:
        if block_type == "evaluation":
            table = build_evaluation_table(blocks, options, document_type)
            options = {**options, "_evaluation_html": render_evaluation_html(table)}
        result.append((block_type, options, content))
    return result
