"""Tests für den Frontmatter-Kern (`app/core/frontmatter.py`, Invariante I6)."""

import pytest
import yaml

from app.core.blatt_kern_shared import split_front_matter
from app.core.blatt_validator_value_helpers import _extract_validation_content_and_base_line
from app.core.frontmatter import (
    BOM,
    DuplicateKeyError,
    content_after_frontmatter,
    frontmatter_bounds,
    load_frontmatter_yaml,
    parse_frontmatter,
)


def test_bounds_basic_lf():
    text = "---\nTitel: A\n---\nInhalt\n"
    bounds = frontmatter_bounds(text)
    assert bounds is not None
    assert bounds.body(text) == "Titel: A\n"
    assert text[bounds.end :] == "Inhalt\n"
    assert bounds.open_line_ending == "\n"
    assert bounds.content_start_line == 4


def test_bounds_crlf_and_dot_closer():
    text = "---\r\nTitel: A\r\n...\r\nRest"
    bounds = frontmatter_bounds(text)
    assert bounds.body(text) == "Titel: A\r\n"
    assert bounds.open_line_ending == "\r\n"
    assert text[bounds.end :] == "Rest"


def test_bounds_with_bom_is_recognized():
    text = BOM + "---\nTitel: A\n---\nx"
    bounds = frontmatter_bounds(text)
    assert bounds is not None and bounds.has_bom
    assert bounds.open_line_start == 1


def test_dashes_inside_a_line_do_not_close_frontmatter():
    text = "---\nTitel: a---b\nFach: M\n---\nInhalt"
    meta, rest = parse_frontmatter(text)
    assert meta == {"Titel": "a---b", "Fach": "M"}
    assert rest == "Inhalt"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Kein Frontmatter",
        "---",  # öffnende Zeile ohne Zeilenende
        "---\nTitel: A\n",  # kein Schluss
        "----\nTitel: A\n---\n",  # vier Striche öffnen nicht
        "\n---\nTitel: A\n---\n",  # Leerzeile davor
        "---x\nA: 1\n---\n",
    ],
)
def test_no_frontmatter_cases(text):
    assert frontmatter_bounds(text) is None
    assert parse_frontmatter(text) == ({}, text)


def test_trailing_whitespace_on_fence_lines_allowed():
    text = "---  \nA: 1\n---\t\nB"
    assert parse_frontmatter(text) == ({"A": 1}, "B")


def test_split_front_matter_delegates_to_core():
    text = "---\nTitel: a---b\n---\n  Inhalt  \n"
    assert split_front_matter(text) == ({"Titel": "a---b"}, "Inhalt")


def test_empty_body_gives_empty_meta():
    assert parse_frontmatter("---\n---\nX") == ({}, "X")


def test_runtime_load_keeps_last_duplicate_value():
    assert load_frontmatter_yaml("a: 1\na: 2\n") == {"a": 2}


def test_strict_load_rejects_duplicates_at_any_level():
    with pytest.raises(DuplicateKeyError):
        load_frontmatter_yaml("a: 1\na: 2\n", reject_duplicates=True)
    with pytest.raises(DuplicateKeyError):
        load_frontmatter_yaml("a:\n  b: 1\n  b: 2\n", reject_duplicates=True)


def test_strict_load_duplicates_hidden_by_comment_lines():
    body = "a: 1\n# Kommentar\n\na: 2\n"
    with pytest.raises(DuplicateKeyError):
        load_frontmatter_yaml(body, reject_duplicates=True)


def test_invalid_yaml_still_raises_like_before():
    with pytest.raises(yaml.YAMLError):
        parse_frontmatter("---\na: [1\n---\n")


def test_content_after_frontmatter_line_numbers():
    text = "---\nA: 1\nB: 2\n---\nZeile5\n"
    content, start = content_after_frontmatter(text)
    assert content == "Zeile5\n"
    assert start == 5
    assert content_after_frontmatter("ohne") == ("ohne", 1)


def test_validator_line_base_uses_core_bounds():
    text = "---\nTitel: a---b\n---\n\n:::task\nX\n:::\n"
    content, base_line = _extract_validation_content_and_base_line(text)
    assert content.startswith(":::task")
    assert base_line == 5
