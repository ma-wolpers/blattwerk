"""Ordering/Reihenfolge answer renderer.

The author writes items in their correct order; the worksheet shows them
shuffled with an empty rank box next to each, and the solution shows the
same shuffled order with the correct rank filled in -- so a teacher can
match item-by-item against what's actually printed on the worksheet.
"""

from __future__ import annotations

import random
import re
from html import escape

from .answer_special_shared import _new_markdown_converter, normalize_markdown
from .blatt_kern_shared_blocks import _alpha_label

_BULLET_LINE_RE = re.compile(r"^[-*+]\s+(.*)$")


def parse_ordering_items(content):
    """Parses bullet-list items in their author-given (correct) order."""
    items = []
    for raw_line in (content or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        bullet_match = _BULLET_LINE_RE.match(stripped)
        text = bullet_match.group(1).strip() if bullet_match else stripped
        if text:
            items.append(text)
    return items


def _shuffle_ranked_items(ranked_items):
    """Deterministically shuffles `(rank, item)` pairs, seeded from the
    original item texts, avoiding the identity permutation when more than
    one distinct order exists. Shuffling the `(rank, item)` pairs together
    (rather than shuffling item text and looking rank up afterwards) keeps
    duplicate item texts correctly paired with their own rank."""
    if len(ranked_items) <= 1:
        return list(ranked_items)

    seed = "|".join(item for _rank, item in ranked_items)
    rng = random.Random(seed)
    shuffled = list(ranked_items)
    original = list(ranked_items)
    for _ in range(8):
        rng.shuffle(shuffled)
        if shuffled != original:
            return shuffled
    return original[1:] + original[:1]


def _format_rank_label(rank_number, numbering_mode):
    if numbering_mode == "letters":
        return _alpha_label(rank_number)
    return str(rank_number)


def render_ordering_answer(options, content, include_solutions):
    """Renders a `:::ordering` block: shuffled items with rank boxes."""
    items = parse_ordering_items(content)
    if not items:
        return ""

    numbering_mode = str((options or {}).get("numbering") or "numeric").strip().lower()
    if numbering_mode not in {"numeric", "letters"}:
        numbering_mode = "numeric"

    ranked_items = list(enumerate(items, start=1))
    shuffled = _shuffle_ranked_items(ranked_items)

    md = _new_markdown_converter()
    rows_html = []
    for rank, item in shuffled:
        box_classes = ["ordering-rank-box"]
        rank_label = ""
        if include_solutions:
            rank_label = _format_rank_label(rank, numbering_mode)
            box_classes.append("ordering-rank-filled")
        item_html = md.convert(normalize_markdown(item)).strip()
        rows_html.append(
            "<div class='ordering-item'>"
            f"<span class='{' '.join(box_classes)}'>{escape(rank_label)}</span>"
            f"<span class='ordering-label'>{item_html}</span>"
            "</div>"
        )

    return f"<div class='answer ordering-answer'>{''.join(rows_html)}</div>"


def estimate_ordering_weight(options, content):
    """Estimates layout weight from item count, mirroring the shape/clamping
    used by other list-based answer blocks (e.g. `estimate_wordsearch_weight`)."""
    items = parse_ordering_items(content)
    if not items:
        return 0.0
    return max(1.0, min(6.0, 0.6 + len(items) * 0.45))
