"""Zahlenstrahl: Skalierung -- Breite, Strichabstand, automatische Schrittweite und
Haupt-Striche aus den Block-Optionen bestimmen.
"""

from __future__ import annotations

import math
from .answer_special_shared import _option_is_enabled
from .answer_numberline_values import (
    _css_length_to_mm,
    _parse_css_size,
    _parse_numberline_positive_float,
)


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
