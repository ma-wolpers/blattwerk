"""Matching answer renderer and weight estimation."""

from __future__ import annotations

import re
from html import escape

import yaml

from .answer_special_shared import (
    _as_text_list,
    _new_markdown_converter,
    _normalize_keyword,
    normalize_markdown,
    _parse_option_list,
)


def _normalize_matching_layout(options, payload):
    """Bestimmt die Matching-Ausrichtung aus Optionen und Inhalt."""
    layout_raw = _normalize_keyword(
        options.get("layout") or options.get("orientation"), default=""
    )
    if layout_raw in {"vertical", "topbottom", "tb", "obenunten", "oben_unten"}:
        return "vertical"
    if layout_raw in {"horizontal", "leftright", "lr", "linksrechts", "links_rechts"}:
        return "horizontal"

    if payload.get("top") or payload.get("bottom"):
        return "vertical"

    return "horizontal"


def _parse_matching_pairs(raw_pairs):
    """Parst Zuordnungspaare im Format Dict oder `1->2`-Text."""
    pairs = []

    for entry in raw_pairs or []:
        if isinstance(entry, dict):
            left_raw = entry.get("from", entry.get("left", entry.get("a")))
            right_raw = entry.get("to", entry.get("right", entry.get("b")))
            try:
                left_index = int(left_raw)
                right_index = int(right_raw)
            except (TypeError, ValueError):
                continue
            pairs.append((left_index, right_index))
            continue

        text = str(entry).strip()
        if not text:
            continue

        match = re.match(r"^(\d+)\s*(?:-|:|=|>|->|=>)\s*(\d+)$", text)
        if not match:
            continue

        pairs.append((int(match.group(1)), int(match.group(2))))

    return pairs


def _parse_matching_bool_option(raw_value, default):
    """Parst boolsche Optionen tolerant aus Strings und Zahlen."""
    if raw_value is None:
        return default

    if isinstance(raw_value, bool):
        return raw_value

    text = _normalize_keyword(str(raw_value), default="")
    if text in {"1", "true", "yes", "ja", "on"}:
        return True
    if text in {"0", "false", "no", "nein", "off"}:
        return False
    return default


def _normalize_matching_height_mode(options, payload):
    """Bestimmt den Hoehenmodus der Matching-Items."""
    raw_mode = _normalize_keyword(
        payload.get("height_mode") or options.get("height_mode"), default="content"
    )
    if raw_mode in {"uniform", "equal", "gleich"}:
        return "uniform"
    return "content"


def _normalize_matching_align(options, payload):
    """Bestimmt die Inhaltsausrichtung in Matching-Items."""
    raw_align = _normalize_keyword(
        payload.get("align") or options.get("align"), default="center"
    )
    if raw_align in {"center", "zentriert", "mittel"}:
        return "center"
    return "center"


def _normalize_lane_align(options, payload):
    """Bestimmt die gegenseitige Lane-Ausrichtung."""
    raw_align = _normalize_keyword(
        payload.get("lane_align") or options.get("lane_align"), default="center"
    )
    if raw_align in {"start", "top", "oben"}:
        return "start"
    if raw_align in {"end", "bottom", "unten"}:
        return "end"
    return "center"


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


def _parse_matching_content(options, content):
    """Extrahiert Layout, Item-Listen und gültige Paar-Indizes aus Blockdaten."""
    payload = {}

    try:
        parsed = yaml.safe_load(content or "")
        if isinstance(parsed, dict):
            payload = parsed
    except yaml.YAMLError:
        payload = {}

    layout = _normalize_matching_layout(options, payload)

    if layout == "vertical":
        first_items = _as_text_list(
            payload.get("top") or payload.get("oben") or payload.get("first")
        )
        second_items = _as_text_list(
            payload.get("bottom") or payload.get("unten") or payload.get("second")
        )
    else:
        first_items = _as_text_list(
            payload.get("left") or payload.get("links") or payload.get("first")
        )
        second_items = _as_text_list(
            payload.get("right") or payload.get("rechts") or payload.get("second")
        )

    if not first_items:
        first_items = _as_text_list(options.get("left") or options.get("top"))
    if not second_items:
        second_items = _as_text_list(options.get("right") or options.get("bottom"))

    raw_pairs = (
        payload.get("matches")
        or payload.get("links")
        or payload.get("pairs")
        or payload.get("zuordnung")
    )
    if raw_pairs is None:
        raw_pairs = options.get("matches") or options.get("links")

    if isinstance(raw_pairs, str):
        raw_pairs = _parse_option_list(raw_pairs)
    elif not isinstance(raw_pairs, list):
        raw_pairs = []

    parsed_pairs = _parse_matching_pairs(raw_pairs)
    valid_pairs = []
    for first_index, second_index in parsed_pairs:
        if 1 <= first_index <= len(first_items) and 1 <= second_index <= len(
            second_items
        ):
            valid_pairs.append((first_index, second_index))

    raw_worksheet_pairs = payload.get("worksheet_matches")
    if raw_worksheet_pairs is None:
        raw_worksheet_pairs = options.get("worksheet_matches")

    if isinstance(raw_worksheet_pairs, str):
        raw_worksheet_pairs = _parse_option_list(raw_worksheet_pairs)
    elif not isinstance(raw_worksheet_pairs, list):
        raw_worksheet_pairs = []

    parsed_worksheet_pairs = _parse_matching_pairs(raw_worksheet_pairs)
    valid_worksheet_pairs = []
    for first_index, second_index in parsed_worksheet_pairs:
        if 1 <= first_index <= len(first_items) and 1 <= second_index <= len(
            second_items
        ):
            valid_worksheet_pairs.append((first_index, second_index))

    show_guides = _parse_matching_bool_option(
        payload.get("show_guides", options.get("show_guides")),
        default=False,
    )
    height_mode = _normalize_matching_height_mode(options, payload)
    align = _normalize_matching_align(options, payload)
    lane_align = _normalize_lane_align(options, payload)

    return (
        layout,
        first_items,
        second_items,
        valid_pairs,
        valid_worksheet_pairs,
        show_guides,
        height_mode,
        align,
        lane_align,
    )


def _render_matching_item(md, raw_item):
    """Rendert einen einzelnen Matching-Eintrag als HTML."""
    return md.convert(normalize_markdown(raw_item or "")).strip()


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
