"""Validiert die Paarung von `:::columns`/`:::nextcol`/`:::endcolumns` über den gesamten Block-Strom.

Arbeitet -- anders als `_collect_block_marker_syntax_diagnostics`
(`blatt_validator_marker_syntax.py`, zeilenbasiert vor dem Parsen) -- auf
der bereits geparsten `blocks`-Liste, weil die erwartete `nextcol`-Anzahl
von der geparsten `cols=N`-Option des öffnenden `columns`-Blocks abhängt.

Zustandsmodell: ein Stack aus offenen `columns`-Rahmen statt eines
einzelnen Zählers, damit verschachtelte `columns`-Blöcke korrekt wieder in
den äußeren Rahmen zurückfallen, sobald der innere (fehlerhafte) Rahmen
geschlossen wird. Jeder Rahmen trägt ein `erroneous`-Flag: sobald ein
Rahmen durch eine Verschachtelung "kontaminiert" wurde (`BL010`), wird für
ihn -- und für den neu geöffneten inneren Rahmen -- die `BL011`-Zählprüfung
beim Schließen unterdrückt, damit ein einzelner Strukturfehler nicht
zusätzlich in einer redundanten Folgewarnung mündet. Ein am Dokument- oder
Folienende (`pagebreak`) unclosed gebliebener Rahmen ist dagegen ein
eigenständiges Problem und wird unabhängig vom `erroneous`-Flag gemeldet.
"""

from __future__ import annotations

from .blatt_validator_types import BuildDiagnostic

_PRESENTATION_SCOPE_RESET_BLOCK_TYPES = frozenset({"pagebreak"})
"""Blocktypen, die einen eigenen Render-Scope für `render_body_with_columns`
eröffnen (siehe `_build_presentation_slides` in `blatt_kern_layout_render.py`:
`pagebreak` leert `current_blocks`, der Renderer schließt offene `columns`
für diese Folie also ohnehin toleriert automatisch). Bewusst OHNE
`framebreak`/`sectionmark`: `framebreak` startet keinen neuen Render-Scope
(`clear_blocks=False`), `sectionmark` beeinflusst den Block-Strom gar nicht."""


class _ColumnsFrame:
    """Ein offener `:::columns`-Rahmen im Validierungs-Stack."""

    __slots__ = ("open_index", "expected_cols", "nextcol_count", "erroneous")

    def __init__(self, open_index, expected_cols, erroneous=False):
        self.open_index = open_index
        self.expected_cols = expected_cols
        self.nextcol_count = 0
        self.erroneous = erroneous


def _resolve_expected_columns(options):
    """Ermittelt die erwartete Spaltenzahl aus `cols=N` (Default 2, geklemmt 2..6).

    Spiegelt exakt die Klemmlogik aus `render_body_with_columns`
    (`blatt_kern_layout_render.py`), damit Validator und Renderer nie
    unterschiedliche Vorstellungen von der gültigen Spaltenzahl haben.
    """
    try:
        raw_cols = int((options or {}).get("cols", 2))
    except (TypeError, ValueError):
        raw_cols = 2
    return max(2, min(raw_cols, 6))


def _emit_unclosed_diagnostics(diagnostics, stack):
    """Meldet `BL009` für jeden am Scope-Ende noch offenen Rahmen und leert den Stack."""
    for frame in stack:
        diagnostics.append(
            BuildDiagnostic(
                code="BL009",
                message=(
                    f"`columns`-Block (Block {frame.open_index}) wird nicht mit "
                    "`endcolumns` geschlossen."
                ),
                severity="error",
                block_index=frame.open_index,
                block_type="columns",
            )
        )
    stack.clear()


def _validate_columns_structure(blocks):
    """Prüft `columns`/`nextcol`/`endcolumns`-Paarung im gesamten Block-Strom (`BL007`-`BL011`)."""
    diagnostics = []
    stack: list[_ColumnsFrame] = []

    for index, (block_type, options, _content) in enumerate(blocks):
        if block_type in _PRESENTATION_SCOPE_RESET_BLOCK_TYPES and stack:
            _emit_unclosed_diagnostics(diagnostics, stack)
            continue

        if block_type == "columns":
            if stack:
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL010",
                        message=(
                            f"Verschachtelter `columns`-Block in Block {index}: "
                            f"der vorherige `columns`-Block (Block {stack[-1].open_index}) "
                            "wurde nicht mit `endcolumns` geschlossen, bevor ein neuer "
                            "`columns`-Block startet."
                        ),
                        severity="error",
                        block_index=index,
                        block_type=block_type,
                    )
                )
                stack[-1].erroneous = True
                stack.append(_ColumnsFrame(index, _resolve_expected_columns(options), erroneous=True))
            else:
                stack.append(_ColumnsFrame(index, _resolve_expected_columns(options)))
            continue

        if block_type == "nextcol":
            if not stack:
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL007",
                        message=(
                            f"`nextcol` in Block {index} außerhalb eines offenen "
                            "`columns`-Blocks. `nextcol` ist nur zwischen `columns` "
                            "und `endcolumns` gültig."
                        ),
                        severity="error",
                        block_index=index,
                        block_type=block_type,
                    )
                )
            else:
                stack[-1].nextcol_count += 1
            continue

        if block_type == "endcolumns":
            if not stack:
                diagnostics.append(
                    BuildDiagnostic(
                        code="BL008",
                        message=f"`endcolumns` in Block {index} ohne passenden offenen `columns`-Block.",
                        severity="error",
                        block_index=index,
                        block_type=block_type,
                    )
                )
                continue

            frame = stack.pop()
            if not frame.erroneous:
                expected_nextcol = frame.expected_cols - 1
                if frame.nextcol_count != expected_nextcol:
                    diagnostics.append(
                        BuildDiagnostic(
                            code="BL011",
                            message=(
                                f"`columns`-Block (Block {frame.open_index}, "
                                f"cols={frame.expected_cols}) erwartet {expected_nextcol} "
                                f"`nextcol`-Marker, gefunden: {frame.nextcol_count}."
                            ),
                            block_index=frame.open_index,
                            block_type="columns",
                        )
                    )
            continue

    _emit_unclosed_diagnostics(diagnostics, stack)
    return diagnostics
