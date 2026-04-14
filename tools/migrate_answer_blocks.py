"""Migrate legacy :::answer type=... block headers to dedicated block types.

Examples:
- :::answer type=grid rows=4        -> :::grid rows=4
- :::answer type=space:::           -> :::space:::

Default scope rewrites markdown/docs and python test fixtures in this repository.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re


CANONICAL_ANSWER_TYPES = {
    "lines",
    "grid",
    "dots",
    "space",
    "table",
    "numberline",
    "mc",
    "cloze",
    "matching",
    "wordsearch",
}

DEFAULT_PATHS = (
    "examples",
    "tests",
    "docs",
)

DEFAULT_SUFFIXES = {".md", ".txt"}

_SELF_CLOSING_PATTERN = re.compile(r":::answer(?P<opts>[^\n]*?):::")
_OPENING_PATTERN = re.compile(r":::answer(?P<opts>[^\n]*)")
_TYPE_TOKEN_PATTERN = re.compile(r"(^|\s)type=(?P<value>\"[^\"]*\"|'[^']*'|[^\s]+)")


@dataclass(frozen=True)
class RewriteIssue:
    file_path: Path
    snippet: str
    reason: str


def _parse_type_and_rest(options_raw: str) -> tuple[str | None, str, str | None]:
    """Return (type, remaining-options-raw, error reason)."""
    text = (options_raw or "").strip()
    if not text:
        return None, "", "missing options"

    type_match = _TYPE_TOKEN_PATTERN.search(text)
    if not type_match:
        return None, text, "missing type option"

    raw_type_value = (type_match.group("value") or "").strip()
    answer_type = raw_type_value.strip('"\'').lower()
    if not answer_type:
        return None, text, "missing type option"

    # Preserve original quoting/spacing for all non-type options.
    remaining = _TYPE_TOKEN_PATTERN.sub(" ", text, count=1)
    remaining = re.sub(r"\s+", " ", remaining).strip()

    if answer_type not in CANONICAL_ANSWER_TYPES:
        return None, remaining, f"unsupported answer type `{answer_type}`"

    return answer_type, remaining, None


def _build_new_header(answer_type: str, remaining_options_raw: str, *, self_closing: bool) -> str:
    header = f":::{answer_type}"
    if remaining_options_raw:
        header += " " + remaining_options_raw
    if self_closing:
        header += ":::"
    return header


def _replace_matches(
    text: str,
    pattern: re.Pattern[str],
    *,
    self_closing: bool,
    file_path: Path,
    issues: list[RewriteIssue],
) -> tuple[str, int]:
    changes = 0

    def _replacement(match: re.Match[str]) -> str:
        nonlocal changes
        original = match.group(0)
        options_raw = match.group("opts") or ""
        answer_type, remaining_options_raw, error = _parse_type_and_rest(options_raw)
        if error:
            issues.append(
                RewriteIssue(file_path=file_path, snippet=original.strip(), reason=error)
            )
            return original

        changes += 1
        return _build_new_header(
            answer_type,
            remaining_options_raw,
            self_closing=self_closing,
        )

    updated = pattern.sub(_replacement, text)
    return updated, changes


def rewrite_content(text: str, file_path: Path) -> tuple[str, int, list[RewriteIssue]]:
    issues: list[RewriteIssue] = []

    # First rewrite explicit self-closing occurrences, then normal opening headers.
    updated, count_self_closing = _replace_matches(
        text,
        _SELF_CLOSING_PATTERN,
        self_closing=True,
        file_path=file_path,
        issues=issues,
    )
    updated, count_opening = _replace_matches(
        updated,
        _OPENING_PATTERN,
        self_closing=False,
        file_path=file_path,
        issues=issues,
    )
    return updated, (count_self_closing + count_opening), issues


def iter_candidate_files(root: Path, relative_paths: list[str], suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for relative in relative_paths:
        base = (root / relative).resolve()
        if not base.exists():
            continue
        if base.is_file():
            if base.suffix.lower() in suffixes:
                files.append(base)
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                files.append(path)
    return sorted(set(files))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current working directory).",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=list(DEFAULT_PATHS),
        help="Relative paths to scan (default: examples tests docs).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes to disk. Without this flag, only dry-run report is printed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    files = iter_candidate_files(root, list(args.paths), DEFAULT_SUFFIXES)

    changed_files = 0
    changed_headers = 0
    issue_list: list[RewriteIssue] = []

    for file_path in files:
        original = file_path.read_text(encoding="utf-8")
        updated, replacements, issues = rewrite_content(original, file_path)
        issue_list.extend(issues)

        if replacements <= 0:
            continue

        changed_files += 1
        changed_headers += replacements
        if args.write and updated != original:
            file_path.write_text(updated, encoding="utf-8")

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"[{mode}] files scanned: {len(files)}")
    print(f"[{mode}] files changed: {changed_files}")
    print(f"[{mode}] headers rewritten: {changed_headers}")

    if issue_list:
        print(f"[{mode}] manual review required: {len(issue_list)}")
        for issue in issue_list[:50]:
            relative = issue.file_path.relative_to(root)
            print(f"  - {relative}: {issue.reason} | {issue.snippet}")
        remaining = len(issue_list) - 50
        if remaining > 0:
            print(f"  ... and {remaining} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
