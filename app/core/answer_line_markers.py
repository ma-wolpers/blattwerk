"""Inline token parsing for answer-block content visibility."""

from __future__ import annotations

import re

from .blatt_kern_shared import _new_markdown_converter, normalize_markdown


MARKER_SHOW_MODE = {
    "§": "worksheet",
    "%": "solution",
    "&": "both",
}

MARKER_TOKEN_PATTERN = "§%&"
_ESCAPED_SPACE_TOKEN = "\ufff0"


def _new_segment(text, show_mode):
    return {
        "text": text,
        "show": show_mode,
    }


def _decode_escaped_space_tokens(text, html=False):
    if not text:
        return text

    replacement = "&nbsp;" if html else " "
    return text.replace(_ESCAPED_SPACE_TOKEN, replacement)


def _extract_leading_line_marker(line):
    """Return ``(marker, remaining_line)`` when line starts with legacy marker token."""
    match = re.match(rf"^\s*([{MARKER_TOKEN_PATTERN}])(?=\s|$)(.*)$", line)
    if not match:
        return None, line

    marker = match.group(1)
    remainder = match.group(2).lstrip()
    return marker, remainder


def _extract_trailing_line_marker(line):
    """Return ``(marker, remaining_line)`` when line ends with legacy marker token."""
    match = re.match(rf"^(.*?)(?:\s+|^)([{MARKER_TOKEN_PATTERN}])\s*$", line)
    if not match:
        return None, line

    remainder = match.group(1).rstrip()
    marker = match.group(2)
    return marker, remainder


def parse_answer_line_visibility(raw_line, default_show="both"):
    """Parse one line with legacy line markers and optional inline visibility tokens."""
    line = "" if raw_line is None else str(raw_line)

    # Legacy syntax support: `§ text` or `text %` controls full-line visibility.
    leading_marker, after_leading = _extract_leading_line_marker(line)
    trailing_marker, after_trailing = _extract_trailing_line_marker(after_leading)

    selected_line_marker = leading_marker or trailing_marker
    has_conflict = leading_marker is not None and trailing_marker is not None
    line_default_show = MARKER_SHOW_MODE.get(selected_line_marker, default_show)

    line = after_trailing
    segments = []
    plain_buffer = []
    index = 0

    while index < len(line):
        char = line[index]

        if char == "\\" and index + 1 < len(line):
            escaped_char = line[index + 1]
            if escaped_char == " ":
                plain_buffer.append(_ESCAPED_SPACE_TOKEN)
            else:
                plain_buffer.append(escaped_char)
            index += 2
            continue

        is_marker_start = (
            char in MARKER_SHOW_MODE
            and index + 1 < len(line)
            and line[index + 1] == "{"
        )
        if is_marker_start:
            if plain_buffer:
                segments.append(_new_segment("".join(plain_buffer), line_default_show))
                plain_buffer = []

            marker_char = char
            marker_buffer = []
            index += 2
            closed = False

            while index < len(line):
                marker_char_current = line[index]
                if marker_char_current == "\\" and index + 1 < len(line):
                    escaped_char = line[index + 1]
                    if escaped_char == " ":
                        marker_buffer.append(_ESCAPED_SPACE_TOKEN)
                    else:
                        marker_buffer.append(escaped_char)
                    index += 2
                    continue
                if marker_char_current == "}":
                    closed = True
                    index += 1
                    break
                marker_buffer.append(marker_char_current)
                index += 1

            if not closed:
                plain_buffer.append(f"{marker_char}{{{''.join(marker_buffer)}")
                has_conflict = True
                break

            segments.append(
                _new_segment("".join(marker_buffer), MARKER_SHOW_MODE[marker_char])
            )
            continue

        plain_buffer.append(char)
        index += 1

    if plain_buffer:
        segments.append(_new_segment("".join(plain_buffer), line_default_show))

    visible_text = "".join(segment["text"] for segment in segments)
    return {
        "text": visible_text,
        "show": line_default_show,
        "segments": segments,
        "has_conflict": has_conflict,
    }


def _line_visible_in_mode(show_mode, include_solutions):
    mode = "solution" if include_solutions else "worksheet"
    return show_mode == "both" or show_mode == mode


def _render_inline_markdown_fragment(text):
    """Render a short markdown fragment without wrapping `<p>` tags."""
    raw = "" if text is None else str(text)
    if raw == "":
        return ""

    leading_spaces = len(raw) - len(raw.lstrip(" "))
    trailing_spaces = len(raw) - len(raw.rstrip(" "))
    core = raw.strip(" ")

    if core == "":
        return " "

    md = _new_markdown_converter()
    html = md.convert(normalize_markdown(core)).strip()
    paragraph_match = re.fullmatch(r"<p>(.*)</p>", html, flags=re.DOTALL)
    rendered = html
    if paragraph_match:
        rendered = paragraph_match.group(1)

    with_ascii_spaces = (" " * leading_spaces) + rendered + (" " * trailing_spaces)
    return _decode_escaped_space_tokens(with_ascii_spaces, html=True)


def _looks_like_block_html(fragment_html):
    """Return true when the fragment starts with a block-level HTML tag."""
    if not fragment_html:
        return False

    stripped = fragment_html.lstrip()
    return bool(
        re.match(
            r"^<(?:ul|ol|li|p|div|blockquote|table|pre|h[1-6])(?:\s|>)",
            stripped,
            flags=re.IGNORECASE,
        )
    )


def _wrap_solution_fragment(fragment_html):
    """Wrap colored solution fragments with valid inline/block containers."""
    if _looks_like_block_html(fragment_html):
        return f"<div class='table-solution-marker'>{fragment_html}</div>"
    return f"<span class='table-solution-marker'>{fragment_html}</span>"


def _visible_segments_for_line(segments, include_solutions):
    return [
        segment
        for segment in segments
        if _line_visible_in_mode(segment["show"], include_solutions)
    ]


def _render_visible_segments_for_line(
    segments,
    include_solutions,
    highlight_solution_segments,
):
    rendered = []
    for segment in segments:
        if not _line_visible_in_mode(segment["show"], include_solutions):
            continue

        fragment_html = _render_inline_markdown_fragment(segment["text"])
        if not fragment_html:
            continue

        if (
            include_solutions
            and highlight_solution_segments
            and segment["show"] == "solution"
        ):
            rendered.append(_wrap_solution_fragment(fragment_html))
        else:
            rendered.append(fragment_html)
    return "".join(rendered)


def filter_answer_content_for_mode(content, include_solutions, default_show="both"):
    """Filter answer content lines to the target output mode."""
    if not (content or ""):
        return ""

    selected_lines = []
    for raw_line in str(content).splitlines():
        if not raw_line.strip():
            selected_lines.append("")
            continue

        parsed = parse_answer_line_visibility(raw_line, default_show=default_show)
        visible_line = "".join(
            segment["text"]
            for segment in _visible_segments_for_line(
                parsed["segments"], include_solutions
            )
        )
        if visible_line.strip():
            selected_lines.append(_decode_escaped_space_tokens(visible_line))

    return "\n".join(selected_lines).strip()


def render_answer_content_html_for_mode(
    content,
    include_solutions,
    default_show="both",
    highlight_solution_segments=True,
):
    """Render visible answer content as HTML with line breaks preserved."""
    if not (content or ""):
        return ""

    html_lines = render_answer_line_html_fragments_for_mode(
        content,
        include_solutions=include_solutions,
        default_show=default_show,
        highlight_solution_segments=highlight_solution_segments,
    )
    return "<br>".join(html_lines).strip()


def render_answer_line_html_fragments_for_mode(
    content,
    include_solutions,
    default_show="both",
    highlight_solution_segments=True,
):
    """Render visible answer lines as per-line HTML fragments."""
    if not (content or ""):
        return []

    html_lines = []
    for raw_line in str(content).splitlines():
        parsed = parse_answer_line_visibility(raw_line, default_show=default_show)
        visible_segments = _visible_segments_for_line(
            parsed["segments"],
            include_solutions,
        )
        visible_line_text = "".join(segment["text"] for segment in visible_segments)
        if not visible_line_text.strip():
            continue

        rendered_line = _render_visible_segments_for_line(
            visible_segments,
            include_solutions,
            highlight_solution_segments,
        )
        html_lines.append(rendered_line)

    return html_lines


def render_answer_line_rows_html_for_mode(
    content,
    include_solutions,
    default_show="both",
    highlight_solution_segments=True,
):
    """Render visible answer lines as dedicated row containers for overlays."""
    html_lines = render_answer_line_html_fragments_for_mode(
        content,
        include_solutions=include_solutions,
        default_show=default_show,
        highlight_solution_segments=highlight_solution_segments,
    )
    row_markup = "".join(
        f"<div class='answer-line-row'>{line_html}</div>" for line_html in html_lines
    )
    return row_markup, len(html_lines)


def count_visible_answer_lines(content, include_solutions, default_show="both"):
    """Count non-empty visible lines for the selected output mode."""
    if not (content or ""):
        return 0

    count = 0
    for raw_line in str(content).splitlines():
        parsed = parse_answer_line_visibility(raw_line, default_show=default_show)
        visible_line = "".join(
            segment["text"]
            for segment in _visible_segments_for_line(
                parsed["segments"], include_solutions
            )
        )
        if visible_line.strip():
            count += 1
    return count


def collect_answer_marker_conflict_lines(content):
    """Return 1-based line numbers with malformed inline token syntax."""
    if not (content or ""):
        return []

    conflict_lines = []
    for line_number, raw_line in enumerate(str(content).splitlines(), start=1):
        if not raw_line.strip():
            continue
        parsed = parse_answer_line_visibility(raw_line)
        if parsed["has_conflict"]:
            conflict_lines.append(line_number)

    return conflict_lines


def is_effectively_empty_answer_content(content):
    """Return true when answer content has no non-empty text after marker parsing."""
    if not (content or ""):
        return True

    for raw_line in str(content).splitlines():
        parsed = parse_answer_line_visibility(raw_line, default_show="both")
        if parsed["text"].strip():
            return False

    return True
