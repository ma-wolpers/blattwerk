"""Spaltenzahl (`columns_count.py`) und die Spaltenbereiche aus `analyze_columns_structure`."""

from __future__ import annotations

import pytest

from app.core.blatt_validator_columns import analyze_columns_structure, index_in_columns_scope
from app.core.columns_count import COLUMNS_DEFAULT, COLUMNS_MAX, COLUMNS_MIN, resolve_columns_count


@pytest.mark.parametrize("options, expected", [
    ({}, COLUMNS_DEFAULT),
    ({"cols": "3"}, 3),
    ({"cols": "1"}, COLUMNS_MIN),
    ({"cols": "99"}, COLUMNS_MAX),
    ({"cols": "drei"}, COLUMNS_DEFAULT),
    (None, COLUMNS_DEFAULT),
])
def test_resolve_columns_count(options, expected):
    assert resolve_columns_count(options) == expected


def _blocks(*types):
    return [(block_type, {}, "") for block_type in types]


def test_scopes_end_at_endcolumns_pagebreak_or_document_end():
    _diagnostics, scopes = analyze_columns_structure(
        _blocks("raw", "columns", "nextcol", "endcolumns", "columns", "pagebreak", "columns", "raw")
    )
    assert [(scope.open_index, scope.close_index) for scope in scopes] == [(1, 3), (4, 5), (6, None)]


def test_nested_columns_close_both_scopes_at_document_end():
    diagnostics, scopes = analyze_columns_structure(_blocks("columns", "columns"))
    assert [(scope.open_index, scope.close_index) for scope in scopes] == [(0, None), (1, None)]
    assert "BL010" in {d.code for d in diagnostics}


def test_index_in_columns_scope_ends_at_pagebreak():
    blocks = _blocks("columns", "task", "pagebreak", "aidsplit", "columns", "nextcol", "endcolumns", "task")
    assert index_in_columns_scope(blocks, 1)
    assert not index_in_columns_scope(blocks, 3)  # früher (Zählung columns/endcolumns) fälschlich "in Spalten"
    assert index_in_columns_scope(blocks, 5)
    assert not index_in_columns_scope(blocks, 7)
