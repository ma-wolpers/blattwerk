"""Frontmatter-Diagnose `FM011` für die vorbefüllbaren Kopf-Felder `Lerngruppe`/`Datum`.

Die Typregeln selbst liegen in `student_header.py` (eine Quelle für Renderer
und Validator); hier wird nur ein Typfehler als Warnung formuliert. Ein
ungültiger Wert blockiert den Export nicht -- das Feld bleibt im Dokument
einfach leer.
"""

from __future__ import annotations

from .blatt_validator_types import BuildDiagnostic
from .student_header import header_value_problem

FRONTMATTER_REGION_ID = "worksheet:frontmatter"


def validate_header_field(field, raw_value, region_id: str = FRONTMATTER_REGION_ID) -> BuildDiagnostic | None:
    """Liefert `FM011`, wenn `raw_value` für die Feldart `field.kind` nicht erlaubt ist."""
    problem = header_value_problem(field.kind, raw_value)
    if problem is None:
        return None
    return BuildDiagnostic(
        code="FM011",
        message=f"`{field.name}` wird nicht in die Kopfzeile übernommen: {problem}",
        severity="warning",
        region_id=region_id,
        anchor=field.name,
    )
