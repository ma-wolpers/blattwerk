"""Number line answer renderer with configurable ticks, labels, and solution boxes."""

from __future__ import annotations

from html import escape

from .answer_special_shared import _option_is_enabled
from .answer_numberline_values import _format_numberline_value, _is_visible, _parse_css_size
from .answer_numberline_scale import _resolve_numberline_width
from .answer_numberline_parse import (
    _build_number_line_config,
    _parse_number_line_payload,
    _parse_numberline_answers,
    _parse_numberline_arcs,
    _parse_numberline_labels,
    _parse_numberline_simple_values,
)


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


def _numberline_x_coord(value, min_value, max_value, x_start=8.0, x_end=92.0):
    """Map a value to an x-position in the SVG coordinate system."""
    total = max(1e-9, max_value - min_value)
    rel = (value - min_value) / total
    rel = max(0.0, min(1.0, rel))
    return x_start + ((x_end - x_start) * rel)


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


