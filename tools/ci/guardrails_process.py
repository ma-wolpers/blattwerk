"""Prozess-Guardrails: Development-Log-/Changelog-Pflicht fuer gestagte Aenderungen und
die nicht blockierenden Prozess- und Shortcut-Abdeckungs-Warnungen.
"""

from __future__ import annotations

import os

from guardrails_config import (
    CHANGELOG_CODEV_RELEVANT_PATHS,
    CHANGELOG_RELEVANT_PREFIXES,
    PROCESS_GUIDANCE_RULES,
    ROOT,
    SHORTCUT_COVERAGE_SOFT_CHECKS,
)
from guardrails_common import (
    _read,
)


def _check_development_log_updated(staged: set[str], errors: list[str]) -> None:
    normalized = {path.replace("\\", "/") for path in staged}
    if not normalized:
        return

    log_touched = "docs/intern/DEVELOPMENT_LOG.md" in normalized

    requires_log = any(
        path.startswith("app/")
        or path.startswith("bw_libs/")
        or path == ".gitmodules"
        or path == ".github/workflows/quality-guardrails.yml"
        or path == "docs/intern/ARCHITEKTUR.md"
        or path == "docs/intern/ARCHITEKTUR_EINFACH.md"
        for path in normalized
    )

    if requires_log and not log_touched:
        errors.append(
            "docs/intern/DEVELOPMENT_LOG.md missing update: relevant feature/architecture changes require a same-cycle log entry"
        )


def _check_changelog_updated(staged: set[str], errors: list[str]) -> None:
    """Require changelog updates for user- or co-developer-relevant changes."""
    normalized = {path.replace("\\", "/") for path in staged}
    if not normalized:
        return

    if "CHANGELOG.md" in normalized:
        return

    requires_changelog = any(
        path.startswith(prefix) for path in normalized for prefix in CHANGELOG_RELEVANT_PREFIXES
    ) or any(path in CHANGELOG_CODEV_RELEVANT_PATHS for path in normalized)

    if requires_changelog:
        errors.append(
            "CHANGELOG.md missing update: user- or co-developer-relevant changes require a changelog entry"
        )


def _collect_process_guidance_warnings() -> list[str]:
    """Collect non-blocking warnings for process guidance consistency."""
    warnings: list[str] = []
    sources = {
        "AGENTS.md": _read("AGENTS.md"),
        ".github/copilot-instructions.md": _read(".github/copilot-instructions.md"),
        ".github/pull_request_template.md": _read(".github/pull_request_template.md"),
    }

    for label, needle in PROCESS_GUIDANCE_RULES.items():
        if not any(needle in text for text in sources.values()):
            warnings.append(
                f"process-guidance ({label}) not found in governance docs/templates"
            )
    return warnings


def _has_any_marker(rel_paths: tuple[str, ...], markers: tuple[str, ...]) -> bool:
    """Return whether any marker appears in at least one existing source file."""

    for rel_path in rel_paths:
        path = ROOT / rel_path
        if not path.exists():
            continue
        text = _read(rel_path)
        if any(marker in text for marker in markers):
            return True
    return False


def _collect_shortcut_coverage_warnings() -> list[str]:
    """Collect non-blocking warnings when key intents miss keyboard shortcut markers."""

    warnings: list[str] = []
    for check in SHORTCUT_COVERAGE_SOFT_CHECKS:
        intent_paths = tuple(check["intent_paths"])
        intent_markers = tuple(check["intent_markers"])
        shortcut_paths = tuple(check["shortcut_paths"])
        shortcut_markers = tuple(check["shortcut_markers"])
        if not _has_any_marker(intent_paths, intent_markers):
            continue
        if _has_any_marker(shortcut_paths, shortcut_markers):
            continue
        warnings.append(
            f"shortcut-coverage ({check['label']}): intent marker found without configured keyboard binding marker"
        )
    return warnings


def _is_ci_environment() -> bool:
    """Return whether the check runs in a CI environment."""
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


