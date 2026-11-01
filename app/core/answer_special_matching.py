"""Matching answer renderer and weight estimation."""

from __future__ import annotations

from .answer_matching_parse import (  # noqa: F401 -- auch für Tests
    _normalize_matching_layout,
    _parse_matching_pairs,
    _parse_matching_bool_option,
    _normalize_matching_height_mode,
    _normalize_matching_align,
    _normalize_lane_align,
    _parse_matching_content,
    parse_matching_sources,
)

import re
from html import escape

import yaml

from .answer_special_shared import (
    _as_text_list,
    _new_markdown_converter,
    _normalize_keyword,
    convert_markdown_with_math,
    _parse_option_list,
)


def _estimate_uniform_item_height(first_items, second_items):
    """Schaetzt eine uniforme Item-Hoehe auf Basis des laengsten Eintrags."""
    all_items = [str(item or "") for item in [*first_items, *second_items]]
    if not all_items:
        return "0.8cm"

    longest = max(len(item.strip()) for item in all_items)
    longest = max(1, longest)
    estimated_lines = max(1, (longest + 31) // 32)
    estimated_cm = min(3.4, max(0.8, 0.46 + (estimated_lines * 0.34)))
    return f"{estimated_cm:.2f}cm"


def _slot_center_percent(slot_index_1based, slots):
    """Liefert die prozentuale Mittelpunktposition eines konkreten Slots."""
    if slots <= 0:
        return 50.0

    center_slot = max(0.5, min(float(slots) - 0.5, slot_index_1based - 0.5))
    return (center_slot / slots) * 100.0


def _center_out_indices(total):
    """Liefert Indexreihenfolge von der Mitte nach außen."""
    if total <= 0:
        return []

    center = (total - 1) / 2.0
    return sorted(range(total), key=lambda idx: (abs(idx - center), idx))


def _distributed_slot_indexes(total_slots, item_count, lane_align):
    """Verteilt Item-Slots deterministisch über den gemeinsamen Slotraum."""
    if total_slots <= 0 or item_count <= 0:
        return []
    if item_count >= total_slots:
        return list(range(1, total_slots + 1))
    if item_count == 1:
        if lane_align == "start":
            return [1]
        if lane_align == "end":
            return [total_slots]
        return [max(1, ((total_slots + 1) // 2))]

    if lane_align == "start":
        return list(range(1, item_count + 1))
    if lane_align == "end":
        offset = total_slots - item_count
        return [offset + value for value in range(1, item_count + 1)]

    extra_slots = total_slots - item_count
    intervals = item_count + 1
    gap_base = extra_slots // intervals
    gap_remainder = extra_slots % intervals
    gaps = [gap_base] * intervals

    for gap_index in _center_out_indices(intervals)[:gap_remainder]:
        gaps[gap_index] += 1

    positions = []
    current_slot = 1 + gaps[0]
    for item_index in range(item_count):
        positions.append(current_slot)
        current_slot += 1 + gaps[item_index + 1]

    return positions


def _render_matching_item(md, raw_item):
    """Rendert einen einzelnen Matching-Eintrag als HTML."""
    return convert_markdown_with_math(md, raw_item or "").strip()


def _render_matching_horizontal_svg(
    pair_indexes,
    slots,
    left_slots,
    right_slots,
    line_class="matching-line",
):
    """Erzeugt SVG-Verbindungslinien für horizontales Matching."""
    if slots <= 0 or not pair_indexes:
        return ""

    lines = []
    for left_index, right_index in pair_indexes:
        if left_index > len(left_slots) or right_index > len(right_slots):
            continue
        y_left = _slot_center_percent(left_slots[left_index - 1], slots)
        y_right = _slot_center_percent(right_slots[right_index - 1], slots)
        lines.append(
            f"<line x1='2' y1='{y_left:.2f}%' x2='98' y2='{y_right:.2f}%' class='{escape(line_class)}'></line>"
        )

    return (
        "<svg class='matching-svg' viewBox='0 0 100 100' preserveAspectRatio='none' "
        "aria-hidden='true'>" + "".join(lines) + "</svg>"
    )


def _render_matching_vertical_svg(
    pair_indexes,
    slots,
    top_slots,
    bottom_slots,
    line_class="matching-line",
):
    """Erzeugt SVG-Verbindungslinien für vertikales Matching."""
    if slots <= 0 or not pair_indexes:
        return ""

    lines = []
    for top_index, bottom_index in pair_indexes:
        if top_index > len(top_slots) or bottom_index > len(bottom_slots):
            continue
        x_top = _slot_center_percent(top_slots[top_index - 1], slots)
        x_bottom = _slot_center_percent(bottom_slots[bottom_index - 1], slots)
        lines.append(
            f"<line x1='{x_top:.2f}%' y1='2' x2='{x_bottom:.2f}%' y2='98' class='{escape(line_class)}'></line>"
        )

    return (
        "<svg class='matching-svg' viewBox='0 0 100 100' preserveAspectRatio='none' "
        "aria-hidden='true'>" + "".join(lines) + "</svg>"
    )


def render_matching_answer(options, content, include_solutions):
    """Rendert das Matching-Feld inklusive optionaler Lösungs-Linien."""
    (
        layout,
        first_items,
        second_items,
        pair_indexes,
        worksheet_pair_indexes,
        show_guides,
        height_mode,
        align,
        lane_align,
    ) = _parse_matching_content(options, content)
    if not first_items or not second_items:
        return ""

    md = _new_markdown_converter()
    slot_count = max(len(first_items), len(second_items), 1)
    first_slots = _distributed_slot_indexes(slot_count, len(first_items), lane_align)
    second_slots = _distributed_slot_indexes(slot_count, len(second_items), lane_align)
    uniform_height = _estimate_uniform_item_height(first_items, second_items)
    answer_classes = [
        "answer",
        "matching-answer",
        f"matching-{layout}",
        f"matching-height-{height_mode}",
        f"matching-align-{align}",
        f"matching-lane-align-{lane_align}",
    ]
    if not show_guides:
        answer_classes.append("matching-no-guides")

    style_chunks = [f"--matching-slots:{slot_count}"]
    if height_mode == "uniform":
        style_chunks.append(f"--matching-item-height:{uniform_height}")

    answer_style = ";".join(style_chunks)

    if layout == "vertical":
        first_lane = []
        second_lane = []

        for item, slot in zip(first_items, first_slots):
            rendered = _render_matching_item(md, item)
            first_lane.append(
                f"<div class='matching-item' style='grid-column:{slot}'>{rendered}</div>"
            )

        for item, slot in zip(second_items, second_slots):
            rendered = _render_matching_item(md, item)
            second_lane.append(
                f"<div class='matching-item' style='grid-column:{slot}'>{rendered}</div>"
            )

        if show_guides:
            first_slot_set = set(first_slots)
            second_slot_set = set(second_slots)
            for slot in range(1, slot_count + 1):
                if slot not in first_slot_set:
                    first_lane.append(
                        f"<div class='matching-item matching-empty' style='grid-column:{slot}'></div>"
                    )
                if slot not in second_slot_set:
                    second_lane.append(
                        f"<div class='matching-item matching-empty' style='grid-column:{slot}'></div>"
                    )

        if include_solutions:
            svg_html = _render_matching_vertical_svg(
                pair_indexes,
                slot_count,
                first_slots,
                second_slots,
                line_class="matching-line",
            )
        else:
            svg_html = _render_matching_vertical_svg(
                worksheet_pair_indexes,
                slot_count,
                first_slots,
                second_slots,
                line_class="matching-line matching-line-worksheet",
            )
        return (
            f"<div class='{' '.join(answer_classes)}' style='{answer_style}'>"
            f"<div class='matching-lane matching-first'>{''.join(first_lane)}</div>"
            f"<div class='matching-canvas'>{svg_html}</div>"
            f"<div class='matching-lane matching-second'>{''.join(second_lane)}</div>"
            "</div>"
        )

    first_lane = []
    second_lane = []
    for item, slot in zip(first_items, first_slots):
        rendered = _render_matching_item(md, item)
        first_lane.append(
            f"<div class='matching-item' style='grid-row:{slot}'>{rendered}</div>"
        )
    for item, slot in zip(second_items, second_slots):
        rendered = _render_matching_item(md, item)
        second_lane.append(
            f"<div class='matching-item' style='grid-row:{slot}'>{rendered}</div>"
        )

    if show_guides:
        first_slot_set = set(first_slots)
        second_slot_set = set(second_slots)
        for slot in range(1, slot_count + 1):
            if slot not in first_slot_set:
                first_lane.append(
                    f"<div class='matching-item matching-empty' style='grid-row:{slot}'></div>"
                )
            if slot not in second_slot_set:
                second_lane.append(
                    f"<div class='matching-item matching-empty' style='grid-row:{slot}'></div>"
                )

    if include_solutions:
        svg_html = _render_matching_horizontal_svg(
            pair_indexes,
            slot_count,
            first_slots,
            second_slots,
            line_class="matching-line",
        )
    else:
        svg_html = _render_matching_horizontal_svg(
            worksheet_pair_indexes,
            slot_count,
            first_slots,
            second_slots,
            line_class="matching-line matching-line-worksheet",
        )

    return (
        f"<div class='{' '.join(answer_classes)}' style='{answer_style}'>"
        f"<div class='matching-lane matching-first'>{''.join(first_lane)}</div>"
        f"<div class='matching-canvas'>{svg_html}</div>"
        f"<div class='matching-lane matching-second'>{''.join(second_lane)}</div>"
        "</div>"
    )


def estimate_matching_weight(text_length, include_solutions):
    """Schätzt den Layout-Bedarf eines Matching-Blocks für Spaltenlogik."""
    if include_solutions:
        return max(2.2, text_length / 160.0)
    return max(1.8, text_length / 190.0)
