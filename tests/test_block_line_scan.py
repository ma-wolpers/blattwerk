"""`scan_block_lines`: Zeilenrollen und Blöcke nach den Regeln des Parsers (nur synthetische Texte)."""

from __future__ import annotations

from app.core.blatt_kern_shared import parse_blocks
from app.core.block_line_scan import LineKind, scan_block_lines


def _kinds(text, **kwargs):
    return [line.kind for line in scan_block_lines(text, **kwargs).lines]


def test_flat_block_with_self_closing_header_and_prose():
    scan = scan_block_lines("Text\n:::task points=2\nInhalt\n:::\n:::pagebreak :::")
    assert _kinds("Text\n:::task points=2\nInhalt\n:::\n:::pagebreak :::") == [
        LineKind.OUTSIDE, LineKind.OPEN, LineKind.CONTENT, LineKind.CLOSE, LineKind.SELF_CLOSING,
    ]
    (span,) = scan.spans
    assert (span.open_line, span.close_line, span.block_type, span.options_text) == (2, 4, "task", "points=2")
    assert [line.header_type for line in scan.headers] == ["task", "pagebreak"]
    assert scan.span_at(3) is span and scan.span_at(1) is None and scan.span_at(5) is None


def test_header_inside_block_is_content_for_the_parser_and_flagged_as_nested():
    text = ":::task\nA\n:::subtask\nB\n:::\n:::"
    assert _kinds(text) == [
        LineKind.OPEN, LineKind.CONTENT, LineKind.NESTED_OPEN, LineKind.CONTENT, LineKind.CLOSE, LineKind.STRAY_CLOSE,
    ]
    # Same structure as the parser: one task block, the subtask header is its content.
    assert [block_type for block_type, _options, _content in parse_blocks(text) if block_type != "raw"] == ["task"]


def test_closing_marker_with_text_is_malformed_not_a_close():
    scan = scan_block_lines(":::info\nA\n::: x\nB\n:::")
    assert [line.kind for line in scan.lines][2] is LineKind.MALFORMED
    assert scan.spans[0].close_line == 5


def test_unclosed_block_reaches_the_end():
    scan = scan_block_lines("Text\n:::info\nA")
    assert scan.spans[0].close_line is None
    assert scan.span_at(3) is scan.spans[0]
    assert scan.spans[0].contains(3, scan.last_line)


def test_frontmatter_is_skipped_and_a_later_rule_is_not_frontmatter():
    text = "---\nTitel: :::task\n---\n:::info\nA\n:::\n---\nB"
    scan = scan_block_lines(text)
    assert [line.kind for line in scan.lines][:3] == [LineKind.FRONTMATTER] * 3
    assert list(scan.frontmatter_lines) == [1, 2, 3]
    assert scan.line(7).kind is LineKind.OUTSIDE


def test_content_after_frontmatter_with_base_line():
    scan = scan_block_lines("---\n:::info\n:::", base_line=5, detect_frontmatter=False)
    assert [line.number for line in scan.lines] == [5, 6, 7]
    assert scan.line(5).kind is LineKind.OUTSIDE
    assert (scan.spans[0].open_line, scan.spans[0].close_line) == (6, 7)


def test_lines_split_only_at_newline_like_tk():
    scan = scan_block_lines("a\x0bb\n:::info\n:::")
    assert len(scan.lines) == 3
    assert scan.spans[0].open_line == 2
