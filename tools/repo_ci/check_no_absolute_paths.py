#!/usr/bin/env python3
"""Fail CI when persisted JSON files contain absolute filesystem paths."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Persisted JSON files in these locations are expected to stay portable.
TRACKED_JSON_GLOBS = (
    "app/storage/.state/*.json",
    ".blattwerk*.json",
)

RELEVANT_PATH_PREFIXES = (
    "app/storage/.state/",
    ".blattwerk",
)

RELEVANT_EXACT_PATHS = {
    "tools/repo_ci/check_no_absolute_paths.py",
    ".github/workflows/repo-path-guardrails.yml",
}

_WINDOWS_ABSOLUTE_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_UNC_RE = re.compile(r"^[\\/]{2}[^\\/]+[\\/][^\\/]+")
_POSIX_ABSOLUTE_RE = re.compile(r"^/")


def _run_git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout


def _paths_from_git_stdout(stdout: str | None) -> set[str]:
    if not stdout:
        return set()
    return {
        line.strip().replace("\\", "/")
        for line in stdout.splitlines()
        if line.strip()
    }


def _staged_files() -> set[str]:
    return _paths_from_git_stdout(_run_git(["diff", "--cached", "--name-only"]))


def _ci_changed_files() -> set[str]:
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        return set()

    base_ref = (os.getenv("GITHUB_BASE_REF") or "").strip()
    if base_ref:
        _run_git(["fetch", "--no-tags", "--depth=1", "origin", base_ref])
        return _paths_from_git_stdout(
            _run_git(["diff", "--name-only", f"origin/{base_ref}...HEAD"])
        )

    before_sha = (os.getenv("GITHUB_EVENT_BEFORE") or "").strip()
    if before_sha and before_sha != "0000000000000000000000000000000000000000":
        return _paths_from_git_stdout(
            _run_git(["diff", "--name-only", f"{before_sha}...HEAD"])
        )

    return set()


def _changed_paths_for_relevance() -> set[str]:
    staged = _staged_files()
    if staged:
        return staged
    return _ci_changed_files()


def _has_relevant_changes(paths: set[str]) -> bool:
    if not paths:
        return True

    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in RELEVANT_EXACT_PATHS:
            return True
        if any(normalized.startswith(prefix) for prefix in RELEVANT_PATH_PREFIXES):
            return True
    return False


def _tracked_files_for_glob(pattern: str) -> list[str]:
    output = _run_git(["ls-files", pattern])
    if output is None:
        return []

    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def _iter_json_leaf_strings(value, dotted_path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{dotted_path}.{key}"
            yield from _iter_json_leaf_strings(child, child_path)
        return

    if isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{dotted_path}[{index}]"
            yield from _iter_json_leaf_strings(child, child_path)
        return

    if isinstance(value, str):
        yield dotted_path, value


def _looks_like_absolute_path(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith(("http://", "https://", "data:", "mailto:")):
        return False

    return bool(
        _WINDOWS_ABSOLUTE_RE.match(stripped)
        or _UNC_RE.match(stripped)
        or _POSIX_ABSOLUTE_RE.match(stripped)
    )


def _validate_file(rel_path: str) -> list[str]:
    path = ROOT / rel_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{rel_path}: invalid json ({exc})"]

    violations: list[str] = []
    for dotted_path, text in _iter_json_leaf_strings(payload):
        if not _looks_like_absolute_path(text):
            continue
        violations.append(
            f"{rel_path}: absolute path at {dotted_path} -> {text}"
        )
    return violations


def main() -> int:
    changed_paths = _changed_paths_for_relevance()
    if not _has_relevant_changes(changed_paths):
        print("Path guardrail check skipped (no guardrail-relevant changed files).")
        return 0

    files: set[str] = set()
    for pattern in TRACKED_JSON_GLOBS:
        files.update(_tracked_files_for_glob(pattern))

    if not files:
        print("No tracked persisted JSON files found for path guardrail check.")
        return 0

    errors: list[str] = []
    for rel_path in sorted(files):
        errors.extend(_validate_file(rel_path))

    if errors:
        print("Absolute persisted JSON paths are not allowed:")
        for item in errors:
            print(f" - {item}")
        return 1

    print("Persisted JSON path guardrail passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
