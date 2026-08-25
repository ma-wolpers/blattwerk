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
_CENTER = _SVG_SIZE / 2
_CENTER_RX, _CENTER_RY = 70, 40
_BRANCH_DISTANCE = 150
_BRANCH_RX, _BRANCH_RY = 55, 32
_MIN_BRANCHES, _MAX_BRANCHES, _DEFAULT_BRANCHES = 2, 12, 6
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


def render_mindmap_block(options, content):
    """Renders a `:::mindmap` block: a central topic with `branches` empty,
    radially arranged boxes for the student's own associations."""
    topic = (content or "").strip()
    if not topic:
        return ""

    options = options or {}
    branches = max(_MIN_BRANCHES, min(_MAX_BRANCHES, _safe_int(options.get("branches"), _DEFAULT_BRANCHES)))
    shape = str(options.get("shape") or "oval").strip().lower()
    if shape not in _KNOWN_SHAPES:
        shape = "oval"

    parts = [f"<svg class='mindmap-svg' viewBox='0 0 {_SVG_SIZE} {_SVG_SIZE}' xmlns='http://www.w3.org/2000/svg'>"]

    for index in range(branches):
        angle = (2 * math.pi * index / branches) - (math.pi / 2)
        bx = _CENTER + _BRANCH_DISTANCE * math.cos(angle)
        by = _CENTER + _BRANCH_DISTANCE * math.sin(angle)
        parts.append(
            f"<line class='mindmap-spoke' x1='{_CENTER:.1f}' y1='{_CENTER:.1f}' x2='{bx:.1f}' y2='{by:.1f}' />"
        )
        parts.append(_render_shape(shape, bx, by, _BRANCH_RX, _BRANCH_RY, "mindmap-branch"))

    parts.append(_render_shape("oval", _CENTER, _CENTER, _CENTER_RX, _CENTER_RY, "mindmap-center"))
    parts.append(
        f"<text x='{_CENTER:.1f}' y='{_CENTER:.1f}' class='mindmap-center-text' "
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
    branches = max(_MIN_BRANCHES, min(_MAX_BRANCHES, _safe_int((options or {}).get("branches"), _DEFAULT_BRANCHES)))
    return 2.0 + (branches * 0.06)
