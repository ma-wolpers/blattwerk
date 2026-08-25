"""Framed free-writing block renderer -- open-ended (no answer).

Reuses the `lines` block's ruled-line generation (`<div class='line'></div>`
repeated `lines` times) inside a decoratively framed box. No worksheet/
solution divergence, so dispatched directly like `material`/`info` --
see `answer_special_mindmap.py`'s module docstring for the full rationale.
"""

from __future__ import annotations

from .answer_special_shared import _new_markdown_converter, _safe_int, normalize_markdown

_DEFAULT_LINES = 5
_MIN_LINES, _MAX_LINES = 1, 20
_KNOWN_STYLES = frozenset({"bubble", "cloud", "frame", "letter"})


def render_writebox_block(options, content):
    """Renders a `:::writebox` block: an optional prompt plus a decoratively
    framed area of ruled lines for open writing."""
    options = options or {}
    style = str(options.get("style") or "frame").strip().lower()
    if style not in _KNOWN_STYLES:
        style = "frame"

    line_count = _safe_int(options.get("lines"), 0)
    if line_count <= 0:
        line_count = _DEFAULT_LINES
    line_count = max(_MIN_LINES, min(_MAX_LINES, line_count))

    prompt = (content or "").strip()
    prompt_html = ""
    if prompt:
        md = _new_markdown_converter()
        prompt_html = f"<div class='writebox-prompt'>{md.convert(normalize_markdown(prompt)).strip()}</div>"

    lines_html = "".join("<div class='line'></div>" for _ in range(line_count))

    return (
        f"<div class='writebox-block writebox-style-{style}'>"
        f"{prompt_html}"
        f"<div class='writebox-lines'>{lines_html}</div>"
        "</div>"
    )


def estimate_writebox_weight(options, content):
    """Estimates layout weight for a writebox's ruled-lines area.

    The generic text-length heuristic would badly underestimate this
    block: its rendered height comes from the `lines` option, not from
    the (often short or entirely absent) prompt text.
    """
    line_count = _safe_int((options or {}).get("lines"), 0)
    if line_count <= 0:
        line_count = _DEFAULT_LINES
    line_count = max(_MIN_LINES, min(_MAX_LINES, line_count))

    prompt_length = len((content or "").strip())
    return max(0.8, line_count * 0.7) + (prompt_length / 200.0)
