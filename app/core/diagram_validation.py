"""Gemeinsamer Ablauf der Diagramm-Validierung: Blockinhalt parsen, Fehler melden, fachlich prüfen.

Vorschau und Validator nutzen denselben Parser; hier entsteht aus dessen
`ParseIssue`s die Diagnose mit Zeilenangabe. Die fachlichen Prüfungen liegen
beim jeweiligen Block (`check(collect, options, model)`).
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic


class DiagnosticCollector:
    """Baut `BuildDiagnostic`s mit gemeinsamem Block-Kontext."""

    def __init__(self, index, block_type, options, title):
        """Merkt sich Blockindex, Blocktyp, Region und Meldungspräfix für alle Diagnosen."""
        self.index = index
        self.block_type = block_type
        self.title = title
        self.region_id = compute_block_region_id(block_type, options or {})
        self.diagnostics: list[BuildDiagnostic] = []

    def add(self, code: str, message: str, severity: str = "warning", anchor: str = "") -> None:
        """Hängt eine Diagnose an; `anchor` unterscheidet Vorkommen fürs Abhaken."""
        self.diagnostics.append(
            BuildDiagnostic(
                code=code,
                message=f"{self.title}: {message}",
                severity=severity,
                block_index=self.index,
                block_type=self.block_type,
                region_id=self.region_id,
                anchor=anchor or code,
            )
        )


def validate_block(index, block_type, options, content, *, title, parse, check, empty_code) -> list[BuildDiagnostic]:
    """Prüft einen Diagrammblock vollständig.

    Args:
        index: Blockindex im Dokument (für Region/Abhaken).
        block_type: Blockname.
        options: Blockoptionen.
        content: Rohinhalt des Blocks (Einrückung erhalten).
        title: Anzeigename, steht vor jeder Meldung.
        parse: `parse(content) -> (modell, issues)`; ein leeres Modell ist falsy.
        check: `check(collect, options, modell)` oder `None`; läuft nur bei
            nicht leerem Modell.
        empty_code: Warnungscode für einen leeren Block.

    Returns:
        Liste der Diagnosen; Zeilenangaben in Meldungen sind 1-basiert
        relativ zum Blockinhalt.
    """
    collect = DiagnosticCollector(index, block_type, options, title)
    model, issues = parse(content)
    for issue in issues:
        collect.add(issue.code, f"Zeile {issue.line} im Block: {issue.message}", issue.severity, f"{issue.code}:{issue.line}")
    if not model:
        collect.add(empty_code, "Der Block ist leer.")
        return collect.diagnostics
    if check is not None:
        check(collect, options or {}, model)
    return collect.diagnostics
