"""Diagnosen zur Operatorentabelle `:::operators:::` (OPR004–OPR008).

Die Operatorentabelle wird nicht mehr automatisch angehängt; diese Prüfung
sorgt dafür, dass verwendete `!!Operatoren!!` trotzdem nicht unerklärt
bleiben. Bereiche und Abdeckung kommen ausschließlich aus
`operator_legend_blocks` (dieselbe Logik wie beim Rendern).

* OPR004 (Warnung): Operatoren verwendet, aber kein `operators`-Block.
* OPR005 (Warnung): Operator-Fundstellen, die kein Block abdeckt (z. B. nach
  der letzten Tabelle mit `scope=previous`). Eine Fundstelle gilt als
  abgedeckt, sobald mindestens ein Block sie abdeckt.
* OPR006 (Fehler): `operators`-Block ohne einen einzigen `!!...!!`-Marker in
  seinem Bereich -- die Tabelle bliebe leer.
* OPR007 (Warnung): `operators`-Block in einem Dokumenttyp ohne
  Operatorentabelle (z. B. Präsentation); er wird nicht dargestellt.
* OPR008 (Warnung): Bereiche überschneiden sich -- dieselbe Fundstelle steht
  in mehreren Tabellen. Erlaubt, aber meist unbeabsichtigt.

Marker, die zu keinem bekannten Operator passen, meldet weiterhin OPR001/OPR003
(`operator_legend.collect_used_operators`); OPR006 zählt deshalb Marker, nicht
erkannte Operatoren, damit eine fehlende Operatoren-Datei nicht zusätzlich
den Export blockiert.
"""

from __future__ import annotations

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .document_type_registry import shows_operator_legend
from .operator_legend_blocks import (
    OPERATORS_BLOCK_TYPE,
    matched_operators_for,
    operator_block_coverages,
    operator_marker_indices,
)


def _diag(blocks, code: str, message: str, index: int, severity: str = "warning") -> BuildDiagnostic:
    block_type, options, _content = blocks[index]
    return BuildDiagnostic(
        code=code, message=message, severity=severity, block_index=index, block_type=block_type,
        region_id=compute_block_region_id(block_type, options), anchor=code,
    )


def _operator_names(blocks, indices, meta) -> str:
    """Kommagetrennte Operatornamen der Fundstellen (Fallback: „Operatoren“)."""
    names = [operator.key for operator in matched_operators_for(blocks, indices, meta)]
    return ", ".join(names) if names else "Operatoren"


def validate_operator_legend(blocks, meta, document_type: str = "worksheet") -> list[BuildDiagnostic]:
    """Prüft Operatorentabellen und ihre Abdeckung (Regeln siehe Moduldocstring)."""
    table_indices = [index for index, (block_type, _o, _c) in enumerate(blocks) if block_type == OPERATORS_BLOCK_TYPE]
    if not shows_operator_legend(document_type):
        return [
            _diag(blocks, "OPR007", "Die Operatorentabelle gibt es nur in Arbeitsblaettern und Klausuren; sie wird hier nicht angezeigt.", index)
            for index in table_indices
        ]
    marker_indices = operator_marker_indices(blocks)
    if not table_indices:
        if not marker_indices:
            return []
        return [_diag(
            blocks, "OPR004",
            f"Operatoren ({_operator_names(blocks, marker_indices, meta)}) ohne Operatorentabelle -- "
            "`:::operators:::` an die gewuenschte Stelle setzen (z. B. ans Ende oder vor `--hm`).",
            marker_indices[0],
        )]
    coverages = operator_block_coverages(blocks, document_type)
    diagnostics = []
    covering = {index: [] for index in marker_indices}
    for coverage in coverages:
        covered_markers = [index for index in coverage.covered if index in covering]
        for index in covered_markers:
            covering[index].append(coverage.block_index)
        if not covered_markers:
            diagnostics.append(_diag(
                blocks, "OPR006",
                f"Operatorentabelle (`scope={coverage.scope}`) ohne Operatoren in ihrem Bereich -- die Tabelle bliebe leer.",
                coverage.block_index, "error",
            ))
    uncovered = [index for index, owners in covering.items() if not owners]
    if uncovered:
        diagnostics.append(_diag(
            blocks, "OPR005",
            f"Operatoren ({_operator_names(blocks, uncovered, meta)}) stehen in keiner Operatorentabelle -- "
            "dahinter eine weitere `:::operators:::` setzen oder bei einer Tabelle `scope=all` verwenden.",
            uncovered[0],
        ))
    diagnostics.extend(_overlap_diagnostics(blocks, covering, meta))
    return diagnostics


def _overlap_diagnostics(blocks, covering: dict[int, list[int]], meta) -> list[BuildDiagnostic]:
    """OPR008 einmal je beteiligtem Block, wenn Fundstellen in mehreren Tabellen stehen."""
    shared: dict[int, list[int]] = {}
    for marker_index, owners in covering.items():
        if len(owners) < 2:
            continue
        for owner in owners:
            shared.setdefault(owner, []).append(marker_index)
    diagnostics = []
    for owner in sorted(shared):
        diagnostics.append(_diag(
            blocks, "OPR008",
            f"Operatorentabelle: {_operator_names(blocks, shared[owner], meta)} stehen auch in einer anderen "
            "Operatorentabelle (Bereiche ueberschneiden sich).",
            owner,
        ))
    return diagnostics
