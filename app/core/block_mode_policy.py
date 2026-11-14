"""Bedeutung der Block-Optionen `mode`/`show` -- einzige Quelle für Renderer, Validator und Editor.

`mode=worksheet|solution` (Legacy-Alias `show=`, zusätzlich `both`) heißt je
nach Lösungsdarstellung des Dokumenttyps
(`document_type_registry.solution_display`) zweierlei:

* **Eigene Lösungsfassung** (Arbeitsblatt, Klausur): Sichtbarkeit je Fassung.
  `mode=worksheet` erscheint nur im Aufgabenblatt, `mode=solution` nur in der
  Lösungsfassung. Gilt für jeden Block mit `mode` im Spec.
* **Lösungen pro Block** (Präsentation): Jeder Block ist sichtbar.
  `mode` wählt nur bei **lösungsfähigen** Blöcken
  (`SOLUTION_VARIANT_BLOCK_TYPES`), ob ihre Lösungen eingetragen erscheinen
  (`mode=solution`) oder nicht (ohne Angabe bzw. `mode=worksheet`, z. B.
  leere Lücken). An allen anderen Blöcken ist `mode`/`show` dort wirkungslos
  und veraltet (`OP004`), ebenso an `:::solution` in jedem Typ.

Lösungsfähig sind genau die Blöcke, deren Renderer eine Lösungsvariante
haben: die Antwortblöcke und die Diagrammblöcke (beide bekommen
`include_solutions`). `task`/`subtask` zählen nicht -- `%`-Teile im
Aufgabentext erscheinen in Präsentationen deshalb nie (`AN055`).
"""

from __future__ import annotations

from .blatt_validator_constants import ANSWER_BLOCK_TYPES
from .diagram_block_catalog import DIAGRAM_BLOCK_NAMES
from .document_type_registry import solutions_per_block

SOLUTION_VARIANT_BLOCK_TYPES = frozenset(ANSWER_BLOCK_TYPES) | DIAGRAM_BLOCK_NAMES
"""Blöcke mit Lösungsvariante; jeder hat `mode` im Spec (Guardrail-Test)."""

SHOW_MODE_WORKSHEET = "worksheet"
SHOW_MODE_SOLUTION = "solution"
SHOW_MODE_BOTH = "both"

DEFAULT_SHOW_MODE_BY_BLOCK_TYPE = {"operators": SHOW_MODE_WORKSHEET}
"""Abweichender Standard ohne `mode`/`show` (sonst „both“).

`operators`: Die Operatorentabelle erscheint wie die frühere automatische
Liste nur in der Arbeitsblattfassung; `mode=solution` zeigt sie nur in der
Lösungsfassung.
"""

VISIBILITY_OPTION_KEYS = frozenset({"mode", "show"})

_SOLUTION_DEPRECATED_KEYS = frozenset({"mode", "show", "target"})
"""Stehen bewusst nicht im Spec von `:::solution` (keine Completion): Lösungen werden nie
bewertet, `target=` ordnet seitdem `:::expectation` zu."""
_SOLUTION_REASON = "Lösungen erscheinen nur in der Lösungsfassung."
_SOLUTION_REASON_PER_BLOCK = "`:::solution` ist in Präsentationen immer sichtbar."
_PER_BLOCK_REASON = (
    "In Präsentationen sind alle Blöcke sichtbar; `mode` entscheidet nur bei Antwort- und "
    "Diagrammblöcken, ob ihre Lösungen eingetragen erscheinen."
)


def block_show_mode(block_type, options) -> str:
    """Die gesetzte Fassung eines Blocks: `mode`, sonst Legacy-`show`, sonst Typ-Standard.

    Args:
        block_type: Blocktyp.
        options: Blockoptionen (``None`` erlaubt).

    Returns:
        ``"worksheet"``, ``"solution"`` oder ``"both"``.
    """
    options = options or {}
    mode_raw = str(options.get("mode") or "").strip().lower()
    if mode_raw in {SHOW_MODE_WORKSHEET, SHOW_MODE_SOLUTION}:
        return mode_raw
    show_raw = str(options.get("show") or "").strip().lower()
    if show_raw in {SHOW_MODE_WORKSHEET, SHOW_MODE_SOLUTION, SHOW_MODE_BOTH}:
        return show_raw
    return DEFAULT_SHOW_MODE_BY_BLOCK_TYPE.get(block_type, SHOW_MODE_BOTH)


def deprecated_ignored_options(block_type, document_type) -> frozenset[str]:
    """Optionen, die an diesem Block in diesem Typ veraltet sind und ignoriert werden (`OP004`).

    Validator (Meldung) und Editor-Completion (kein Vorschlag) fragen beide hier.
    """
    if block_type == "solution":
        return _SOLUTION_DEPRECATED_KEYS
    if solutions_per_block(document_type) and block_type not in SOLUTION_VARIANT_BLOCK_TYPES:
        return VISIBILITY_OPTION_KEYS
    return frozenset()


def deprecated_option_reason(block_type, document_type) -> str:
    """Begründungssatz der `OP004`-Meldung für `deprecated_ignored_options`."""
    if block_type == "solution":
        return _SOLUTION_REASON_PER_BLOCK if solutions_per_block(document_type) else _SOLUTION_REASON
    return _PER_BLOCK_REASON
