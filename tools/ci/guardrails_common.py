"""Gemeinsame Helfer der AI-Guardrails: Git-Abfragen, Dateilesen, Substring-Pruefungen
und die Datei-Iteratoren fuer die GUI-Contract-Scans.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from guardrails_config import (
    FUTURE_GUI_ENTRY_FILE_NAMES,
    FUTURE_GUI_SEARCH_ROOTS,
    GUARDRAIL_RELEVANT_PATHS,
    GUI_CONTRACT_SCAN_ROOTS,
    ROOT,
    UI_BASECLASS_MODULE_ALIASES,
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
        normalized = staged_path.replace("\\", "/")
        if normalized in normalized_relevant or _is_future_gui_entry_path(normalized) or _is_repo_gui_python_path(normalized):
            return True
    return False


def _staged_added_lines(repo_root: Path, rel_path: str) -> list[str]:
    """Return the lines a staged change adds to ``rel_path`` (without the leading ``+``).

    Used to read the newly staged DEVELOPMENT_LOG entry, e.g. for the changelog
    opt-out marker. Returns ``[]`` if git fails or nothing is staged for the file.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0", "--", rel_path],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except Exception:
        return []
    return [
        line[1:]
        for line in result.stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _read(rel_path: str) -> str:
    path = ROOT / rel_path
    if not path.exists():
        raise RuntimeError(f"Missing required file: {rel_path}")
    return path.read_text(encoding="utf-8")


def _require_substring(text: str, needle: str, source: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"{source}: missing required text -> {needle}")


def _forbid_substring(text: str, needle: str, source: str, errors: list[str]) -> None:
    if needle in text:
        errors.append(f"{source}: forbidden fallback text present -> {needle}")


def _is_future_gui_entry_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    file_name = normalized.rsplit("/", 1)[-1]
    if file_name not in FUTURE_GUI_ENTRY_FILE_NAMES:
        return False
    return any(normalized.startswith(f"{root}/") for root in FUTURE_GUI_SEARCH_ROOTS)


def _iter_future_gui_entry_candidates() -> list[str]:
    candidates: set[str] = set()
    for rel_root in FUTURE_GUI_SEARCH_ROOTS:
        root_path = ROOT / rel_root
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*.py"):
            if file_path.name not in FUTURE_GUI_ENTRY_FILE_NAMES:
                continue
            candidates.add(file_path.relative_to(ROOT).as_posix())
    return sorted(candidates)


def _is_repo_gui_python_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    if not normalized.endswith(".py"):
        return False
    return any(normalized.startswith(f"{root}/") for root in GUI_CONTRACT_SCAN_ROOTS)


def _iter_repo_gui_python_files() -> list[str]:
    files: set[str] = set()
    for rel_root in GUI_CONTRACT_SCAN_ROOTS:
        root_path = ROOT / rel_root
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*.py"):
            files.add(file_path.relative_to(ROOT).as_posix())
    return sorted(files)


def _iter_python_files_under(rel_roots: tuple[str, ...]) -> list[str]:
    files: set[str] = set()
    for rel_root in rel_roots:
        root_path = ROOT / rel_root
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*.py"):
            files.add(file_path.relative_to(ROOT).as_posix())
    return sorted(files)


def _contains_direct_tkinter_import(module: ast.Module) -> bool:
    for node in module.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "tkinter" or name.startswith("tkinter.") or name == "ttk":
                    return True
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if (
                module_name == "tkinter"
                or module_name.startswith("tkinter.")
                or module_name == "ttk"
            ):
                return True
    return False


def _local_ui_bases(class_node: ast.ClassDef) -> list[str]:
    bases: list[str] = []
    for base in class_node.bases:
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
            if base.value.id in UI_BASECLASS_MODULE_ALIASES:
                bases.append(ast.unparse(base))
    return bases


