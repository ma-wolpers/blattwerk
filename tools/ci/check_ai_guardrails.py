#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GUARDRAIL_RELEVANT_PATHS = {
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/agents/Blattwerker.agent.md",
    ".github/pull_request_template.md",
    "docs/ARCHITEKTUR.md",
    "docs/ARCHITEKTUR_EINFACH.md",
    "docs/AGENT_SETUP.md",
    "docs/DEVELOPMENT_LOG.md",
    "docs/VALIDATOR.md",
    "CHANGELOG.md",
    "tools/ci/check_ai_guardrails.py",
}

BLAETTWERKER_SOLUTION_RULE = (
    "auch eine sichtbare Loesung vorhanden ist"
)


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


def _load_core_block_and_option_catalogs(errors: list[str]) -> tuple[set[str], set[str]]:
    """Read canonical block/option catalogs from validator constants."""
    try:
        from app.core import blatt_validator as validator
    except Exception as exc:  # pragma: no cover - defensive guardrail fallback
        errors.append(f"app/core/blatt_validator.py: import failed for guardrail sync check ({exc})")
        return set(), set()

    core_block_types = {
        str(value).strip()
        for value in getattr(validator, "KNOWN_BLOCK_TYPES", set())
        if isinstance(value, str) and value.strip() and value.strip() != "raw"
    }

    core_option_keys: set[str] = set()
    option_map = getattr(validator, "BLOCK_ALLOWED_OPTIONS", {})
    if isinstance(option_map, dict):
        for values in option_map.values():
            if isinstance(values, set):
                core_option_keys.update(
                    str(value).strip()
                    for value in values
                    if isinstance(value, str) and value.strip()
                )

    return core_block_types, core_option_keys


def _extract_alternatives(regex_text: str, marker: str) -> set[str]:
    """Extract alternatives from a regex fragment like :::(?:a|b|c) or :::(a|b|c)."""
    if not regex_text or marker not in regex_text:
        return set()

    if marker.endswith("(?:"):
        close_token = ")"
    else:
        close_token = ")"

    start = regex_text.find(marker)
    if start < 0:
        return set()
    start += len(marker)
    end = regex_text.find(close_token, start)
    if end < 0:
        return set()

    return {
        token.strip()
        for token in regex_text[start:end].split("|")
        if token.strip()
    }


def _extract_block_types_from_tm_language(rel_path: str, errors: list[str]) -> tuple[set[str], set[str]]:
    """Extract block type alternatives from begin and self-closing grammar regexes."""
    try:
        payload = json.loads(_read(rel_path))
    except Exception as exc:
        errors.append(f"{rel_path}: invalid JSON ({exc})")
        return set(), set()

    begin_set: set[str] = set()
    self_closing_set: set[str] = set()

    for pattern in payload.get("patterns", []):
        if not isinstance(pattern, dict):
            continue
        begin_regex = pattern.get("begin")
        if isinstance(begin_regex, str) and ":::(?:" in begin_regex:
            begin_set = _extract_alternatives(begin_regex, ":::(?:")

        match_regex = pattern.get("match")
        if isinstance(match_regex, str) and ":::(?:" in match_regex:
            self_closing_set = _extract_alternatives(match_regex, ":::(?:")

    if not begin_set:
        errors.append(f"{rel_path}: could not extract block types from begin regex")
    if not self_closing_set:
        errors.append(f"{rel_path}: could not extract block types from self-closing regex")

    return begin_set, self_closing_set


def _extract_option_keys_from_tm_language(rel_path: str, errors: list[str]) -> set[str]:
    """Extract option-key highlighting catalog from tmLanguage option-key regex."""
    try:
        payload = json.loads(_read(rel_path))
    except Exception:
        return set()

    for pattern in payload.get("patterns", []):
        if not isinstance(pattern, dict):
            continue
        inner_patterns = pattern.get("patterns")
        if not isinstance(inner_patterns, list):
            continue
        for inner in inner_patterns:
            if not isinstance(inner, dict):
                continue
            match_regex = inner.get("match")
            if not isinstance(match_regex, str):
                continue

            capture = re.search(r"\\b\(([^)]+)\)\\b\(\?==\)", match_regex)
            if capture:
                return {
                    token.strip()
                    for token in capture.group(1).split("|")
                    if token.strip()
                }

    errors.append(f"{rel_path}: could not extract option-key regex alternatives")
    return set()


def _extract_block_types_from_extension_ts(rel_path: str, errors: list[str]) -> set[str]:
    """Extract block type alternatives from diagnostics hasDirective regex."""
    text = _read(rel_path)
    capture = re.search(r":::\(([^)]+)\)\\b/m", text)
    if not capture:
        errors.append(f"{rel_path}: could not extract hasDirective block type regex")
        return set()

    return {
        token.strip()
        for token in capture.group(1).split("|")
        if token.strip()
    }


def _check_extension_validator_sync(errors: list[str]) -> None:
    """Ensure validator block/option catalogs stay in sync with extension regex catalogs."""
    core_block_types, core_option_keys = _load_core_block_and_option_catalogs(errors)
    if not core_block_types:
        return

    tm_path = "vscode-extension/blattwerk-language/syntaxes/blattwerk-injection.tmLanguage.json"
    ts_path = "vscode-extension/blattwerk-language/src/extension.ts"

    begin_blocks, self_closing_blocks = _extract_block_types_from_tm_language(tm_path, errors)
    ts_blocks = _extract_block_types_from_extension_ts(ts_path, errors)
    tm_option_keys = _extract_option_keys_from_tm_language(tm_path, errors)

    if begin_blocks and self_closing_blocks and begin_blocks != self_closing_blocks:
        errors.append(
            f"{tm_path}: begin/self-closing block catalogs differ -> "
            f"begin-only={sorted(begin_blocks - self_closing_blocks)}, "
            f"self-closing-only={sorted(self_closing_blocks - begin_blocks)}"
        )

    if begin_blocks:
        missing_in_tm = sorted(core_block_types - begin_blocks)
        if missing_in_tm:
            errors.append(
                f"{tm_path}: missing block types from validator catalog -> {missing_in_tm}"
            )

    if ts_blocks:
        missing_in_ts = sorted(core_block_types - ts_blocks)
        if missing_in_ts:
            errors.append(
                f"{ts_path}: missing block types from validator catalog -> {missing_in_ts}"
            )

    if tm_option_keys:
        missing_option_keys = sorted(core_option_keys - tm_option_keys)
        if missing_option_keys:
            errors.append(
                f"{tm_path}: missing option keys from validator BLOCK_ALLOWED_OPTIONS -> {missing_option_keys}"
            )


def _check_blattwerker_solution_rule(errors: list[str]) -> None:
    """Ensure Blattwerker docs keep the worksheet/solution pairing rule."""
    for rel_path in (
        ".github/agents/Blattwerker.agent.md",
        "docs/AGENT_SETUP.md",
    ):
        _require_substring(
            _read(rel_path),
            BLAETTWERKER_SOLUTION_RULE,
            rel_path,
            errors,
        )

    validator_doc = _read("docs/VALIDATOR.md")
    _require_substring(validator_doc, "AN010", "docs/VALIDATOR.md", errors)


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
    _check_extension_validator_sync(errors)
    _check_blattwerker_solution_rule(errors)

    if errors:
        print("AI guardrail check failed:")
        for item in errors:
            print(f" - {item}")
        return 2

    print("AI guardrail check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
