#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GUARDRAIL_RELEVANT_PATHS = {
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/pull_request_template.md",
    "docs/ARCHITEKTUR.md",
    "docs/ARCHITEKTUR_EINFACH.md",
    "docs/DEVELOPMENT_LOG.md",
    "CHANGELOG.md",
    "tools/ci/check_ai_guardrails.py",
}


def _repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except Exception:
        return ROOT


def _staged_files(repo_root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            line.strip().replace("\\", "/")
            for line in result.stdout.splitlines()
            if line.strip()
        }
    except Exception:
        return set()


def _has_relevant_staged_changes(staged: set[str], repo_root: Path) -> bool:
    try:
        root_rel_to_repo = str(ROOT.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        root_rel_to_repo = ""

    normalized_relevant: set[str] = set()
    for rel in GUARDRAIL_RELEVANT_PATHS:
        rel_norm = rel.replace("\\", "/")
        normalized_relevant.add(rel_norm)
        if root_rel_to_repo not in {"", "."}:
            normalized_relevant.add(f"{root_rel_to_repo}/{rel_norm}")

    for staged_path in staged:
        if staged_path.replace("\\", "/") in normalized_relevant:
            return True
    return False


def _read(rel_path: str) -> str:
    path = ROOT / rel_path
    if not path.exists():
        raise RuntimeError(f"Missing required file: {rel_path}")
    return path.read_text(encoding="utf-8")


def _require_substring(text: str, needle: str, source: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"{source}: missing required text -> {needle}")


def _check_development_log_updated(staged: set[str], errors: list[str]) -> None:
    normalized = {path.replace("\\", "/") for path in staged}
    if not normalized:
        return

    log_touched = "docs/DEVELOPMENT_LOG.md" in normalized

    requires_log = any(
        path.startswith("app/")
        or path == "docs/ARCHITEKTUR.md"
        or path == "docs/ARCHITEKTUR_EINFACH.md"
        for path in normalized
    )

    if requires_log and not log_touched:
        errors.append(
            "docs/DEVELOPMENT_LOG.md missing update: relevant feature/architecture changes require a same-cycle log entry"
        )


def _check_marker_token_consistency(errors: list[str]) -> None:
    """Ensure marker docs/highlighting stay aligned with core §/%/& token set."""
    target_files = (
        "app/ui/blatt_ui_editor.py",
        "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json",
        "docs/NUTZERHANDBUCH.md",
    )

    outdated_patterns = ("[§$&]", "§/$/&")
    for rel_path in target_files:
        text = _read(rel_path)
        for pattern in outdated_patterns:
            if pattern in text:
                errors.append(
                    f"{rel_path}: outdated marker token notation detected ({pattern}); expected §/%/&"
                )


def main() -> int:
    repo_root = _repo_root()
    staged = _staged_files(repo_root)
    if staged and not _has_relevant_staged_changes(staged, repo_root):
        print("AI guardrail check skipped (no guardrail-relevant staged files).")
        return 0

    errors: list[str] = []

    _read("AGENTS.md")
    _read(".github/copilot-instructions.md")
    _read("CHANGELOG.md")
    _read("docs/DEVELOPMENT_LOG.md")

    arch_doc = _read("docs/ARCHITEKTUR.md")
    _require_substring(
        arch_doc,
        "beschreiben nur den aktuellen Architekturzustand",
        "docs/ARCHITEKTUR.md",
        errors,
    )
    _require_substring(
        arch_doc,
        "docs/DEVELOPMENT_LOG.md",
        "docs/ARCHITEKTUR.md",
        errors,
    )

    arch_simple_doc = _read("docs/ARCHITEKTUR_EINFACH.md")
    _require_substring(
        arch_simple_doc,
        "zeigen nur den aktuellen Zustand",
        "docs/ARCHITEKTUR_EINFACH.md",
        errors,
    )
    _require_substring(
        arch_simple_doc,
        "docs/DEVELOPMENT_LOG.md",
        "docs/ARCHITEKTUR_EINFACH.md",
        errors,
    )

    _check_development_log_updated(staged, errors)
    _check_marker_token_consistency(errors)

    if errors:
        print("AI guardrail check failed:")
        for item in errors:
            print(f" - {item}")
        return 2

    print("AI guardrail check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
