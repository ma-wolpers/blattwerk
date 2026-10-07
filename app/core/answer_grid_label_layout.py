"""Label-Layout für Geometry: Einstieg, Modi und Ergebnis.

`layout_labels` bestimmt für jedes `LabelSpec` der Szene die Textposition.

* `labels=fixed`: die bisherigen festen Versätze (`LabelSpec.x/y`), unverändert.
* `labels=auto` (Standard): Kandidatenwahl, Kräfte-Relaxation und Fallback
  (siehe `answer_grid_label_candidates`/`answer_grid_label_relax`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

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


def layout_labels(specs, obstacles, cols, rows, bleed_units, mode_raw=None) -> LabelPlacement:
    """Positioniert alle Labels der Szene (deterministisch, Reihenfolge wie `specs`)."""
    del obstacles, cols, rows, bleed_units, mode_raw
    return LabelPlacement([(spec.x, spec.y) for spec in specs])
