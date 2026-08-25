"""Self-assessment/reflection-scale block renderer -- open-ended (no answer).

Reuses `mc`'s glyph-based option rendering *idea* (a row of selectable
symbols), but with no "correct" one -- there is no worksheet/solution
divergence, so this is dispatched directly like `material`/`info`, not
through `_render_answer_block()` (see `answer_special_mindmap.py`'s
module docstring for the same rationale in more detail).
"""

from __future__ import annotations

from html import escape

from .answer_special_shared import (
    _new_markdown_converter,
    _option_is_enabled,
    _safe_int,
    convert_markdown_with_math,
    parse_bullet_list_lines,
)

_MIN_STEPS, _MAX_STEPS, _DEFAULT_STEPS = 2, 7, 3
_KNOWN_SCALES = frozenset({"smiley", "ampel", "sterne", "zahlen"})

_SCALE_GLYPH_PRESETS = {
    "smiley": {
        3: ("\U0001F61F", "\U0001F610", "\U0001F642"),  # worried, neutral, slight smile
        5: ("\U0001F61F", "\U0001F641", "\U0001F610", "\U0001F642", "\U0001F604"),
    },
    "ampel": {
        3: ("\U0001F534", "\U0001F7E1", "\U0001F7E2"),  # red, yellow, green
    },
}


def _resolve_scale_glyphs(scale, steps):
    """Returns `steps` glyph strings for `scale`, one per selectable step.

    Falls back to plain numbered circles when no curated glyph set exists
    for this exact `(scale, steps)` combination (e.g. `smiley` with
    `steps=4`) -- always renders *something* usable rather than requiring
    an exhaustive preset table.
    """
    preset = _SCALE_GLYPH_PRESETS.get(scale)
    if preset and steps in preset:
        return list(preset[steps])
    if scale == "sterne":
        return ["☆"] * steps  # unfilled star, differentiated by position only
    return [str(step) for step in range(1, steps + 1)]


def render_selfcheck_block(options, content):
    """Renders a `:::selfcheck` block: one row per statement, each with a
    `steps`-wide scale of selectable symbols and no marked "correct" one.

    `dual=true` renders **two** independent instances of the same scale per
    row (e.g. a self-assessment and a teacher-assessment column, or an
    earlier/later self-assessment -- the two use cases the option was
    requested for) instead of picking one fixed pair of labels. `label1`/
    `label2` optionally caption the two columns via a header row; without
    either set (the default), the two columns render unlabeled.
    """
    statements = parse_bullet_list_lines(content)
    if not statements:
        return ""

    options = options or {}
    scale = str(options.get("scale") or "smiley").strip().lower()
    if scale not in _KNOWN_SCALES:
        scale = "smiley"
    steps = max(_MIN_STEPS, min(_MAX_STEPS, _safe_int(options.get("steps"), _DEFAULT_STEPS)))
    glyphs = _resolve_scale_glyphs(scale, steps)
    glyphs_html = "".join(f"<span class='selfcheck-glyph'>{escape(glyph)}</span>" for glyph in glyphs)

    dual = _option_is_enabled(options.get("dual"), default=False)
    single_scale_html = f"<span class='selfcheck-scale'>{glyphs_html}</span>"
    if dual:
        scale_html = f"<span class='selfcheck-scale-group'>{single_scale_html}{single_scale_html}</span>"
    else:
        scale_html = single_scale_html

    header_html = ""
    if dual:
        label1 = str(options.get("label1") or "").strip()
        label2 = str(options.get("label2") or "").strip()
        if label1 or label2:
            header_html = (
                "<div class='selfcheck-header-row'>"
                "<span class='selfcheck-statement'></span>"
                "<span class='selfcheck-scale-group'>"
                f"<span class='selfcheck-scale-label'>{escape(label1)}</span>"
                f"<span class='selfcheck-scale-label'>{escape(label2)}</span>"
                "</span>"
                "</div>"
            )

    md = _new_markdown_converter()
    rows = []
    for statement in statements:
        statement_html = convert_markdown_with_math(md, statement).strip()
        rows.append(
            "<div class='selfcheck-row'>"
            f"<span class='selfcheck-statement'>{statement_html}</span>"
            f"{scale_html}"
            "</div>"
        )

    return f"<div class='selfcheck-block'>{header_html}{''.join(rows)}</div>"
