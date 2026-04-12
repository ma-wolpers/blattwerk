"""Number line answer renderer with configurable ticks, labels, and solution boxes."""

from __future__ import annotations

import math
import re
from html import escape

import yaml

from .answer_special_shared import _option_is_enabled, _safe_int


def render_number_line_answer(
    options, content, include_solutions, render_solution_text
):
    """Render a horizontal number line answer field with configurable ticks and markers."""
    payload, fallback_solution_text = _parse_number_line_payload(content)
    config = _build_number_line_config(options)
    auto_plus_positive = _option_is_enabled(
        options.get("positive_sign") or options.get("signed_positive"),
        default=config["min"] < 0,
    )
    labels = _parse_numberline_labels(
        payload.get("labels") or payload.get("preset") or payload.get("numbers"),
        auto_plus_positive,
    )
    labels.extend(
        _parse_numberline_simple_values(
            payload.get("preset_values"), show="&", positive_sign=auto_plus_positive
        )
    )
    answers = _parse_numberline_answers(
        payload.get("answers") or payload.get("boxes") or payload.get("blanks"),
        auto_plus_positive,
    )
    arcs = _parse_numberline_arcs(
        payload.get("arcs") or payload.get("jumps") or payload.get("arrows")
    )

    numberline_html = _render_number_line_html(
        config, labels, answers, arcs, include_solutions
    )
    debug_html = _render_numberline_debug_comment(options, config)

    height = _parse_css_size(options.get("height"), "2.7cm")
    width = _resolve_numberline_width(options, config)
    base_html = (
        f"<div class='answer numberline' style='height:{height}; width:{width}'>"
        f"{debug_html}"
        f"{numberline_html}"
        "</div>"
    )

    if include_solutions and fallback_solution_text.strip():
        solution_text_html = render_solution_text(fallback_solution_text)
        if solution_text_html:
            return f"<div class='answer-with-solution'>{solution_text_html}{base_html}</div>"

    return base_html


def _parse_number_line_payload(content):
    """Parse YAML payload for number line markers and optional extra solution text."""
    text = (content or "").strip()
    if not text:
        return {}, ""

    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}, ""

    if isinstance(parsed, dict):
        return parsed, str(parsed.get("solution") or parsed.get("solution_text") or "")

    return {}, ""


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


def _resolve_numberline_width(options, config):
    """Resolve final CSS width; derive natural width when no explicit width is provided."""
    max_width_mm = _resolve_max_width_mm(options)

    explicit_width = _parse_css_size(options.get("width"), None)
    if explicit_width:
        explicit_width_mm = _css_length_to_mm(explicit_width)
        if explicit_width_mm is not None and explicit_width_mm > max_width_mm:
            return f"{max_width_mm:.3f}mm"
        return explicit_width

    if _option_is_enabled(options.get("full_width"), default=True):
        return "100%"

    intervals = max(1, int(config.get("intervals", 1)))
    tick_spacing_mm = _parse_numberline_positive_float(
        config.get("tick_spacing_mm"), 5.0
    )
    if tick_spacing_mm is None:
        tick_spacing_mm = 5.0

    # Includes left/right inner field margins so the first/last labels stay readable.
    natural_width_mm = (intervals * tick_spacing_mm) + 8.0
    natural_width_mm = max(60.0, natural_width_mm)
    return f"{min(natural_width_mm, max_width_mm):.3f}mm"


def _resolve_tick_spacing_mm(options):
    """Resolve preferred tick spacing in millimeters (mm preferred over cm)."""
    direct_mm = _parse_numberline_positive_float(options.get("tick_spacing_mm"), None)
    if direct_mm is not None:
        return direct_mm

    cm_value = _parse_numberline_positive_float(
        options.get("tick_spacing_cm") or options.get("tick_spacing"), None
    )
    if cm_value is not None:
        return cm_value * 10.0

    return 5.0


def _resolve_max_width_mm(options):
    """Resolve maximum rendered width in mm (A4-safe default)."""
    max_width_mm = _parse_numberline_positive_float(options.get("max_width_mm"), None)
    if max_width_mm is not None:
        return max(60.0, max_width_mm)

    max_width_cm = _parse_numberline_positive_float(options.get("max_width_cm"), None)
    if max_width_cm is not None:
        return max(60.0, max_width_cm * 10.0)

    return 165.0


def _target_interval_count(options, tick_spacing_mm):
    """Estimate a practical interval count from spacing and max width limits."""
    max_width_mm = _resolve_max_width_mm(options)
    usable_width_mm = max(20.0, max_width_mm - 8.0)
    spacing = max(1.0, tick_spacing_mm)
    return max(2, min(80, int(round(usable_width_mm / spacing))))


def _css_length_to_mm(css_size):
    """Convert absolute CSS lengths to mm where possible, else return None."""
    text = str(css_size or "").strip().lower()
    mm_match = re.fullmatch(r"(\d+(?:\.\d+)?)mm", text)
    if mm_match:
        return float(mm_match.group(1))

    cm_match = re.fullmatch(r"(\d+(?:\.\d+)?)cm", text)
    if cm_match:
        return float(cm_match.group(1)) * 10.0

    return None


def _render_number_line_html(config, labels, answers, arcs, include_solutions):
    """Render number line purely in HTML/CSS with one shared coordinate system."""
    min_value = config["min"]
    max_value = config["max"]
    tick_values = config["tick_values"]
    show_ticks = config["show_ticks"]
    major_tick_indices = set(config.get("major_tick_indices") or [])

    tick_start_x = 8.0
    tick_end_x = 92.0
    right_overhang_x = 6.0
    left_overhang_x = 0.0 if min_value == 0 else 6.0
    axis_start_x = tick_start_x - left_overhang_x
    axis_end_x = tick_end_x + right_overhang_x
    view_height = 28.0

    axis_y = 11.8
    tick_minor_top = 8.8
    tick_minor_bottom = 14.8
    tick_major_top = 7.1
    tick_major_bottom = 16.5
    label_above_y = 4.1
    label_below_y = 19.4
    answer_y = 20.0
    answer_height = 7.2

    parts = [
        "<div class='numberline-canvas'>",
        f"<div class='numberline-axis-html' style='left:{axis_start_x:.4f}%; top:{(axis_y / view_height) * 100.0:.4f}%; width:{(axis_end_x - axis_start_x):.4f}%'></div>",
        f"<span class='numberline-axis-arrow-html' style='left:{axis_end_x:.4f}%; top:{(axis_y / view_height) * 100.0:.4f}%'>▶</span>",
    ]

    visible_arcs = [
        entry for entry in arcs if _is_visible(entry["show"], include_solutions)
    ]
    for entry in visible_arcs:
        from_value = entry["from"]
        to_value = entry["to"]
        if (
            from_value < min_value
            or from_value > max_value
            or to_value < min_value
            or to_value > max_value
        ):
            continue

        start_x = _numberline_x_coord(
            from_value, min_value, max_value, tick_start_x, tick_end_x
        )
        end_x = _numberline_x_coord(
            to_value, min_value, max_value, tick_start_x, tick_end_x
        )
        if abs(end_x - start_x) < 0.0001:
            continue

        left_x = min(start_x, end_x)
        width_x = abs(end_x - start_x)
        base_curve = min(8.0, max(3.0, width_x * 0.16))
        arc_height_pct = (base_curve / view_height) * 100.0

        if entry["side"] == "above":
            top_y = axis_y - base_curve
            arc_class = "numberline-arc-html numberline-arc-html-above"
            arrow_top_y = axis_y - 0.2
            label_y = top_y - 1.2
        else:
            top_y = axis_y
            arc_class = "numberline-arc-html numberline-arc-html-below"
            arrow_top_y = axis_y + 0.2
            label_y = (axis_y + base_curve) + 1.2

        parts.append(
            f"<div class='{arc_class}' style='left:{left_x:.4f}%; top:{(top_y / view_height) * 100.0:.4f}%; width:{width_x:.4f}%; height:{arc_height_pct:.4f}%'></div>"
        )

        if entry["arrow"]:
            arrow_left = end_x
            forward = end_x >= start_x
            if entry["side"] == "above":
                arrow_glyph = "▼"
                tilt_degrees = -14 if forward else 14
            else:
                arrow_glyph = "▲"
                tilt_degrees = 14 if forward else -14
            parts.append(
                f"<span class='numberline-arc-arrow-html' style='left:{arrow_left:.4f}%; top:{(arrow_top_y / view_height) * 100.0:.4f}%; transform:translate(-50%, -50%) rotate({tilt_degrees}deg)'>{arrow_glyph}</span>"
            )

        if entry["label"]:
            control_x = (start_x + end_x) / 2.0
            parts.append(
                f"<span class='numberline-arc-label-html' style='left:{control_x:.4f}%; top:{(label_y / view_height) * 100.0:.4f}%'>{escape(entry['label'])}</span>"
            )

    if show_ticks:
        for index, tick_value in enumerate(tick_values):
            x = _numberline_x_coord(
                tick_value, min_value, max_value, tick_start_x, tick_end_x
            )
            is_major = index in major_tick_indices
            y_top = tick_major_top if is_major else tick_minor_top
            y_bottom = tick_major_bottom if is_major else tick_minor_bottom
            tick_class = (
                "numberline-tick-html numberline-tick-html-major"
                if is_major
                else "numberline-tick-html"
            )
            parts.append(
                f"<span class='{tick_class}' style='left:{x:.4f}%; top:{(y_top / view_height) * 100.0:.4f}%; height:{((y_bottom - y_top) / view_height) * 100.0:.4f}%'></span>"
            )

        total_range = max(1e-9, max_value - min_value)
        tick_step = max(1e-9, config.get("tick_step") or 0.0)
        x_step = ((tick_end_x - tick_start_x) * tick_step) / total_range

        if x_step > 1e-9:
            left_x = tick_start_x - x_step
            while left_x >= axis_start_x - 1e-6:
                parts.append(
                    f"<span class='numberline-tick-html' style='left:{left_x:.4f}%; top:{(tick_minor_top / view_height) * 100.0:.4f}%; height:{((tick_minor_bottom - tick_minor_top) / view_height) * 100.0:.4f}%'></span>"
                )
                left_x -= x_step

            right_x = tick_end_x + x_step
            while right_x <= axis_end_x + 1e-6:
                parts.append(
                    f"<span class='numberline-tick-html' style='left:{right_x:.4f}%; top:{(tick_minor_top / view_height) * 100.0:.4f}%; height:{((tick_minor_bottom - tick_minor_top) / view_height) * 100.0:.4f}%'></span>"
                )
                right_x += x_step

    for entry in labels:
        if not _is_visible(entry["show"], include_solutions):
            continue
        value = entry["value"]
        if value < min_value or value > max_value:
            continue

        x = _numberline_x_coord(value, min_value, max_value, tick_start_x, tick_end_x)
        top_y = label_above_y if entry["position"] == "above" else label_below_y
        base_position_cls = (
            "numberline-label-html-above"
            if entry["position"] == "above"
            else "numberline-label-html-below"
        )
        mode_cls = f"numberline-label-html-mode-{entry['show']}"
        cls = f"numberline-label-html {base_position_cls} {mode_cls}"
        parts.append(
            f"<span class='{cls}' style='left:{x:.4f}%; top:{(top_y / view_height) * 100.0:.4f}%'>{escape(entry['text'])}</span>"
        )

    for entry in answers:
        if not _is_visible(entry["show"], include_solutions):
            continue
        value = entry["value"]
        if value < min_value or value > max_value:
            continue

        x = _numberline_x_coord(value, min_value, max_value, tick_start_x, tick_end_x)
        parts.append(
            f"<span class='numberline-answer-box-html' style='left:{x:.4f}%; top:{(answer_y / view_height) * 100.0:.4f}%; height:{(answer_height / view_height) * 100.0:.4f}%'></span>"
        )

        if include_solutions:
            center_y = answer_y + (answer_height / 2.0)
            parts.append(
                f"<span class='numberline-answer-text-html' style='left:{x:.4f}%; top:{(center_y / view_height) * 100.0:.4f}%'>{escape(entry['text'])}</span>"
            )

    parts.append("</div>")
    return "".join(parts)


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


def _numberline_x_coord(value, min_value, max_value, x_start=8.0, x_end=92.0):
    """Map a value to an x-position in the SVG coordinate system."""
    total = max(1e-9, max_value - min_value)
    rel = (value - min_value) / total
    rel = max(0.0, min(1.0, rel))
    return x_start + ((x_end - x_start) * rel)


def _compute_major_tick_indices(tick_values, tick_step, major_every):
    """Compute unique major tick indices aligned to rounded 5/10 value targets."""
    if major_every <= 1 or not tick_values:
        return []

    step = _parse_numberline_positive_float(tick_step, None)
    if step is None:
        return []

    normalized_every = _normalize_major_every(major_every)
    raw_major_step = step * normalized_every
    major_step = _snap_to_five_ten_step(raw_major_step)
    if major_step <= 0:
        return []

    major_indices = []
    for index, tick_value in enumerate(tick_values):
        ratio = tick_value / major_step
        if abs(ratio - round(ratio)) < 1e-6:
            major_indices.append(index)

    if major_indices:
        return major_indices

    # Fallback for explicit odd tick steps: keep deterministic spacing by index.
    return [idx for idx in range(0, len(tick_values), normalized_every)]


def _normalize_major_every(major_every):
    """Normalize major tick stride to educationally common 5/10 groupings."""
    if major_every <= 5:
        return 5
    return 10


def _snap_to_five_ten_step(raw_step):
    """Snap any positive step to nearest 5*10^k or 10*10^k value."""
    if raw_step <= 0:
        return 0.0

    exponent = math.floor(math.log10(raw_step))
    scale = 10**exponent
    candidates = [5.0 * scale, 10.0 * scale]

    # Also test adjacent decades to avoid bad snaps near borders.
    lower_scale = scale / 10.0
    higher_scale = scale * 10.0
    candidates.extend(
        [5.0 * lower_scale, 10.0 * lower_scale, 5.0 * higher_scale, 10.0 * higher_scale]
    )

    positive_candidates = [candidate for candidate in candidates if candidate > 0]
    return min(positive_candidates, key=lambda candidate: abs(candidate - raw_step))


def _select_auto_tick_step(value_range, target_intervals, major_every):
    """Pick an auto tick step that is readable and stable for major tick grouping."""
    if value_range <= 0:
        return 1.0

    raw_step = value_range / max(1, target_intervals)
    if major_every > 1:
        normalized_every = _normalize_major_every(major_every)
        raw_major_step = raw_step * normalized_every
        major_step = _snap_to_five_ten_step(raw_major_step)
        return max(1e-9, major_step / normalized_every)

    return _snap_to_pretty_decimal_step(raw_step)


def _snap_to_pretty_decimal_step(raw_step):
    """Snap a raw numeric step to common readable decimal increments."""
    if raw_step <= 0:
        return 1.0

    exponent = math.floor(math.log10(raw_step))
    base = 10**exponent
    multipliers = [1.0, 2.0, 2.5, 5.0, 10.0]

    candidates = []
    for scale in (base / 10.0, base, base * 10.0):
        candidates.extend([multiplier * scale for multiplier in multipliers])

    positive_candidates = [candidate for candidate in candidates if candidate > 0]
    return min(positive_candidates, key=lambda candidate: abs(candidate - raw_step))


def _build_anchored_tick_values(min_value, max_value, tick_step):
    """Build ticks anchored to a zero-based raster, clipped to the visible range."""
    step = max(1e-9, tick_step)
    start_index = math.ceil((min_value - 1e-9) / step)
    end_index = math.floor((max_value + 1e-9) / step)

    if end_index < start_index:
        midpoint = (min_value + max_value) / 2.0
        snapped = round(midpoint / step) * step
        return [snapped]

    values = [index * step for index in range(start_index, end_index + 1)]
    return values


def _render_numberline_debug_comment(options, config):
    """Return optional debug comment for deterministic verification in rendered HTML."""
    if not _option_is_enabled(options.get("debug"), default=False):
        return ""

    tick_values = config.get("tick_values") or []
    major_indices = set(config.get("major_tick_indices") or [])
    major_values = [
        tick_values[idx] for idx in sorted(major_indices) if 0 <= idx < len(tick_values)
    ]

    tick_preview = ",".join(
        _format_numberline_value(value) for value in tick_values[:18]
    )
    major_preview = ",".join(
        _format_numberline_value(value) for value in major_values[:18]
    )
    return (
        "<!-- numberline-debug: "
        f"min={_format_numberline_value(config.get('min', 0.0))}; "
        f"max={_format_numberline_value(config.get('max', 0.0))}; "
        f"tick_step={_format_numberline_value(config.get('tick_step', 0.0))}; "
        f"tick_count={len(tick_values)}; major_count={len(major_values)}; "
        f"ticks={tick_preview}; majors={major_preview}"
        " -->"
    )


def _format_numberline_value(value, positive_sign=False):
    """Format numeric values with compact decimal output and comma separator."""
    rounded = 0.0 if abs(value) < 1e-9 else value
    text = f"{rounded:.6f}".rstrip("0").rstrip(".")
    if text in {"-0", ""}:
        text = "0"
    if positive_sign and rounded > 0:
        text = f"+{text}"
    return text.replace(".", ",")


def _parse_css_size(raw_value, default_value):
    """Parse safe CSS sizes for answer-field width/height values."""
    if raw_value is None:
        return default_value

    text = str(raw_value).strip().lower().replace(",", ".")
    if text == "auto":
        return text
    if re.fullmatch(r"\d+(?:\.\d+)?(px|%|cm|mm|in|pt|em|rem|vh|vw)", text):
        return text
    return default_value


def _as_numberline_float(value):
    """Parse numeric values for numberline config, tolerant to decimal comma."""
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    return _as_float(value)


def _parse_numberline_positive_float(value, default):
    """Parse strictly positive floats for numberline values (comma tolerant)."""
    parsed = _as_numberline_float(value)
    if parsed is None or parsed <= 0:
        return default
    return parsed


def _as_float(value):
    """Convert value to float and return None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_visible(show_value, include_solutions):
    """Evaluate marker-based visibility for numberline elements."""
    if show_value in {"worksheet", "solution", "both", "invalid"}:
        normalized = show_value
    else:
        normalized = _normalize_show_mode(show_value)
    if normalized == "worksheet":
        return not include_solutions
    if normalized == "solution":
        return include_solutions
    if normalized == "both":
        return True
    return False


def _normalize_show_mode(show_value):
    """Normalize marker visibility to internal `worksheet|solution|both` mode."""
    normalized = str(show_value or "&").strip()
    if normalized == "§":
        return "worksheet"
    if normalized == "%":
        return "solution"
    if normalized == "&":
        return "both"
    return "invalid"
