"""Lösungsteile, die wegen der Lösungsdarstellung des Typs nie erscheinen (`AN055`).

In Typen mit Lösungen pro Block (Präsentation) zeigen nur lösungsfähige
Blöcke mit `mode=solution` ihre Lösungen (`block_mode_policy`). `task` und
`subtask` gehören nicht dazu: `%`-markierte Teile im Aufgabentext würden dort
still verschwinden. **AN055 (Warnung)** meldet das, damit nichts unbemerkt
fehlt -- der Teil gehört in `:::solution` oder in einen Antwortblock mit
`mode=solution`.

Ob ein Block seine Lösungsvariante zeigt, entscheidet allein
`blatt_kern_shared_blocks.block_shows_solutions` (dieselbe Regel wie beim
Rendern); die Segmente kommen aus
`blatt_validator_marker_syntax.content_visibility_modes`.
"""

from __future__ import annotations

from .blatt_kern_shared_blocks import block_shows_solutions
from .blatt_validator_marker_syntax import content_visibility_modes
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .block_mode_policy import SHOW_MODE_SOLUTION
from .document_type_registry import solutions_per_block

_TASK_BLOCK_TYPES = frozenset({"task", "subtask"})


def validate_solution_display(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """`AN055` je `task`/`subtask`, deren `%`-Teile in diesem Typ nie sichtbar werden.

    Args:
        blocks: geparste Blockliste.
        document_type: Typ aus der Dateiendung; nur Typen mit Lösungen pro
            Block werden geprüft.
    """
    if not solutions_per_block(document_type):
        return []
    diagnostics = []
    for index, (block_type, options, content) in enumerate(blocks):
        if block_type not in _TASK_BLOCK_TYPES:
            continue
        if block_shows_solutions(block_type, options, False, document_type):
            continue
        if SHOW_MODE_SOLUTION not in content_visibility_modes(content):
            continue
        diagnostics.append(
            BuildDiagnostic(
                code="AN055",
                message=(
                    f"`%`-Lösungsteile in `:::{block_type}` erscheinen in Präsentationen nie. "
                    "Lösungen gehören dort in `:::solution` oder in einen Antwortblock mit "
                    "`mode=solution`."
                ),
                block_index=index,
                block_type=block_type,
                region_id=compute_block_region_id(block_type, options),
                anchor="AN055",
            )
        )
    return diagnostics
