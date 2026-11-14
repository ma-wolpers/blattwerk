"""Blocktypen, die es nur in bestimmten Dokumenttypen gibt -- eine Tabelle, ein Prüfer.

Früher prüfte jede Regel selbst und jede anders: `BL012` über
`has_slide_layout` als Ersatz für eine fehlende Lernhilfen-Capability, `EV002`
über die Spec, `OPR007` über `shows_operator_legend`. Jetzt nennt jeder
Eintrag die Registry-Capability (`document_type_registry`), von der der Block
abhängt, und `validate_block_availability` meldet jeden Block, dessen
Capability im Typ fehlt. Die fachlichen Folgeprüfungen (Lernhilfe-Abzug,
Bewertungstabelle, Operatorabdeckung) laufen nur, wenn der Typ die Capability
hat, und fragen dafür dieselben Registry-Funktionen.

| Block          | Capability             | Code     | Folge im Typ ohne Capability       |
|----------------|------------------------|----------|------------------------------------|
| `help`         | `has_help_cards`       | `BL012`  | veraltet, wird noch dargestellt    |
| `evaluation`   | `has_evaluation`       | `EV002`  | wird nicht dargestellt             |
| `operators`    | `shows_operator_legend`| `OPR007` | wird nicht dargestellt             |
| `expectation`  | `has_points`           | `BL018`  | wird nie dargestellt, nie geprüft  |
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .blatt_kern_shared_data import HELP_BLOCK_TYPE
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .document_type_registry import has_evaluation, has_help_cards, has_points, shows_operator_legend
from .operator_legend_blocks import OPERATORS_BLOCK_TYPE


@dataclass(frozen=True)
class BlockAvailability:
    """Ein Blocktyp, den es nur in Typen mit einer bestimmten Capability gibt.

    Attributes:
        block_type: kanonischer Blockname.
        available: Registry-Abfrage ``document_type -> bool``.
        code: Diagnosecode für Blöcke in Typen ohne Capability.
        message: Meldungstext; ``{block_type}`` wird eingesetzt.
        severity: Schärfe der Meldung.
    """

    block_type: str
    available: Callable[[str | None], bool]
    code: str
    message: str
    severity: str = "warning"


BLOCK_AVAILABILITY: tuple[BlockAvailability, ...] = (
    BlockAvailability(
        HELP_BLOCK_TYPE,
        has_help_cards,
        "BL012",
        "`:::{block_type}` ist in Präsentationen veraltet -- Lernhilfen gibt es nur in "
        "Arbeitsblättern und Klausuren. Der Block wird noch dargestellt; bitte als normalen "
        "Folieninhalt umsetzen oder entfernen.",
    ),
    BlockAvailability(
        "evaluation",
        has_evaluation,
        "EV002",
        "Die Bewertungstabelle gibt es nur in Arbeitsblättern und Klausuren; sie wird hier nicht angezeigt.",
    ),
    BlockAvailability(
        OPERATORS_BLOCK_TYPE,
        shows_operator_legend,
        "OPR007",
        "Die Operatorentabelle gibt es nur in Arbeitsblättern und Klausuren; sie wird hier nicht angezeigt.",
    ),
    BlockAvailability(
        "expectation",
        has_points,
        "BL018",
        "Erwartungen (`:::expectation`) gibt es nur in Arbeitsblättern und Klausuren; der Block wird "
        "hier weder angezeigt noch ausgewertet.",
    ),
)

_AVAILABILITY_BY_BLOCK = {entry.block_type: entry for entry in BLOCK_AVAILABILITY}


def validate_block_availability(blocks, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """Meldet jeden Block, den es im Dokumenttyp nicht gibt (Codes siehe Tabelle oben)."""
    diagnostics = []
    for index, (block_type, options, _content) in enumerate(blocks):
        entry = _AVAILABILITY_BY_BLOCK.get(block_type)
        if entry is None or entry.available(document_type):
            continue
        diagnostics.append(
            BuildDiagnostic(
                code=entry.code,
                message=entry.message.format(block_type=block_type),
                severity=entry.severity,
                block_index=index,
                block_type=block_type,
                region_id=compute_block_region_id(block_type, options),
                anchor=entry.code,
            )
        )
    return diagnostics
