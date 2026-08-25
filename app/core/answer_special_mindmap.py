"""Mindmap/cluster block renderer -- radial SVG diagram, open-ended (no answer).

Not part of `ANSWER_BLOCK_TYPES`/`answer_special.py`'s re-export surface: it
has no worksheet/solution divergence (there is no "correct" set of branches
to reveal), so it is dispatched directly from `blatt_kern_task_render.py`
like `material`/`info`, not through `_render_answer_block()`.
"""

from __future__ import annotations

import math
from html import escape

from .answer_special_shared import _safe_int

_SVG_SIZE = 420
_SVG_SIZE_WITH_SUBBRANCHES = 560
"""Larger canvas used whenever `subbranches > 0` -- the extra tier of
shapes reaches further out from the center than the default single-tier
canvas has room for; the default `_SVG_SIZE` stays untouched so a plain
`:::mindmap` (the common case) renders byte-identically to before."""
_CENTER_RX, _CENTER_RY = 70, 40
_BRANCH_DISTANCE = 150
_BRANCH_RX, _BRANCH_RY = 55, 32
_SUBBRANCH_DISTANCE = 70
_SUBBRANCH_RX, _SUBBRANCH_RY = 30, 18
_SUBBRANCH_FAN_DEGREES = 70
_MIN_BRANCHES, _MAX_BRANCHES, _DEFAULT_BRANCHES = 2, 12, 6
_MIN_SUBBRANCHES, _MAX_SUBBRANCHES, _DEFAULT_SUBBRANCHES = 0, 4, 0
_KNOWN_SHAPES = frozenset({"oval", "rect", "cloud"})


def _render_shape(shape, cx, cy, rx, ry, css_class):
    if shape == "rect":
        x, y = cx - rx, cy - ry
        return f"<rect class='{css_class}' x='{x:.1f}' y='{y:.1f}' width='{2 * rx:.1f}' height='{2 * ry:.1f}' rx='8' />"
    if shape == "cloud":
        # A precise scalloped cloud outline isn't worth the complexity here --
        # a cluster of overlapping ellipses reads as "cloud-ish" at a glance,
        # which is all this decorative option needs to achieve.
        bumps = [
            (cx - rx * 0.5, cy, rx * 0.55, ry * 0.75),
            (cx, cy - ry * 0.3, rx * 0.65, ry * 0.85),
            (cx + rx * 0.5, cy, rx * 0.55, ry * 0.75),
            (cx, cy + ry * 0.2, rx * 0.95, ry * 0.65),
        ]
        ellipses = "".join(
            f"<ellipse cx='{bx:.1f}' cy='{by:.1f}' rx='{brx:.1f}' ry='{bry:.1f}' />"
            for bx, by, brx, bry in bumps
        )
        return f"<g class='{css_class}'>{ellipses}</g>"
    return f"<ellipse class='{css_class}' cx='{cx:.1f}' cy='{cy:.1f}' rx='{rx:.1f}' ry='{ry:.1f}' />"


def _subbranch_angle_offsets(count):
    """Returns `count` angular offsets (radians), fanned symmetrically
    around a main branch's own direction, used to place its sub-branches.
    A single sub-branch sits directly in line with its parent branch;
    two or more spread evenly across `_SUBBRANCH_FAN_DEGREES`."""
    if count <= 0:
        return []
    if count == 1:
        return [0.0]
    spread = math.radians(_SUBBRANCH_FAN_DEGREES)
    step = spread / (count - 1)
    return [-spread / 2 + i * step for i in range(count)]


def render_mindmap_block(options, content):
    """Renders a `:::mindmap` block: a central topic with `branches` empty,
    radially arranged boxes for the student's own associations, and
    optionally a further `subbranches` fan of smaller boxes off each
    branch (opt-in via `subbranches=`, default `0`/off -- a mindmap
    without sub-branches is still a common, valid single-tier "word web"
    shape, so the richer two-tier look is not forced on every author)."""
    topic = (content or "").strip()
    if not topic:
        return ""

    options = options or {}
    branches = max(_MIN_BRANCHES, min(_MAX_BRANCHES, _safe_int(options.get("branches"), _DEFAULT_BRANCHES)))
    subbranches = max(
        _MIN_SUBBRANCHES, min(_MAX_SUBBRANCHES, _safe_int(options.get("subbranches"), _DEFAULT_SUBBRANCHES))
    )
    shape = str(options.get("shape") or "oval").strip().lower()
    if shape not in _KNOWN_SHAPES:
        shape = "oval"

    svg_size = _SVG_SIZE_WITH_SUBBRANCHES if subbranches > 0 else _SVG_SIZE
    center = svg_size / 2
    subbranch_offsets = _subbranch_angle_offsets(subbranches)

    parts = [f"<svg class='mindmap-svg' viewBox='0 0 {svg_size} {svg_size}' xmlns='http://www.w3.org/2000/svg'>"]

    for index in range(branches):
        angle = (2 * math.pi * index / branches) - (math.pi / 2)
        bx = center + _BRANCH_DISTANCE * math.cos(angle)
        by = center + _BRANCH_DISTANCE * math.sin(angle)
        parts.append(
            f"<line class='mindmap-spoke' x1='{center:.1f}' y1='{center:.1f}' x2='{bx:.1f}' y2='{by:.1f}' />"
        )
        parts.append(_render_shape(shape, bx, by, _BRANCH_RX, _BRANCH_RY, "mindmap-branch"))

        for offset in subbranch_offsets:
            sub_angle = angle + offset
            sx = bx + _SUBBRANCH_DISTANCE * math.cos(sub_angle)
            sy = by + _SUBBRANCH_DISTANCE * math.sin(sub_angle)
            parts.append(
                f"<line class='mindmap-subspoke' x1='{bx:.1f}' y1='{by:.1f}' x2='{sx:.1f}' y2='{sy:.1f}' />"
            )
            parts.append(_render_shape(shape, sx, sy, _SUBBRANCH_RX, _SUBBRANCH_RY, "mindmap-subbranch"))

    parts.append(_render_shape("oval", center, center, _CENTER_RX, _CENTER_RY, "mindmap-center"))
    parts.append(
        f"<text x='{center:.1f}' y='{center:.1f}' class='mindmap-center-text' "
        f"text-anchor='middle' dominant-baseline='middle'>{escape(topic)}</text>"
    )
    parts.append("</svg>")

    return f"<div class='mindmap-block'>{''.join(parts)}</div>"


def estimate_mindmap_weight(options, content):
    """Estimates layout weight for a mindmap's roughly square SVG diagram.

    The generic text-length heuristic in `estimate_block_weight` would
    badly underestimate this block: its rendered footprint comes from a
    fixed-size radial diagram, not from the (often just a few words long)
    topic string that is its only text content.
    """
    topic = (content or "").strip()
    if not topic:
        return 0.0
    options = options or {}
    branches = max(_MIN_BRANCHES, min(_MAX_BRANCHES, _safe_int(options.get("branches"), _DEFAULT_BRANCHES)))
    subbranches = max(
        _MIN_SUBBRANCHES, min(_MAX_SUBBRANCHES, _safe_int(options.get("subbranches"), _DEFAULT_SUBBRANCHES))
    )
    weight = 2.0 + (branches * 0.06)
    if subbranches > 0:
        weight += branches * subbranches * 0.03
    return weight
