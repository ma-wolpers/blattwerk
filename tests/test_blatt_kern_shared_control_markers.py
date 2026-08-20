"""Cross-Konsistenz-Tests für `CONTROL_MARKERS` (die Blattwerk-Kontrollsyntax-Quelle)."""

import re

import pytest

from app.core.blatt_kern_shared_data import CONTROL_MARKERS
from app.core.blatt_validator_constants import BLOCK_ALLOWED_OPTIONS, KNOWN_BLOCK_TYPES
from app.core.blatt_kern_shared import parse_blocks


def test_control_marker_names_are_unique():
    names = [marker.name for marker in CONTROL_MARKERS]
    assert len(names) == len(set(names))


def test_control_marker_patterns_compile_and_literals_are_strings():
    for marker in CONTROL_MARKERS:
        if marker.kind == "pattern":
            assert isinstance(marker.literal_or_regex, re.Pattern)
        elif marker.kind == "literal":
            assert isinstance(marker.literal_or_regex, str)
        else:
            pytest.fail(f"Unbekannte marker.kind: {marker.kind!r}")


def test_control_marker_block_types_exist_in_known_block_types():
    for marker in CONTROL_MARKERS:
        if marker.block_type is None:
            continue
        assert marker.block_type in KNOWN_BLOCK_TYPES, (
            f"CONTROL_MARKERS-Eintrag {marker.name!r} referenziert unbekannten "
            f"block_type {marker.block_type!r}"
        )


def test_control_marker_option_capture_matches_allowed_block_options():
    for marker in CONTROL_MARKERS:
        if marker.block_type is None or not marker.option_capture:
            continue
        allowed_options = BLOCK_ALLOWED_OPTIONS.get(marker.block_type, set())
        for option_name in marker.option_capture:
            assert option_name in allowed_options, (
                f"CONTROL_MARKERS-Eintrag {marker.name!r} erzeugt Option "
                f"{option_name!r}, die fuer block_type {marker.block_type!r} "
                "nicht in BLOCK_ALLOWED_OPTIONS erlaubt ist"
            )


def test_control_marker_option_capture_count_matches_regex_groups():
    for marker in CONTROL_MARKERS:
        if marker.kind != "pattern":
            continue
        assert marker.literal_or_regex.groups == len(marker.option_capture), (
            f"CONTROL_MARKERS-Eintrag {marker.name!r}: Anzahl Regex-Gruppen "
            f"({marker.literal_or_regex.groups}) passt nicht zu option_capture "
            f"({marker.option_capture!r})"
        )


def test_soft_section_break_has_no_block_type():
    soft_break = next(m for m in CONTROL_MARKERS if m.name == "soft_section_break")
    assert soft_break.block_type is None
    assert soft_break.literal_or_regex == "--"


@pytest.mark.parametrize(
    ("line", "expected_block_type"),
    [
        ("--!", "pagebreak"),
        ("-+", "framebreak"),
        ("--hf", "slidechromeoff"),
        ("--# Mein Abschnitt", "sectionmark"),
        ("-=0.5cm", "vspacer"),
    ],
)
def test_parse_blocks_recognizes_each_control_marker(line, expected_block_type):
    blocks = parse_blocks(f"Text davor\n{line}\nText danach\n")
    marker_blocks = [block for block in blocks if block[0] == expected_block_type]
    assert marker_blocks, f"Kein {expected_block_type}-Block fuer Zeile {line!r} erkannt"


def test_parse_blocks_soft_section_break_produces_html_comment_marker():
    blocks = parse_blocks("Erster Absatz\n--\nZweiter Absatz\n")
    raw_blocks = [content for block_type, _, content in blocks if block_type == "raw"]
    assert any("<!--BLATTWERK_SECTION_BREAK-->" in content for content in raw_blocks)


def test_parse_blocks_horizontal_rule_is_not_a_control_marker():
    blocks = parse_blocks("Erster Absatz\n---\nZweiter Absatz\n")
    # `---` bleibt gewoehnliches Markdown im raw-Buffer, kein eigener Block-Typ.
    assert all(block_type != "sectionmark" for block_type, _, _ in blocks)
    raw_blocks = [content for block_type, _, content in blocks if block_type == "raw"]
    assert any("---" in content for content in raw_blocks)
