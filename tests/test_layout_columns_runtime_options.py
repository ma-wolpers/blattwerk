"""Spaltenblöcke bekommen dieselben Laufzeitoptionen -- auch ohne `:::endcolumns`.

Regression: Ein nicht geschlossener Spaltenbereich wurde am Dokumentende ohne
Druckhöhe und Rechen-Cache gerendert, ein geschlossener mit beiden.
"""

from __future__ import annotations

import pytest

from app.core import blatt_kern_layout_columns as columns
from app.core.blatt_kern_shared import parse_blocks

CLOSED = ":::columns cols=2 :::\n:::task\nA\n:::\n:::nextcol :::\n:::task\nB\n:::\n:::endcolumns :::\n"
UNCLOSED = ":::columns cols=2 :::\n:::task\nA\n:::\n:::nextcol :::\n:::task\nB\n:::\n"


@pytest.mark.parametrize("body", [CLOSED, UNCLOSED], ids=["closed", "unclosed"])
def test_column_blocks_get_all_runtime_options(monkeypatch, body):
    """Druckbreite, Druckhöhe, Cache und Sprache erreichen jeden Spaltenblock."""
    seen = []

    def _record(block_type, options, content, **_kwargs):
        """Merkt sich die Optionen jedes gerenderten Blocks."""
        seen.append(options)
        return "<div></div>"

    monkeypatch.setattr(columns, "render_block", _record)
    cache = object()
    columns.render_body_with_columns(
        parse_blocks(body),
        include_solutions=False,
        printable_width_cm=17.0,
        printable_height_cm=25.0,
        cache=cache,
        language="pt-br",
    )

    assert len(seen) == 2
    for options in seen:
        assert options["_printable_width_cm"] == 17.0
        assert options["_printable_height_cm"] == 25.0
        assert options["_computation_cache"] is cache
        assert options["_language"] == "pt-br"


THREE_WITH_EMPTY = ":::columns cols=3 :::\n:::task\nA\n:::\n:::nextcol :::\n:::nextcol :::\n:::task\nB\n:::\n"


@pytest.mark.parametrize("closing", ["", ":::endcolumns :::\n"], ids=["unclosed", "closed"])
def test_unclosed_columns_are_normalized_like_closed_ones(closing):
    """Leere Mittelspalte entfällt in beiden Fällen: identisches HTML mit und ohne `endcolumns`."""
    html = columns.render_body_with_columns(parse_blocks(THREE_WITH_EMPTY + closing), include_solutions=False)
    assert html.count("<div class='column'>") == 2
    closed = columns.render_body_with_columns(
        parse_blocks(THREE_WITH_EMPTY + ":::endcolumns :::\n"), include_solutions=False
    )
    assert html == closed
