"""Diagnose AN020: `widths=` einer `:::table` passt nicht zur Spaltenzahl.

Rechnet Spaltenzahl und Breitenregel mit denselben Funktionen wie der Renderer
(`answer_table_layout.resolve_table_layout`, `widths_count_mismatch`), damit die
Warnung genau dann erscheint, wenn Breiten tatsaechlich ignoriert oder abgeschnitten
werden.
"""

from __future__ import annotations

from .answer_table_layout import resolve_table_layout, widths_count_mismatch
from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic


def validate_tables(blocks) -> list[BuildDiagnostic]:
    """AN020 (Warnung) fuer jede `table`, deren `widths`-Anzahl nicht passt.

    Erlaubt sind ``cols`` Werte (Datenspalten) und - mit `row_headers` - ``cols + 1``
    Werte (erster Wert = Kopfspalte).
    """
    diagnostics = []
    for index, (block_type, options, content) in enumerate(blocks):
        if block_type != "table" or not options.get("widths"):
            continue
        layout = resolve_table_layout(options, content)
        mismatch = widths_count_mismatch(options.get("widths"), layout.cols, layout.has_row_header_column)
        if mismatch is None:
            continue
        given, allowed = mismatch
        allowed_text = " oder ".join(str(value) for value in allowed)
        diagnostics.append(BuildDiagnostic(
            code="AN020",
            message=(
                f"Tabelle: `widths` hat {given} Werte, die Tabelle hat aber {layout.cols} Datenspalten "
                f"-- erwartet werden {allowed_text} Werte"
                + (" (bei `row_headers` gilt ein zusätzlicher erster Wert für die Kopfspalte)" if layout.has_row_header_column else "")
                + ". Überzählige Werte werden ignoriert, zu wenige heben `widths` ganz auf."
            ),
            block_index=index,
            block_type=block_type,
            region_id=compute_block_region_id(block_type, options),
            anchor="AN020",
        ))
    return diagnostics
