"""Liest `:::matching`-Blöcke: Seiten, Verbindungen und Layout-Optionen.

Gemeinsame Quelle für Renderer (`answer_special_matching`) und Validator
(`blatt_validator_answers`), damit beide dieselben Einträge und Verbindungen sehen.
"""

from __future__ import annotations

import re

import yaml

from .answer_special_shared import _as_text_list, _normalize_keyword, _parse_option_list


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


def parse_matching_sources(options, content) -> tuple[list, list, list, list]:
    """Seiten und alle Verbindungen, auch die, die der Renderer als ungültig übergeht.

    Returns:
        `(erste_seite, zweite_seite, matches, worksheet_matches)`; die Verbindungen sind
        ungefilterte `(links, rechts)`-Paare.
    """
    _layout, first, second, _valid, _worksheet, *_rest = _parse_matching_content(options, content)
    try:
        parsed = yaml.safe_load(content or "")
    except yaml.YAMLError:
        parsed = None
    payload = parsed if isinstance(parsed, dict) else {}
    raw_matches = payload.get("matches") or payload.get("links") or payload.get("pairs") or payload.get("zuordnung")
    if raw_matches is None:
        raw_matches = options.get("matches") or options.get("links")
    raw_worksheet = payload.get("worksheet_matches")
    if raw_worksheet is None:
        raw_worksheet = options.get("worksheet_matches")

    def as_pairs(raw) -> list:
        return _parse_matching_pairs(_parse_option_list(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else [])

    return first, second, as_pairs(raw_matches), as_pairs(raw_worksheet)
