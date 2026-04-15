"""Grid answer renderers for writing fields and coordinate systems."""

from __future__ import annotations

import ast
import math
import re
from html import escape

from .answer_special_shared import _option_is_enabled, _safe_int
from .answer_yaml_payload import parse_yaml_answer_payload_with_solution


def _parse_grid_scale(raw_value):
    """Parst den Grid-Maßstab als sichere CSS-Länge."""
    if raw_value is None:
        return "0.5cm"

    text = str(raw_value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?(cm|mm|px|pt|em|rem|%)", text, flags=re.IGNORECASE):
        return text
    return "0.5cm"


def render_dots_answer(options, content, include_solutions, render_solution_text):
    """Render a dotted answer field with optional in-field solution overlay text."""
    height = options.get("height", "4cm")
    solution_text_html = render_solution_text(content, include_solutions)
    if solution_text_html:
        return (
            f"<div class='answer dots answer-overlay-container' style='height:{height}'>"
            f"<div class='answer-overlay-text'>{solution_text_html}</div>"
            "</div>"
        )
    return f"<div class='answer dots' style='height:{height}'></div>"


def render_grid_field_answer(options, content, include_solutions, render_solution_text):
    """Render a writing grid with optional marker-based overlay text."""
    rows = max(1, _safe_int(options.get("rows", 5), 5))
    scale = _parse_grid_scale(options.get("scale"))
    cols_option = options.get("cols")
    has_explicit_cols = cols_option is not None and str(cols_option).strip() != ""
    cols = max(1, _safe_int(cols_option, 20)) if has_explicit_cols else 20

    grid_classes = ["answer", "grid"]
    style_parts = [f"--rows:{rows}", f"--cell-size:{scale}"]
    if has_explicit_cols:
        style_parts.append(f"--cols:{cols}")
    else:
        grid_classes.append("grid-auto-width")

    solution_text_html = render_solution_text(content, include_solutions)

    overlay_parts = []
    if solution_text_html:
        overlay_parts.append(
            f"<div class='answer-overlay-text'>{solution_text_html}</div>"
        )

    classes_html = " ".join(grid_classes)
    style_html = "; ".join(style_parts)
    if overlay_parts:
        classes_html = f"{classes_html} answer-overlay-container"
        return f"<div class='{classes_html}' style='{style_html}'>{''.join(overlay_parts)}</div>"

    return f"<div class='{classes_html}' style='{style_html}'></div>"


def render_grid_system_answer(options, content, include_solutions, render_solution_text):
    """Render a coordinate/raster system with optional YAML-defined overlays."""
    rows = max(1, _safe_int(options.get("rows", 5), 5))
    scale = _parse_grid_scale(options.get("scale"))
    cols_option = options.get("cols")
    has_explicit_cols = cols_option is not None and str(cols_option).strip() != ""
    cols = max(1, _safe_int(cols_option, 20)) if has_explicit_cols else 20

    payload, fallback_solution_text = _parse_grid_payload(content)
    primitives_svg = _render_grid_primitives_svg(
        options, payload, rows, cols, include_solutions
    )

    grid_classes = ["answer", "grid"]
    style_parts = [f"--rows:{rows}", f"--cell-size:{scale}"]
    if has_explicit_cols or primitives_svg:
        style_parts.append(f"--cols:{cols}")
    else:
        grid_classes.append("grid-auto-width")

    solution_text_html = ""
    if include_solutions and fallback_solution_text.strip():
        solution_text_html = render_solution_text(fallback_solution_text)

    overlay_parts = []
    if primitives_svg:
        overlay_parts.append(primitives_svg)
    if solution_text_html:
        overlay_parts.append(
            f"<div class='answer-overlay-text'>{solution_text_html}</div>"
        )

    classes_html = " ".join(grid_classes)
    style_html = "; ".join(style_parts)
    if overlay_parts:
        classes_html = f"{classes_html} answer-overlay-container"
        return f"<div class='{classes_html}' style='{style_html}'>{''.join(overlay_parts)}</div>"

    return f"<div class='{classes_html}' style='{style_html}'></div>"


def _parse_grid_payload(content):
    """Parse YAML payload for grid overlays and return `(payload, fallback_solution_text)`."""
    return parse_yaml_answer_payload_with_solution(content)


def _render_grid_primitives_svg(options, payload, rows, cols, include_solutions):
    """Render optional geometric primitives inside the grid as SVG."""
    axis_enabled = _option_is_enabled(options.get("axis"), default=False)
    origin = _parse_origin(options.get("origin"), cols, rows) if axis_enabled else None
    axis_origin = (
        _clamp_axis_origin(origin[0], origin[1], cols, rows)
        if axis_enabled and origin is not None
        else None
    )
    if axis_enabled and origin is None:
        axis_enabled = False

    step_x = _parse_positive_float(options.get("step_x"), 1.0)
    step_y = _parse_positive_float(options.get("step_y"), 1.0)

    lines = []
    if axis_enabled and origin is not None and axis_origin is not None:
        logical_ox, logical_oy = origin
        axis_ox, axis_oy = axis_origin
        axis_label_x = _resolve_axis_name(
            options,
            "axis_label_x",
            aliases=("x_label", "axis_x_label"),
            default="x",
        )
        axis_label_y = _resolve_axis_name(
            options,
            "axis_label_y",
            aliases=("y_label", "axis_y_label"),
            default="y",
        )
        lines.append(
            f"<line class='grid-axis' x1='0' y1='{axis_oy:.4f}' x2='{cols:.4f}' y2='{axis_oy:.4f}' />"
        )
        lines.append(
            f"<line class='grid-axis' x1='{axis_ox:.4f}' y1='0' x2='{axis_ox:.4f}' y2='{rows:.4f}' />"
        )
        lines.extend(
            _render_axis_arrowheads_and_names(
                axis_ox, axis_oy, cols, rows, axis_label_x, axis_label_y
            )
        )
        lines.extend(
            _render_axis_ticks_and_labels(
                logical_ox,
                logical_oy,
                axis_ox,
                axis_oy,
                cols,
                rows,
                step_x,
                step_y,
            )
        )

    point_entries = _parse_points(
        payload.get("points"), axis_enabled, origin, step_x, step_y, include_solutions
    )
    pair_entries = _parse_pairs(
        payload.get("pairs"), axis_enabled, origin, step_x, step_y, include_solutions
    )
    fn_entries = _parse_functions(
        payload.get("functions"), axis_enabled, include_solutions
    )

    point_markup = []
    for px, py, label, mode in point_entries + pair_entries:
        if not _inside_grid(px, py, cols, rows):
            continue
        cross_half = 0.18
        point_markup.append(
            f"<line class='grid-point grid-mode-{mode}' x1='{px - cross_half:.4f}' y1='{py - cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py + cross_half:.4f}' />"
        )
        point_markup.append(
            f"<line class='grid-point grid-mode-{mode}' x1='{px - cross_half:.4f}' y1='{py + cross_half:.4f}' x2='{px + cross_half:.4f}' y2='{py - cross_half:.4f}' />"
        )
        if label:
            point_markup.append(
                f"<text class='grid-point-label grid-mode-{mode}' x='{px + 0.24:.4f}' y='{py - 0.24:.4f}'>{escape(label)}</text>"
            )

    if pair_entries:
        filtered = [
            (x, y, mode)
            for x, y, _label, mode in pair_entries
            if _inside_grid(x, y, cols, rows)
        ]
        if len(filtered) >= 2:
            pairs_mode = filtered[0][2]
            points_attr = " ".join(
                f"{x:.4f},{y:.4f}"
                for x, y, _mode in sorted(filtered, key=lambda item: item[0])
            )
            lines.append(
                f"<polyline class='grid-pairs-line grid-mode-{pairs_mode}' points='{points_attr}' />"
            )

    for expr, x_min, x_max, mode in fn_entries:
        poly_points = _sample_function_points(
            expr, x_min, x_max, origin, step_x, step_y, cols, rows
        )
        if len(poly_points) < 2:
            continue
        points_attr = " ".join(f"{x:.4f},{y:.4f}" for x, y in poly_points)
        lines.append(
            f"<polyline class='grid-function-line grid-mode-{mode}' points='{points_attr}' />"
        )

    all_markup = lines + point_markup
    if not all_markup:
        return ""

    return (
        f"<svg class='grid-overlay' viewBox='0 0 {cols} {rows}' preserveAspectRatio='none' aria-hidden='true'>"
        f"{''.join(all_markup)}"
        "</svg>"
    )


def _parse_origin(raw_origin, cols, rows):
    """Parse origin in `col,row` form without clamping to grid extents."""
    if not raw_origin:
        return None

    text = str(raw_origin).strip().replace(";", ",").replace(" ", "")
    parts = [part for part in text.split(",") if part]
    if len(parts) != 2:
        return None

    try:
        col = float(parts[0])
        row = float(parts[1])
    except ValueError:
        return None

    return col, row


def _clamp_axis_origin(origin_x, origin_y, cols, rows):
    """Clamp only the visible axis position so axes stay on-grid."""
    return (
        _clamp_to_range(origin_x, 0.0, float(cols)),
        _clamp_to_range(origin_y, 0.0, float(rows)),
    )


def _clamp_to_range(value, lower, upper):
    """Clamp a scalar value into the inclusive `[lower, upper]` range."""
    return max(lower, min(upper, float(value)))


def _parse_points(raw_points, axis_enabled, origin, step_x, step_y, include_solutions):
    """Parse point entries into grid-space tuples `(x, y, label, mode)`."""
    if not isinstance(raw_points, list):
        return []

    parsed = []
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue

        if axis_enabled:
            x = _as_float(item.get("x"))
            y = _as_float(item.get("y"))
            if x is None or y is None or origin is None:
                continue
            gx = origin[0] + (x / step_x)
            gy = origin[1] - (y / step_y)
        else:
            gx = _as_float(item.get("col", item.get("x")))
            gy = _as_float(item.get("row", item.get("y")))
            if gx is None or gy is None:
                continue

        label = str(item.get("label", "")).strip()
        parsed.append((gx, gy, label, mode))

    return parsed


def _parse_pairs(raw_pairs, axis_enabled, origin, step_x, step_y, include_solutions):
    """Parse function value pairs, only when axis mode is enabled."""
    if not axis_enabled or origin is None or not isinstance(raw_pairs, list):
        return []

    parsed = []
    for item in raw_pairs:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue
        x = _as_float(item.get("x"))
        y = _as_float(item.get("y"))
        if x is None or y is None:
            continue
        gx = origin[0] + (x / step_x)
        gy = origin[1] - (y / step_y)
        label = str(item.get("label", "")).strip()
        parsed.append((gx, gy, label, mode))
    return parsed


def _parse_functions(raw_functions, axis_enabled, include_solutions):
    """Parse function descriptors `(expr, x_min, x_max)` for plotting."""
    if not axis_enabled or not isinstance(raw_functions, list):
        return []

    parsed = []
    for item in raw_functions:
        if not isinstance(item, dict):
            continue
        mode = _normalize_show_mode(item.get("show"))
        if not _is_visible(mode, include_solutions):
            continue

        expr = str(item.get("expr", "")).strip()
        if not expr:
            continue

        domain = str(item.get("domain", "")).strip() or "-10:10"
        x_min, x_max = _parse_domain(domain)
        if x_min is None or x_max is None or x_min >= x_max:
            continue

        parsed.append((expr, x_min, x_max, mode))

    return parsed


def _render_axis_ticks_and_labels(
    logical_origin_x,
    logical_origin_y,
    axis_origin_x,
    axis_origin_y,
    cols,
    rows,
    step_x,
    step_y,
):
    """Render axis ticks and value labels for a coordinate grid."""
    tick_markup = []
    x_positions = _iter_axis_tick_positions(logical_origin_x, cols, step_x)
    y_positions = _iter_axis_tick_positions(logical_origin_y, rows, step_y)
    x_label_stride = _choose_axis_label_stride(len(x_positions))
    y_label_stride = _choose_axis_label_stride(len(y_positions))

    for gx, logical_x in x_positions:
        tick_markup.append(
            f"<line class='grid-axis-tick' x1='{gx:.4f}' y1='{axis_origin_y - 0.18:.4f}' x2='{gx:.4f}' y2='{axis_origin_y + 0.18:.4f}' />"
        )
        if _should_render_axis_label(logical_x, x_label_stride) and _is_inside_axis_label_safe_area(
            gx, cols
        ):
            tick_markup.append(
                f"<text class='grid-axis-label' x='{gx:.4f}' y='{axis_origin_y + 0.58:.4f}'>{_format_axis_label(logical_x)}</text>"
            )

    for gy, logical_y in y_positions:
        tick_markup.append(
            f"<line class='grid-axis-tick' x1='{axis_origin_x - 0.18:.4f}' y1='{gy:.4f}' x2='{axis_origin_x + 0.18:.4f}' y2='{gy:.4f}' />"
        )
        if _should_render_axis_label(logical_y, y_label_stride) and _is_inside_axis_label_safe_area(
            gy, rows
        ):
            tick_markup.append(
                f"<text class='grid-axis-label grid-axis-label-y' x='{axis_origin_x - 0.28:.4f}' y='{gy + 0.04:.4f}'>{_format_axis_label(-logical_y)}</text>"
            )

    return tick_markup


def _resolve_axis_name(options, key, aliases=(), default=""):
    """Resolve a textual axis name from options with optional aliases."""
    value = options.get(key)
    if value is None:
        for alias in aliases:
            candidate = options.get(alias)
            if candidate is not None:
                value = candidate
                break
    if value is None:
        return default

    text = str(value).strip()
    return text or default


def _render_axis_arrowheads_and_names(origin_x, origin_y, cols, rows, axis_label_x, axis_label_y):
    """Render arrowheads at positive axis ends and textual axis names."""
    markup = []

    x_tip = float(cols) - 0.02
    x_base = max(origin_x + 0.24, x_tip - 0.44)
    x_top = max(0.04, origin_y - 0.18)
    x_bottom = min(float(rows) - 0.04, origin_y + 0.18)
    if x_base < x_tip:
        markup.append(
            "<polygon class='grid-axis' points='"
            f"{x_tip:.4f},{origin_y:.4f} {x_base:.4f},{x_top:.4f} {x_base:.4f},{x_bottom:.4f}' />"
        )
    if axis_label_x:
        x_name_y = max(0.32, min(float(rows) - 0.12, origin_y - 0.28))
        x_name_x = min(float(cols) - 0.14, x_tip - 0.52)
        markup.append(
            f"<text class='grid-axis-label grid-axis-name' x='{x_name_x:.4f}' y='{x_name_y:.4f}' text-anchor='end'>{escape(axis_label_x)}</text>"
        )

    y_tip = 0.02
    y_base = min(origin_y - 0.24, y_tip + 0.44)
    y_left = max(0.04, origin_x - 0.18)
    y_right = min(float(cols) - 0.04, origin_x + 0.18)
    if y_tip < y_base:
        markup.append(
            "<polygon class='grid-axis' points='"
            f"{origin_x:.4f},{y_tip:.4f} {y_left:.4f},{y_base:.4f} {y_right:.4f},{y_base:.4f}' />"
        )
    if axis_label_y:
        y_name_x = min(float(cols) - 0.14, max(0.20, origin_x + 0.38))
        y_name_y = max(0.34, y_tip + 0.30)
        markup.append(
            f"<text class='grid-axis-label grid-axis-name' x='{y_name_x:.4f}' y='{y_name_y:.4f}'>{escape(axis_label_y)}</text>"
        )

    return markup


def _choose_axis_label_stride(tick_count):
    """Pick a sparse-enough label cadence for readable axis text."""
    max_labels = 12
    if tick_count <= max_labels:
        return 1
    return int(math.ceil(tick_count / max_labels))


def _should_render_axis_label(logical_value, stride):
    """Return True when a tick should receive a textual axis label."""
    if abs(logical_value) < 1e-9:
        return False
    rounded = int(round(logical_value))
    if abs(logical_value - rounded) > 1e-9:
        return False
    return rounded % max(1, stride) == 0


def _is_inside_axis_label_safe_area(position, limit):
    """Allow labels on the full visible axis segment for coordinate correctness."""
    return 0.0 <= float(position) <= float(limit)


def _iter_axis_tick_positions(origin, limit, step_value):
    """Yield visible tick coordinates as `(grid_pos, logical_value)` tuples."""
    ticks = []
    max_ticks = 240

    start_index = int(math.floor((-origin) * step_value))
    end_index = int(math.ceil((limit - origin) * step_value))

    for logical in range(start_index, end_index + 1):
        grid_pos = origin + (logical / step_value)
        if 0.0 <= grid_pos <= float(limit):
            ticks.append((grid_pos, float(logical)))
        if len(ticks) >= max_ticks:
            break

    return ticks


def _format_axis_label(value):
    """Format axis labels with integer preference and compact decimals."""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _parse_domain(domain_text):
    """Parse textual function domain `min:max` to float tuple."""
    normalized = domain_text.replace("..", ":")
    parts = [part.strip() for part in normalized.split(":") if part.strip()]
    if len(parts) != 2:
        return None, None

    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def _sample_function_points(expr, x_min, x_max, origin, step_x, step_y, cols, rows):
    """Sample function graph points and map them to grid coordinates."""
    if origin is None:
        return []

    sample_count = max(24, min(360, int((x_max - x_min) * 24)))
    points = []
    for index in range(sample_count + 1):
        x_value = x_min + ((x_max - x_min) * index / sample_count)
        y_value = _eval_function_expr(expr, x_value)
        if y_value is None or math.isnan(y_value) or math.isinf(y_value):
            continue

        gx = origin[0] + (x_value / step_x)
        gy = origin[1] - (y_value / step_y)
        if _inside_grid(gx, gy, cols, rows):
            points.append((gx, gy))

    return points


def _eval_function_expr(expr, x_value):
    """Safely evaluate a mathematical expression with variable `x`."""
    normalized_expr = (expr or "").replace("^", "**")
    safe_globals = {
        "__builtins__": {},
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log,
        "exp": math.exp,
        "abs": abs,
        "pi": math.pi,
        "e": math.e,
    }

    try:
        tree = ast.parse(normalized_expr, mode="eval")
    except SyntaxError:
        return None

    if not _is_safe_expression_tree(tree):
        return None

    try:
        return float(
            eval(compile(tree, "<grid-function>", "eval"), safe_globals, {"x": x_value})
        )
    except Exception:
        return None


def _is_safe_expression_tree(tree):
    """Validate AST nodes for safe mathematical evaluation."""
    allowed_nodes = {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.Call,
    }
    allowed_names = {"x", "sin", "cos", "tan", "sqrt", "log", "exp", "abs", "pi", "e"}

    for node in ast.walk(tree):
        if type(node) not in allowed_nodes:
            return False
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            return False
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                return False
            if node.func.id not in allowed_names:
                return False
    return True


def _as_float(value):
    """Convert value to float and return `None` on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_positive_float(value, default):
    """Parse a strictly positive float, otherwise return `default`."""
    parsed = _as_float(value)
    if parsed is None or parsed <= 0:
        return default
    return parsed


def _inside_grid(x_value, y_value, cols, rows):
    """Return whether a point lies inside the visible grid area."""
    return 0.0 <= x_value <= float(cols) and 0.0 <= y_value <= float(rows)


def _is_visible(show_value, include_solutions):
    """Evaluate marker-based element visibility (`§`, `%`, `&`)."""
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
