"""CLI bridge to expose Blattwerk diagnostics as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_document
from app.core.blatt_kern_shared import build_block_index_line_map


def _line_range(text: str, line_1_based: int) -> tuple[int, int]:
    lines = text.splitlines()
    if not lines:
        return 0, 0

    line_index = max(1, min(line_1_based, len(lines))) - 1
    line_text = lines[line_index]
    return line_index, len(line_text)


def _is_blocking_mode(diagnostics, mode: str) -> bool:
    if mode == "strict":
        return bool(diagnostics)
    if mode == "permissive":
        return any(diagnostic.severity == "error" for diagnostic in diagnostics)
    return has_blocking_diagnostics(diagnostics)


def _diagnostics_json(file_path: Path, mode: str) -> dict:
    text = file_path.read_text(encoding="utf-8")
    inspected = inspect_markdown_document(file_path)
    index_line_map = build_block_index_line_map(text)

    diagnostics = []
    for diagnostic in inspected.diagnostics:
        if diagnostic.line_number is not None:
            start_line = diagnostic.line_number
        elif diagnostic.block_index is None:
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
        "mode": mode,
        "blocking": _is_blocking_mode(inspected.diagnostics, mode),
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
    parser.add_argument(
        "--mode",
        choices=("standard", "strict", "permissive"),
        default="standard",
        help=(
            "Validation mode: standard blocks critical diagnostics, strict blocks any "
            "diagnostic, permissive blocks only severity=error"
        ),
    )
    parser.add_argument(
        "--fail-on-blocking",
        action="store_true",
        help="Return exit code 3 when the selected mode marks diagnostics as blocking",
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
        payload = _diagnostics_json(file_path, args.mode)
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

    if args.fail_on_blocking and payload.get("blocking"):
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
