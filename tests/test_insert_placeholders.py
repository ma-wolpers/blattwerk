"""`resolve_insert_placeholders`: die eine Platzhalter-Konvention für Vorlagen und Vervollständigung."""

from __future__ import annotations

import pytest

from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS, IMAGE_INSERT_SNIPPET
from app.core.insert_placeholders import CURSOR_PLACEHOLDER, resolve_insert_placeholders, strip_insert_placeholders


@pytest.mark.parametrize("raw, expected", [
    (":::info\n[[CURSOR]]Text\n:::\n", (":::info\nText\n:::\n", 8)),
    ("rows=", ("rows=", 5)),                                          # ohne Platzhalter: ans Ende
    ("a [[2:zwei]] b [[1:eins]]", ("a zwei b eins", 9)),               # kleinstes n gewinnt
    ("[[1:x]] [[CURSOR]]", ("x [[CURSOR]]", 0)),                       # nummerierte haben Vorrang
    ("[[CURSOR]]a[[CURSOR]]", ("a[[CURSOR]]", 0)),                     # nur das erste zählt
])
def test_resolve_insert_placeholders(raw, expected):
    assert resolve_insert_placeholders(raw) == expected


def test_every_template_has_exactly_one_cursor_placeholder():
    for name, snippet in {**BLOCK_INSERT_SNIPPETS, "image": IMAGE_INSERT_SNIPPET}.items():
        assert snippet.count(CURSOR_PLACEHOLDER) == 1, name
        assert "\x01" not in snippet, name
        assert CURSOR_PLACEHOLDER not in strip_insert_placeholders(snippet), name
