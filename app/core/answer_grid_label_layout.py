"""Label-Layout für Geometry: Einstieg, Modi, Ablauf und Fallback.

`layout_labels` bestimmt für jedes `LabelSpec` der Szene die Textposition.

* `labels=fixed`: die bisherigen festen Versätze (`LabelSpec.x/y`), unverändert.
* `labels=auto` (Standard), in drei Phasen:

  1. **Kandidatenwahl** (gierig, in Szenenreihenfolge): je Label der beste
     zulässige Kandidat nach dem lexikographischen Kostentupel
     (`answer_grid_label_candidates`); frühere Labels zählen für spätere als
     Hindernis der Stufe 2.
  2. **Kräfte-Relaxation** (`answer_grid_label_relax`) für Labels, die noch eine
     Kollision der Stufen 1–3 haben; monoton, nie schlechter als Phase 1.
  3. **Fallback**: Überdeckt ein Label danach noch ein Punktkreuz oder ein
     anderes Label, folgt eine erweiterte Ringsuche bis zum Maximalradius
     (weiterhin nur zulässige Positionen). Bleibt die Kollision, gilt der
     lexikographisch beste Kandidat -- notfalls lieber ein Label überdecken
     als ein Punktkreuz -- und das Label landet in `unresolved` (Diagnose
     AN019). Kollisionen mit Linien/Achsen sind dann hinnehmbar.

Feste Labels (Tick-Zahlen) werden nie bewegt und zählen als Hindernis der
Achsen-Stufe. Ist für ein Label keine einzige Position zulässig (sehr kleine
Zone), bleibt es an seiner Standardposition. Komplexität O(L·C·(O+L)) mit
Hüllbox-Vorfilter; Annahme: kleine Geometrien (L ≤ ~50 Labels, O ≤ ~1000
Hindernisstücke).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .answer_grid_label_candidates import (
    LayoutContext,
    best_candidate,
    candidate_positions,
    cost,
    extended_positions,
    has_collision,
    has_hard_collision,
)
from .answer_grid_label_model import text_box
from .answer_grid_label_relax import relax

LABELS_AUTO = "auto"
LABELS_FIXED = "fixed"


@dataclass
class LabelPlacement:
    """Ergebnis des Layouts: Position je Label (Reihenfolge wie die Specs) und ungelöste Labels."""

    positions: list[tuple[float, float]]
    unresolved: list[str] = field(default_factory=list)


def resolve_labels_mode(raw) -> str:
    """Normalisierte Block-Option `labels`; alles außer `fixed` gilt als `auto` (OP002 meldet Ungültiges)."""
    return LABELS_FIXED if str(raw or "").strip().lower() == LABELS_FIXED else LABELS_AUTO


def layout_zone(cols, rows, bleed_units) -> tuple[float, float, float, float]:
    """Zulässige Zone: Zeichenfläche plus bestehender Bleed-Rand `(oben, rechts, unten, links)`."""
    top, right, bottom, left = bleed_units
    return (-float(left), -float(top), float(cols) + float(right), float(rows) + float(bottom))


def _other_boxes(specs, positions, members, index):
    return [text_box(specs[i], *positions[i]) for i in members if i != index]


def layout_labels(specs, obstacles, cols, rows, bleed_units, mode_raw=None) -> LabelPlacement:
    """Positioniert alle Labels der Szene (deterministisch, Reihenfolge wie `specs`)."""
    defaults = [(spec.x, spec.y) for spec in specs]
    if resolve_labels_mode(mode_raw) == LABELS_FIXED or not specs:
        return LabelPlacement(defaults)

    context = LayoutContext(
        obstacles=tuple(obstacles),
        fixed_boxes=tuple(text_box(spec, spec.x, spec.y) for spec in specs if not spec.movable),
        zone=layout_zone(cols, rows, bleed_units),
    )
    members = [index for index, spec in enumerate(specs) if spec.movable]
    positions = list(defaults)

    placed: list[int] = []
    for index in members:
        others = [text_box(specs[i], *positions[i]) for i in placed]
        best = best_candidate(specs[index], candidate_positions(specs[index]), context, others)
        if best is not None:
            positions[index] = best[0]
        placed.append(index)

    active = [
        index for index in members
        if has_collision(cost(specs[index], positions[index], context, _other_boxes(specs, positions, members, index), 0))
    ]
    if active:
        positions = relax(specs, positions, list(positions), context, members, active)

    unresolved: list[str] = []
    for index in members:
        spec = specs[index]
        current = cost(spec, positions[index], context, _other_boxes(specs, positions, members, index), 0)
        if not has_hard_collision(current):
            continue
        others = _other_boxes(specs, positions, members, index)
        best = best_candidate(spec, extended_positions(spec), context, others, start_index=1)
        if best is not None and best[1][:4] < current[:4]:
            positions[index] = best[0]
            current = best[1]
        if has_hard_collision(current):
            unresolved.append(spec.text)
    return LabelPlacement(positions, unresolved)
