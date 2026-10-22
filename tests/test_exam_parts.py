"""Klausurteile-Modell `ExamPartLayout` (Wunschliste Schritt 6a): Resolver, Invarianten, Summenquelle."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.core.blatt_kern_shared import parse_blocks
from app.core.exam_parts import (
    PART_KIND_AID,
    PART_KIND_CHOICE,
    ChoiceGroup,
    ExamPart,
    ExamPartLayout,
    exam_max_points,
    resolve_exam_parts,
)

TASK = ":::task points=1 afb=1\nX\n:::\n"


def _part(order, part_id, start, end, marker, kind=PART_KIND_AID, group=None):
    return ExamPart(order, part_id, kind, part_id, part_id, start, end, marker, group)


def _choice_layout():
    """Teil A | Wahlteile W1, W2, W3 (k=2) -- gültige Referenz für die Negativtests."""
    parts = (
        _part(0, "A", 0, 3, None),
        _part(1, "W1", 3, 5, 3, PART_KIND_CHOICE, "G"),
        _part(2, "W2", 5, 7, 5, PART_KIND_CHOICE, "G"),
        _part(3, "W3", 7, 9, 7, PART_KIND_CHOICE, "G"),
    )
    return parts, (ChoiceGroup("G", 2, ("W1", "W2", "W3")),)


def test_resolver_covers_document_without_gaps_and_cover_belongs_to_part_a():
    blocks = parse_blocks("Deckblatt\n\n--hm\n" + TASK + "--hm\n" + TASK)
    layout = resolve_exam_parts(blocks, "exam").layout
    cover, split = [i for i, (bt, _o, _c) in enumerate(blocks) if bt == "aidsplit"]
    assert [(p.part_id, p.start_block, p.end_block, p.marker_block) for p in layout.parts] == [
        ("A", 0, split, cover),
        ("B", split, len(blocks), split),
    ]
    assert layout.part_for_block(0).part_id == "A" and layout.cover_end == cover


def test_resolver_reports_problems_instead_of_layout():
    resolution = resolve_exam_parts(parse_blocks("--hm\n" + TASK), "exam")
    assert resolution.layout is None and [p.code for p in resolution.problems] == ["KL004"]
    outside = resolve_exam_parts(parse_blocks(TASK + "--hm\n" + TASK), "worksheet")
    assert outside.layout is None and [p.code for p in outside.problems] == ["KL002"]
    assert resolve_exam_parts(parse_blocks(TASK), "exam") == resolve_exam_parts(parse_blocks(TASK), "exam")


def test_valid_choice_layout_is_accepted():
    parts, groups = _choice_layout()
    assert ExamPartLayout(parts, groups).part_for_block(6).part_id == "W2"


def _with_part(index, **changes):
    parts, groups = _choice_layout()
    parts = list(parts)
    parts[index] = replace(parts[index], **changes)
    return tuple(parts), groups


@pytest.mark.parametrize(
    ("parts_groups", "message"),
    [
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 2, ("W1", "W2", "WX")),)), "unbekannter Teil"),
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 1, ("W1", "W2")), ChoiceGroup("H", 1, ("W2", "W3")))), "mehrfach"),
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 2, ("W1", "W1", "W2")),)), "mehrfach"),
        (lambda: _with_part(2, group_id="H"), "passt nicht"),
        (lambda: _with_part(0, group_id="G"), "keiner Wahlgruppe"),
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 2, ("W1", "W2", "W3")), ChoiceGroup("E", 1, ()))), "leer"),
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 1, ("W1", "W2")),)), "passt nicht"),
        (lambda: _with_part(2, part_id="W1"), "part_id doppelt"),
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 3, ("W1", "W2", "W3")),)), "k=3"),
        (lambda: (_choice_layout()[0], (ChoiceGroup("G", 2, ("W1", "W2", "W3")), ChoiceGroup("G", 1, ("A",)))), "group_id doppelt"),
        (lambda: _with_part(2, start_block=4), "lückenlos"),
        (lambda: _with_part(2, order=5), "order"),
        (lambda: _with_part(2, marker_block=None), "ohne Trenner"),
        (lambda: _with_part(1, kind="extra"), "Teilart"),
    ],
)
def test_inconsistent_layouts_raise_value_error(parts_groups, message):
    parts, groups = parts_groups()
    with pytest.raises(ValueError, match=message):
        ExamPartLayout(parts, groups)


def test_non_contiguous_group_raises():
    parts = (
        _part(0, "W1", 0, 2, None, PART_KIND_CHOICE, "G"),
        _part(1, "A", 2, 4, 2),
        _part(2, "W2", 4, 6, 4, PART_KIND_CHOICE, "G"),
    )
    with pytest.raises(ValueError, match="nicht zusammenhängend"):
        ExamPartLayout(parts, (ChoiceGroup("G", 1, ("W1", "W2")),))


def test_exam_max_points_counts_k_best_choice_parts():
    parts, groups = _choice_layout()
    layout = ExamPartLayout(parts, groups)
    points = {"A": Decimal(10), "W1": Decimal(5), "W2": Decimal(5), "W3": Decimal(5)}
    assert exam_max_points(layout, points) == Decimal(20)
    assert exam_max_points(layout, {**points, "W3": None}) is None
