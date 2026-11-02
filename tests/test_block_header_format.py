"""`format_options`/`format_block_header`: das Gegenstück zu `parse_options`."""

from __future__ import annotations

import pytest

from app.core.blatt_kern_shared_parsing import (
    _BLOCK_START_PATTERN,
    _SELF_CLOSING_BLOCK_PATTERN,
    format_block_header,
    format_options,
    parse_options,
)


@pytest.mark.parametrize("options", [
    {"points": "3", "type": "note"},
    {"widths": "1 1", "column_headers": "A|B|C"},
    {"title": 'Er sagt "Hallo"', "path": "C:\\Ordner\\bild.png"},
    {"w": "80%", "empty": ""},
])
def test_format_options_round_trips_through_parse_options(options):
    assert parse_options(format_options(options)) == options


def test_simple_values_stay_unquoted_and_order_is_kept():
    assert format_options({"cols": 2, "widths": "1 1"}) == 'cols=2 widths="1 1"'


def test_block_header_matches_the_parser_patterns():
    open_header = format_block_header("task", {"points": 2})
    closed_header = format_block_header("nextcol", self_closing=True)
    assert open_header == ":::task points=2"
    assert closed_header == ":::nextcol :::"
    assert _BLOCK_START_PATTERN.match(open_header).group(1) == "task"
    assert _SELF_CLOSING_BLOCK_PATTERN.match(closed_header).group(1) == "nextcol"
