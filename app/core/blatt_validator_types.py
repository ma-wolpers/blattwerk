"""Gemeinsame Datentypen für den Blattwerk-Validator.

Bewusst als eigenes, sehr kleines Modul ausgelagert: `BuildDiagnostic` wird
von praktisch jedem Validator-Submodul (Konstruktion neuer Diagnosen) und
gleichzeitig vom öffentlichen Einstiegspunkt `blatt_validator.py` benötigt.
Läge die Klasse in `blatt_validator.py` selbst, würde jeder Submodul-Import
von dort einen Zirkelimport erzeugen, sobald `blatt_validator.py` umgekehrt
Funktionen aus denselben Submodulen importiert. Externer Code importiert
`BuildDiagnostic`/`InspectedDocument` weiterhin wie bisher aus
`app.core.blatt_validator` (dort re-exportiert) — dieser Modulpfad ist ein
reines internes Implementierungsdetail.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuildDiagnostic:
    """Nicht-blockierende oder blockierende Diagnose aus Parsing/Validierung."""

    code: str
    message: str
    severity: str = "warning"
    block_index: int | None = None
    block_type: str | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class InspectedDocument:
    """Geparstes Markdown-Dokument plus zugehörige Diagnosen."""

    meta: dict
    blocks: list[tuple[str, dict, str]]
    diagnostics: list[BuildDiagnostic]
