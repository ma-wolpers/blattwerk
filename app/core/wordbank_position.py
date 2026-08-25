"""Shared "word bank beside/above/below main content" layout helper.

Block-type-agnostic: any block that pairs a primary answer area with a
secondary list (a crossword's clue list, a cloze word bank, a wordsearch
word list, ...) can use this instead of hand-rolling its own positioning.
"""

from __future__ import annotations

_KNOWN_POSITIONS = frozenset({"above", "below", "left", "right"})


def normalize_wordbank_position(value, default="below"):
    """Normalizes a `position=`/`layout=` option value to one of
    `"above"`/`"below"`/`"left"`/`"right"`/`"auto"`, or `default` if
    unrecognized."""
    normalized = str(value or "").strip().lower()
    if normalized in {"above", "top", "oben", "ueber", "über"}:
        return "above"
    if normalized in {"below", "bottom", "under", "unten", "unter"}:
        return "below"
    if normalized in {"left", "links"}:
        return "left"
    if normalized in {"right", "rechts"}:
        return "right"
    if normalized == "auto":
        return "auto"
    return default


def resolve_wordbank_auto_position(main_content_width_cm, printable_width_cm, min_side_width_cm=4.0):
    """Resolves `"auto"` to a concrete position: `"right"` if enough
    horizontal space remains beside the main content, else `"below"`.

    Callers compute their own `main_content_width_cm` estimate (a
    crossword's grid width, say) -- this helper stays generic by not
    trying to introspect rendered HTML for that.
    """
    remaining_width_cm = printable_width_cm - main_content_width_cm
    return "right" if remaining_width_cm >= min_side_width_cm else "below"


def wrap_with_wordbank_position(main_html, bank_html, position, extra_classes=()):
    """Wraps `main_html` and `bank_html` in a flex container ordered by
    `position` (`"above"`/`"below"`/`"left"`/`"right"`).

    DOM order is always `main_html` then `bank_html` (screen readers reach
    the primary content first regardless of visual position); the CSS
    classes `.wordbank-position-{position}` control the visual
    left/right/above/below placement via `flex-direction`.
    """
    if not bank_html:
        return main_html
    if not main_html:
        return bank_html

    position = position if position in _KNOWN_POSITIONS else "below"
    classes = " ".join(["wordbank-layout", f"wordbank-position-{position}", *extra_classes])
    return f"<div class='{classes}'>{main_html}{bank_html}</div>"
