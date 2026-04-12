"""CLI bridge to expose Blattwerk diagnostics as JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app.core.blatt_validator import inspect_markdown_document


def _build_block_index_line_map(text: str) -> dict[int, int]:
    """Approximate 1-based start line for each parsed block index."""
    index_to_line: dict[int, int] = {}
    lines = text.splitlines(keepends=True)

    block_start_pattern = re.compile(r"^:::(\w+)(.*)$")
    self_closing_pattern = re.compile(r"^:::(\w+)(.*?):::$")

    block_index = 0
    block_open_line = None
    raw_buffer_start_line = None
    in_block = False

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_block:
            if self_closing_pattern.match(stripped):
                if raw_buffer_start_line is not None:
                    index_to_line[block_index] = raw_buffer_start_line
                    block_index += 1
                    raw_buffer_start_line = None
                index_to_line[block_index] = line_no
                block_index += 1
                continue

            start_match = block_start_pattern.match(stripped)
            if start_match:
                if raw_buffer_start_line is not None:
                    index_to_line[block_index] = raw_buffer_start_line
                    block_index += 1
                    raw_buffer_start_line = None
                in_block = True
                block_open_line = line_no
                continue

            if raw_buffer_start_line is None:
                raw_buffer_start_line = line_no
            continue

        if stripped == ":::":
            index_to_line[block_index] = block_open_line or line_no
            block_index += 1
            in_block = False
            block_open_line = None

    if in_block:
        index_to_line[block_index] = block_open_line or max(1, len(lines))
        block_index += 1

    if raw_buffer_start_line is not None:
        index_to_line[block_index] = raw_buffer_start_line

    return index_to_line


def _line_range(text: str, line_1_based: int) -> tuple[int, int]:
    lines = text.splitlines()
    if not lines:
        return 0, 0

    line_index = max(1, min(line_1_based, len(lines))) - 1
    line_text = lines[line_index]
    return line_index, len(line_text)


def _diagnostics_json(file_path: Path) -> dict:
    text = file_path.read_text(encoding="utf-8")
    inspected = inspect_markdown_document(file_path)
    index_line_map = _build_block_index_line_map(text)

    diagnostics = []
    for diagnostic in inspected.diagnostics:
        if diagnostic.block_index is None:
            start_line = 1
        else:
            start_line = index_line_map.get(diagnostic.block_index, 1)

        start_line_0, end_char = _line_range(text, start_line)
        diagnostics.append(
            {
                "code": diagnostic.code,
                "message": diagnostic.message,
                "severity": diagnostic.severity,
                "blockIndex": diagnostic.block_index,
                "blockType": diagnostic.block_type,
                "range": {
                    "start": {"line": start_line_0, "character": 0},
                    "end": {"line": start_line_0, "character": end_char},
                },
            }
        )

    return {
        "source": "blattwerk-validator",
        "file": str(file_path),
        "diagnostics": diagnostics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="blattwerk-diagnostics",
        description="Emit Blattwerk validation diagnostics as JSON.",
    )
    parser.add_argument("--file", required=True, help="Path to markdown file")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON for human inspection",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(
            json.dumps(
                {
                    "source": "blattwerk-validator",
                    "file": str(file_path),
                    "diagnostics": [],
                    "error": "file_not_found",
                }
            )
        )
        return 1

    try:
        payload = _diagnostics_json(file_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "source": "blattwerk-validator",
                    "file": str(file_path),
                    "diagnostics": [],
                    "error": str(exc),
                }
            )
        )
        return 2

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
