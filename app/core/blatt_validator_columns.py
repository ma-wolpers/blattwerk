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

from dataclasses import dataclass

from .blatt_validator_region import compute_block_region_id
from .blatt_validator_types import BuildDiagnostic
from .columns_count import resolve_columns_count

COLUMNS_SCOPE_RESET_BLOCK_TYPES = frozenset({"pagebreak"})
"""Blocktypen, die einen eigenen Render-Scope für `render_body_with_columns`
eröffnen (siehe `_build_presentation_slides` in `blatt_kern_layout_render.py`:
`pagebreak` leert `current_blocks`, der Renderer schließt offene `columns`
für diese Folie also ohnehin toleriert automatisch). Bewusst OHNE
`framebreak`/`sectionmark`: `framebreak` startet keinen neuen Render-Scope
(`clear_blocks=False`), `sectionmark` beeinflusst den Block-Strom gar nicht."""


@dataclass
class ColumnsScope:
    """Ein Spaltenbereich im Block-Strom, wie ihn die Zustandsmaschine unten sieht.

    Attributes:
        open_index: Index des `columns`-Blocks.
        close_index: Index des Blocks, der den Bereich beendet (`endcolumns`
            oder ein Scope-Ende wie `pagebreak`), `None` bis zum Ende.
    """

    open_index: int
    close_index: int | None = None


class _ColumnsFrame:
    """Ein offener `:::columns`-Rahmen im Validierungs-Stack."""

    __slots__ = ("open_index", "expected_cols", "nextcol_count", "erroneous", "options", "scope")

    def __init__(self, open_index, expected_cols, erroneous=False, options=None):
        self.open_index = open_index
        self.expected_cols = expected_cols
        self.nextcol_count = 0
        self.erroneous = erroneous
        self.options = options or {}
        self.scope = ColumnsScope(open_index)


def _emit_unclosed_diagnostics(diagnostics, stack, close_index=None):
    """Meldet `BL009` für jeden am Scope-Ende noch offenen Rahmen und leert den Stack.

    `close_index` ist der Block, der den Scope beendet (`None` = Dokumentende).
    """
    for frame in stack:
        frame.scope.close_index = close_index
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
    return analyze_columns_structure(blocks)[0]


def analyze_columns_structure(blocks):
    """Die eine Zustandsmaschine für Spaltenbereiche: Diagnosen plus erkannte Bereiche.

    Args:
        blocks: Folge von `(block_type, options, content)` wie aus `parse_blocks`.
            Das Block-Einfügen im Editor übergibt dieselbe Form, gebaut aus den
            Köpfen und Markerzeilen von `scan_block_lines`.

    Returns:
        `(diagnostics, scopes)`; `scopes` in Reihenfolge ihres Öffnens.
    """
    diagnostics = []
    scopes: list[ColumnsScope] = []
    stack: list[_ColumnsFrame] = []

    for index, (block_type, options, _content) in enumerate(blocks):
        if block_type in COLUMNS_SCOPE_RESET_BLOCK_TYPES and stack:
            _emit_unclosed_diagnostics(diagnostics, stack, close_index=index)
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
                stack.append(_ColumnsFrame(index, resolve_columns_count(options), erroneous=True, options=options))
            else:
                stack.append(_ColumnsFrame(index, resolve_columns_count(options), options=options))
            scopes.append(stack[-1].scope)
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
            frame.scope.close_index = index
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
                            region_id=compute_block_region_id("columns", frame.options),
                            anchor="",
                        )
                    )
            continue

    _emit_unclosed_diagnostics(diagnostics, stack)
    return diagnostics, scopes
