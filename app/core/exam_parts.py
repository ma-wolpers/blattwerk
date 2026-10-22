"""Klausurteile: ein Modell für alle Teil-Auswertungen (Hilfsmittel- und Wahlteile).

Einzige Semantik der Teil-Trenner. `resolve_exam_parts` liefert entweder ein
gültiges `ExamPartLayout` oder -- bei struktureller Ungültigkeit -- kein Layout
und die Probleme (Codes), die der Validator als Fehler meldet. Alle
Konsumenten (Bewertungstabelle, Analyse, Erwartungshorizont, Operatorenlegende,
Rendern) fragen nur das Layout; keiner kennt feste Teile A/B.

Bereichsvertrag: Die Teile decken die Blockliste lückenlos ab. Der erste Teil
beginnt bei Block 0 und schließt ein Deckblatt ein (das keine Aufgaben enthält,
also keine Auswertung verändert); jeder weitere Teil beginnt an seinem
Trenner. `marker_block` ist der Trenner, an dem der Teil im Dokument beginnt
-- nur der erste Teil darf keinen haben (ohne Deckblatt steht Teil A am
Dokumentanfang und bekommt beim Rendern einen synthetischen Block).

Die Konsistenz eines Layouts prüft `exam_parts_invariants.check_layout` beim
Erzeugen (Programmierfehler → `ValueError`, keine Nutzerdiagnose).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from .document_type_registry import spec_for_type
from .exam_parts_choice import ChoiceRegion, choice_split_indices, resolve_choice_regions
from .exam_parts_invariants import PART_KIND_AID, PART_KIND_CHOICE, PART_KIND_REQUIRED, check_layout
from .exam_parts_position import (  # noqa: F401 (Re-Export der Trenner-Blocktypen)
    AID_SPLIT_BLOCK,
    CHOICE_SPLIT_BLOCK,
    PART_SPLIT_BLOCKS,
    aid_cover_position_problem,
    aid_split_position_problem,
)

MAX_AID_SPLITS = 2
"""Höchstens zwei `--hm`: mit zweitem Marker trennt der erste ein Deckblatt ab."""

AID_PART_SHORT_LABELS = {"A": "Teil A", "B": "Teil B"}
"""Kurznamen für Tabellen und Auswertungen."""
AID_PART_LABELS = {"A": "Teil A – hilfsmittelfrei", "B": "Teil B – mit Hilfsmitteln"}
"""Überschriften der Hilfsmittelteile im Dokument und im Erwartungshorizont."""
REQUIRED_PART_LABEL = "Pflichtteil"
"""Kurzname des Bereichs vor dem ersten Wahlbereich ohne `--hm` (ohne Überschrift im Dokument)."""


@dataclass(frozen=True)
class ExamPart:
    """Ein Klausurteil.

    Attributes:
        order: Position in Dokumentreihenfolge (0, 1, …, lückenlos).
        part_id: Eindeutige Kennung (`A`, `B`, `P` = Pflichtteil, `W<g>.<n>` = Wahlteil).
        kind: `aid` (Hilfsmittelteil), `required` (Pflichtteil) oder `choice` (Wahlteil).
        label: Kurzname für Tabellen und Auswertungen („Teil A“, „Wahlteil 2“).
        heading: Überschrift im Dokument („Teil A – hilfsmittelfrei“); leer = keine
            Überschrift (Pflichtteil).
        start_block: Erster Blockindex des Bereichs (inklusive).
        end_block: Blockindex nach dem Bereich (exklusive).
        marker_block: Blockindex des Trenners, an dem der Teil beginnt, oder
            ``None`` (nur erster Teil ohne Deckblatt).
        group_id: Wahlgruppe eines `choice`-Teils, sonst ``None``.
        page_break: Teil beginnt auf einer neuen Seite -- genau dann, wenn er
            an einem Trenner beginnt und es der erste Teil ist oder der vorige
            Teil Aufgaben enthält (eine aufgabenlose Überschrift wie „Teil B“
            direkt vor einem Wahlbereich steht so nie allein auf einer Seite).
    """

    order: int
    part_id: str
    kind: str
    label: str
    heading: str
    start_block: int
    end_block: int
    marker_block: int | None
    group_id: str | None = None
    page_break: bool = False

    def contains(self, block_index: int) -> bool:
        """Ob der Blockindex in den Bereich dieses Teils fällt."""
        return self.start_block <= block_index < self.end_block


@dataclass(frozen=True)
class ChoiceGroup:
    """Wahlbereich: von `len(part_ids)` Teilen sind `k` zu bearbeiten."""

    group_id: str
    k: int
    part_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExamPartLayout:
    """Gültige Teilstruktur einer Klausur (Invarianten siehe `check_layout`).

    Attributes:
        parts: Teile in Dokumentreihenfolge.
        groups: Wahlgruppen (leer ohne Wahlteile).
        cover_end: Blockindex des Deckblatt-Trenners oder ``None``.
    """

    parts: tuple[ExamPart, ...]
    groups: tuple[ChoiceGroup, ...] = ()
    cover_end: int | None = None

    def __post_init__(self) -> None:
        check_layout(self)

    def part_for_block(self, block_index: int) -> ExamPart:
        """Der Teil, in dessen Bereich der Blockindex liegt (Indizes vor `annotate`)."""
        for part in self.parts:
            if part.contains(block_index):
                return part
        raise IndexError(f"Blockindex {block_index} liegt in keinem Klausurteil")


@dataclass(frozen=True)
class ExamPartProblem:
    """Strukturproblem eines Trenners (Code wie `KL004`, Meldung im Validator)."""

    code: str
    block_index: int


@dataclass(frozen=True)
class ExamPartResolution:
    """Ergebnis von `resolve_exam_parts`: Layout oder ``None`` plus Probleme."""

    layout: ExamPartLayout | None
    problems: tuple[ExamPartProblem, ...] = ()


def aid_split_indices(blocks) -> list[int]:
    """Blockindizes aller `aidsplit`-Pseudoblöcke in Dokumentreihenfolge."""
    return [index for index, (block_type, _o, _c) in enumerate(blocks) if block_type == AID_SPLIT_BLOCK]


def resolve_exam_parts(blocks, document_type: str | None) -> ExamPartResolution:
    """Einzige Semantik der Teil-Trenner (deterministisch, ohne Seiteneffekte).

    * Typ ohne Teile (alles außer Klausur): kein Layout; jeder `--hm` ist
      `KL002` (Warnung, wirkt nicht), jeder `--w` `KL012` (Fehler).
    * `--hm`: ein Marker Teil A | Teil B, zwei Deckblatt | Teil A | Teil B.
    * `--w[k]`/`--w`: Wahlbereiche (`exam_parts_choice`), kombinierbar mit `--hm`.
    * Jedes Strukturproblem (`KL001`, `KL004`, `KL005`, `KL007`–`KL010`):
      kein Layout -- der Validator meldet Fehler, der Build wird blockiert.
    """
    aid = aid_split_indices(blocks)
    choice = choice_split_indices(blocks)
    if not document_type or not spec_for_type(document_type).aid_split:
        problems = [ExamPartProblem("KL002", index) for index in aid] + [ExamPartProblem("KL012", index) for index in choice]
        return ExamPartResolution(None, tuple(sorted(problems, key=lambda problem: problem.block_index)))
    problems = list(_aid_problems(blocks, aid))
    cover = aid[0] if len(aid) == MAX_AID_SPLITS else None
    separators = sorted([index for index in aid if index != cover] + choice)
    regions, choice_problems = resolve_choice_regions(blocks, separators)
    problems.extend(ExamPartProblem(code, index) for code, index in choice_problems)
    problems.sort(key=lambda problem: problem.block_index)
    if problems or not separators:
        return ExamPartResolution(None, tuple(problems))
    return ExamPartResolution(_build_layout(blocks, separators, regions, cover))


def _aid_problems(blocks, indices: list[int]) -> tuple[ExamPartProblem, ...]:
    """Positionsprobleme aller `--hm` (Reihenfolge = Dokumentreihenfolge)."""
    problems = []
    has_cover = len(indices) == MAX_AID_SPLITS
    for position, index in enumerate(indices):
        if position >= MAX_AID_SPLITS:
            problems.append(ExamPartProblem("KL001", index))
            continue
        if has_cover and position == 0:
            code = aid_cover_position_problem(blocks, index)
        else:
            code = aid_split_position_problem(blocks, index, start=indices[0] + 1 if has_cover else 0)
        if code:
            problems.append(ExamPartProblem(code, index))
    return tuple(problems)


def _build_layout(blocks, separators: list[int], regions: list[ChoiceRegion], cover: int | None) -> ExamPartLayout:
    """Zerlegt die Blockliste an den Trennern in Teile (Bereichsvertrag siehe Moduldoku).

    Vor dem ersten Trenner steht Teil A (mit `--hm`, schließt ein Deckblatt
    ein) bzw. der Pflichtteil (ohne `--hm`); ab dem A/B-`--hm` Teil B; ab
    jedem `--w` ein Wahlteil seines Bereichs.
    """
    choice_info: dict[int, tuple[int, int]] = {}
    groups = []
    for group_no, region in enumerate(regions, start=1):
        for position, index in enumerate(region.marker_indices, start=1):
            choice_info[index] = (group_no, position)
        part_ids = tuple(f"W{group_no}.{position}" for position in range(1, len(region.marker_indices) + 1))
        groups.append(ChoiceGroup(f"G{group_no}", region.k, part_ids))
    specs = []
    if separators[0] > 0:
        if any(blocks[index][0] == AID_SPLIT_BLOCK for index in separators):
            specs.append(("A", PART_KIND_AID, AID_PART_SHORT_LABELS["A"], AID_PART_LABELS["A"], 0, separators[0], cover, None))
        else:
            specs.append(("P", PART_KIND_REQUIRED, REQUIRED_PART_LABEL, "", 0, separators[0], None, None))
    for index, end in zip(separators, separators[1:] + [len(blocks)]):
        start = index if specs else 0
        if index in choice_info:
            group_no, position = choice_info[index]
            label = f"Wahlteil {position}"
            title = str(blocks[index][1].get("title") or "").strip()
            heading = f"{label} – {title}" if title else label
            specs.append((f"W{group_no}.{position}", PART_KIND_CHOICE, label, heading, start, end, index, f"G{group_no}"))
        else:
            specs.append(("B", PART_KIND_AID, AID_PART_SHORT_LABELS["B"], AID_PART_LABELS["B"], start, end, index, None))
    parts = []
    for order, spec in enumerate(specs):
        previous = specs[order - 1] if order else None
        page_break = spec[6] is not None and (previous is None or _has_task(blocks, previous[4], previous[5]))
        parts.append(ExamPart(order, *spec, page_break=page_break))
    return ExamPartLayout(tuple(parts), tuple(groups), cover_end=cover)


def _has_task(blocks, start: int, end: int) -> bool:
    """Ob im Blockbereich eine Aufgabe (`task`) steht."""
    return any(block_type == "task" for block_type, _o, _c in blocks[start:end])


def exam_max_points(layout: ExamPartLayout, part_points: Mapping[str, Decimal | None]) -> Decimal | None:
    """Einzige Quelle der erreichbaren Gesamtpunktzahl einer Klausur mit Teilen.

    Teile außerhalb von Wahlgruppen zählen voll; eine Wahlgruppe zählt mit
    der Summe ihrer `k` punktstärksten Teile (bei gleichen Punkten k × p).

    Args:
        layout: Gültiges Layout.
        part_points: Punkte je `part_id`; ``None`` = unbekannt.

    Returns:
        Die Summe oder ``None``, sobald ein beteiligter Wert unbekannt ist.
    """
    values = {part.part_id: part_points.get(part.part_id) for part in layout.parts}
    if any(value is None for value in values.values()):
        return None
    grouped = {part_id for group in layout.groups for part_id in group.part_ids}
    total = sum((value for part_id, value in values.items() if part_id not in grouped), Decimal(0))
    for group in layout.groups:
        best = sorted((values[part_id] for part_id in group.part_ids), reverse=True)[: group.k]
        total += sum(best, Decimal(0))
    return total
