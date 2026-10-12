"""Zahlenstrahl: YAML-Inhalt und Block-Optionen in Konfiguration, Beschriftungen,
Antwortfelder und Boegen uebersetzen.
"""

from __future__ import annotations

import re
from .answer_special_shared import _option_is_enabled, _safe_int
from .answer_yaml_payload import parse_yaml_answer_payload_with_solution
from .answer_numberline_values import (
    _as_numberline_float,
    _format_numberline_value,
    _normalize_show_mode,
    _parse_numberline_positive_float,
)
from .answer_numberline_scale import (
    _build_anchored_tick_values,
    _compute_major_tick_indices,
    _resolve_tick_spacing_mm,
    _select_auto_tick_step,
    _target_interval_count,
)


def _parse_number_line_payload(content):
    """Parse YAML payload for number line markers and optional extra solution text."""
    return parse_yaml_answer_payload_with_solution(content)


def _build_number_line_config(options):
    """Build normalized number line config from answer options."""
    show_ticks = _option_is_enabled(options.get("ticks"), default=True)
    tick_spacing_mm = _resolve_tick_spacing_mm(options)

    explicit_min = _as_numberline_float(options.get("min") or options.get("minimum"))
    explicit_max = _as_numberline_float(options.get("max") or options.get("maximum"))
    explicit_step = _parse_numberline_positive_float(options.get("tick_step"), None)

    if (
        explicit_min is not None
        and explicit_max is not None
        and explicit_max > explicit_min
    ):
        number_min = explicit_min
        number_max = explicit_max
    else:
        number_min = _as_numberline_float(options.get("start"))
        if number_min is None:
            number_min = 0.0

        value_step = _parse_numberline_positive_float(
            options.get("value_step") or options.get("step"), None
        )
        if value_step is None:
            value_step = 1.0

        tick_count = _target_interval_count(options, tick_spacing_mm)
        number_max = number_min + (value_step * tick_count)
        explicit_step = value_step

    total_range = max(1e-9, number_max - number_min)

    if explicit_step is not None:
        tick_step = explicit_step
        tick_values = (
            _build_anchored_tick_values(number_min, number_max, tick_step)
            if show_ticks
            else []
        )
        intervals = max(1, len(tick_values) - 1)
    else:
        target_intervals = _target_interval_count(options, tick_spacing_mm)
        tick_step = _select_auto_tick_step(
            total_range,
            target_intervals,
            max(0, _safe_int(options.get("major_every"), 0)),
        )
        tick_values = (
            _build_anchored_tick_values(number_min, number_max, tick_step)
            if show_ticks
            else []
        )
        intervals = max(1, len(tick_values) - 1)

    major_every = max(0, _safe_int(options.get("major_every"), 0))
    major_tick_indices = _compute_major_tick_indices(
        tick_values, tick_step, major_every
    )
    return {
        "min": number_min,
        "max": number_max,
        "intervals": intervals,
        "tick_step": tick_step,
        "tick_spacing_mm": tick_spacing_mm,
        "tick_values": tick_values,
        "major_every": major_every,
        "major_tick_indices": major_tick_indices,
        "show_ticks": show_ticks,
    }


def _parse_numberline_labels(raw_items, positive_sign=False):
    """Parse label entries for displayed numbers on the number line."""
    parsed = []
    if isinstance(raw_items, list):
        items = raw_items
    elif isinstance(raw_items, dict):
        items = [raw_items]
    else:
        return parsed

    for item in items:
        if isinstance(item, dict):
            value = _as_numberline_float(item.get("value"))
            if value is None:
                continue
            text = str(
                item.get("text")
                or item.get("label")
                or _format_numberline_value(value, positive_sign=positive_sign)
            ).strip()
            if not text:
                text = _format_numberline_value(value, positive_sign=positive_sign)
            position_raw = (
                str(item.get("position") or item.get("pos") or "below").strip().lower()
            )
            position = "above" if position_raw == "above" else "below"
            parsed.append(
                {
                    "value": value,
                    "text": text,
                    "show": _normalize_show_mode(item.get("show")),
                    "position": position,
                }
            )
            continue

        value = _as_numberline_float(item)
        if value is None:
            continue
        parsed.append(
            {
                "value": value,
                "text": _format_numberline_value(value, positive_sign=positive_sign),
                "show": "both",
                "position": "below",
            }
        )

    return parsed


def _parse_numberline_simple_values(raw_values, show="&", positive_sign=False):
    """Parse a list of plain numeric values as label entries."""
    values = []
    if isinstance(raw_values, list):
        source_values = raw_values
    elif isinstance(raw_values, str):
        source_values = [
            part for part in re.split(r"[|;\\s]+", raw_values) if part.strip()
        ]
    else:
        return values

    for raw in source_values:
        value = _as_numberline_float(raw)
        if value is None:
            continue
        values.append(
            {
                "value": value,
                "text": _format_numberline_value(value, positive_sign=positive_sign),
                "show": _normalize_show_mode(show),
                "position": "below",
            }
        )

    return values


def _parse_numberline_answers(raw_items, positive_sign=False):
    """Parse answer-box entries (empty on worksheet, filled in solution mode)."""
    parsed = []
    if isinstance(raw_items, list):
        items = raw_items
    elif isinstance(raw_items, dict):
        items = [raw_items]
    else:
        return parsed

    for item in items:
        if isinstance(item, dict):
            value = _as_numberline_float(item.get("value"))
            if value is None:
                continue
            text = str(
                item.get("text")
                or item.get("label")
                or _format_numberline_value(value, positive_sign=positive_sign)
            ).strip()
            if not text:
                text = _format_numberline_value(value, positive_sign=positive_sign)
            parsed.append(
                {
                    "value": value,
                    "text": text,
                    "show": _normalize_show_mode(item.get("show")),
                }
            )
            continue

        value = _as_numberline_float(item)
        if value is None:
            continue
        parsed.append(
            {
                "value": value,
                "text": _format_numberline_value(value, positive_sign=positive_sign),
                "show": "both",
            }
        )

    return parsed


def _parse_numberline_arcs(raw_items):
    """Parse arc/jump entries drawn from one number-line value to another."""
    parsed = []
    if isinstance(raw_items, list):
        items = raw_items
    elif isinstance(raw_items, dict):
        items = [raw_items]
    else:
        return parsed

    for item in items:
        if not isinstance(item, dict):
            continue

        from_value = _as_numberline_float(item.get("from", item.get("start")))
        to_value = _as_numberline_float(item.get("to", item.get("end")))
        if from_value is None or to_value is None:
            continue

        side_raw = (
            str(item.get("side") or item.get("position") or "above").strip().lower()
        )
        side = "below" if side_raw == "below" else "above"
        label = str(item.get("label") or item.get("text") or "").strip()
        arrow = _option_is_enabled(item.get("arrow"), default=True)
        parsed.append(
            {
                "from": from_value,
                "to": to_value,
                "label": label,
                "arrow": arrow,
                "side": side,
                "show": _normalize_show_mode(item.get("show")),
            }
        )

    return parsed
