#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GUARDRAIL_RELEVANT_PATHS = {
    ".gitmodules",
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/agents/Blattwerker.agent.md",
    ".github/pull_request_template.md",
    ".github/workflows/quality-guardrails.yml",
    "docs/ARCHITEKTUR.md",
    "docs/ARCHITEKTUR_EINFACH.md",
    "docs/AGENT_SETUP.md",
    "docs/DEVELOPMENT_LOG.md",
    "docs/GUI_MIGRATION_BACKLOG.md",
    "docs/VALIDATOR.md",
    "CHANGELOG.md",
    "tools/ci/check_ai_guardrails.py",
    "app/ui/blatt_ui_style.py",
    "app/ui/export_dialog.py",
    "bw_libs/ui_contract/keybinding.py",
    "bw_libs/ui_contract/popup.py",
    "bw_libs/ui_contract/hsm.py",
    "bw_libs/ui_contract/laufkern.py",
    "bw_libs/app_paths.py",
}
FUTURE_GUI_SEARCH_ROOTS = (
    "app/ui",
)
FUTURE_GUI_ENTRY_FILE_NAMES = {
    "main_window.py",
    "ui.py",
    "blatt_ui.py",
    "screen_builder.py",
}
FUTURE_GUI_ENTRY_BASELINES: set[str] = set()
FUTURE_GUI_REQUIRED_SHARED_SNIPPETS = (
    "ensure_bw_gui_on_path()",
    "from bw_gui.runtime import",
    "from bw_gui.menu import",
    "open_tabbed_settings_dialog",
    "compose_hover_text",
    "HoverTooltip",
)
GUI_CONTRACT_SCAN_ROOTS = (*FUTURE_GUI_SEARCH_ROOTS, "bw_libs")
UI_BASECLASS_MODULE_ALIASES = {"ui", "widgets", "tui"}
LEGACY_UI_BASECLASS_ALLOWLIST: set[str] = set()
SHARED_PRIMITIVE_CLASS_NAMES = {"TkRootHost", "ScrollablePopupWindow", "WrappedTextField"}
SHARED_PRIMITIVE_CLASS_ALLOWLIST: set[str] = set()
GUI_MIGRATION_BACKLOG_PATH = "docs/GUI_MIGRATION_BACKLOG.md"

BLAETTWERKER_SOLUTION_RULE = (
    "auch eine sichtbare Loesung vorhanden ist"
)
PROCESS_GUIDANCE_RULES = {
    "feature_commit": "Feature-Aenderungen werden in eigenstaendigen Commits",
    "manual_push": "Push erfolgt manuell",
}
SHORTCUT_COVERAGE_SOFT_CHECKS = (
    {
        "label": "global-export",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_EXPORT", "global.export"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_EXPORT",),
    },
    {
        "label": "global-help-preview",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_HELP_PREVIEW", "global.help_preview"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_HELP_PREVIEW",),
    },
    {
        "label": "global-new-file",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_NEW_FILE", "global.new_file"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_NEW_FILE",),
    },
    {
        "label": "global-save-as",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_SAVE_AS", "global.save_as"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_SAVE_AS",),
    },
    {
        "label": "global-settings",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_SETTINGS", "global.settings"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_SETTINGS", "<Control-comma>"),
    },
    {
        "label": "global-debug-overlay",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_DEBUG_OVERLAY", "global.debug_overlay"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_DEBUG_OVERLAY",),
    },
    {
        "label": "global-escape",
        "intent_paths": ("app/ui/ui_intents.py",),
        "intent_markers": ("GLOBAL_ESCAPE", "global.escape"),
        "shortcut_paths": ("app/ui/blatt_shortcuts.py",),
        "shortcut_markers": ("UiIntent.GLOBAL_ESCAPE", "<Escape>"),
    },
)
CHANGELOG_RELEVANT_PREFIXES = (
    "app/ui/",
    "app/core/",
    "bw_libs/",
)
CHANGELOG_CODEV_RELEVANT_PATHS = {
    ".gitmodules",
    ".github/workflows/quality-guardrails.yml",
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/pull_request_template.md",
    "tools/ci/check_ai_guardrails.py",
    "docs/GUI_MIGRATION_BACKLOG.md",
    "bw_libs/ui_contract/keybinding.py",
    "bw_libs/ui_contract/popup.py",
    "bw_libs/ui_contract/hsm.py",
    "bw_libs/ui_contract/laufkern.py",
    "bw_libs/app_paths.py",
}
LAUFKERN_BRIDGE_PATH = "bw_libs/ui_contract/laufkern.py"
LAUFKERN_FALLBACK_SCAN_ROOTS = ("app", "bw_libs")

DOWNSTREAM_MOD_SUBMODULE_NAME = "kurzentwerfer"
DOWNSTREAM_MOD_SUBMODULE_PATH = "kurzentwerfer"
DOWNSTREAM_MOD_SUBMODULE_URL = "https://github.com/ma-wolpers/kurzentwerfer.git"
DOWNSTREAM_BW_GUI_URL = "https://github.com/ma-wolpers/bw-gui"


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


def _check_development_log_updated(staged: set[str], errors: list[str]) -> None:
    normalized = {path.replace("\\", "/") for path in staged}
    if not normalized:
        return

    log_touched = "docs/DEVELOPMENT_LOG.md" in normalized

    requires_log = any(
        path.startswith("app/")
        or path.startswith("bw_libs/")
        or path == ".gitmodules"
        or path == ".github/workflows/quality-guardrails.yml"
        or path == "docs/ARCHITEKTUR.md"
        or path == "docs/ARCHITEKTUR_EINFACH.md"
        for path in normalized
    )

    if requires_log and not log_touched:
        errors.append(
            "docs/DEVELOPMENT_LOG.md missing update: relevant feature/architecture changes require a same-cycle log entry"
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


def _check_shared_ui_contract_hardening(errors: list[str]) -> None:
    """Require shared menu/shortcut contracts in Blattwerk UI modules."""

    style_module = _read("app/ui/blatt_ui_style.py")
    for snippet in (
        "from bw_gui.menu import CustomMenuBar as SharedCustomMenuBar",
        "def _build_custom_menu_strip(self):",
        "self._shared_menu_bar = SharedCustomMenuBar(",
    ):
        _require_substring(style_module, snippet, "app/ui/blatt_ui_style.py", errors)

    for snippet in (
        "except ModuleNotFoundError",
        "if SharedCustomMenuBar is None",
    ):
        _forbid_substring(style_module, snippet, "app/ui/blatt_ui_style.py", errors)

    export_module = _read("app/ui/export_dialog.py")
    for snippet in (
        "from bw_gui.shortcuts import compose_hover_text as compose_shared_hover_text",
        "merged = compose_shared_hover_text(desc, sequence)",
    ):
        _require_substring(export_module, snippet, "app/ui/export_dialog.py", errors)

    _forbid_substring(export_module, "except ModuleNotFoundError", "app/ui/export_dialog.py", errors)


def _check_future_gui_entry_contracts(errors: list[str]) -> None:
    """Require shared GUI bootstrap contracts for newly added entrypoint files."""

    for rel_path in _iter_future_gui_entry_candidates():
        if rel_path in FUTURE_GUI_ENTRY_BASELINES:
            continue

        text = _read(rel_path)
        for snippet in FUTURE_GUI_REQUIRED_SHARED_SNIPPETS:
            _require_substring(text, snippet, rel_path, errors)

        _forbid_substring(text, "import tkinter", rel_path, errors)
        _forbid_substring(text, "from tkinter import", rel_path, errors)


def _check_repo_wide_gui_contracts(errors: list[str]) -> None:
    """Enforce repo-wide GUI contract: no direct tkinter imports and no new local widget bases."""

    for rel_path in _iter_repo_gui_python_files():
        try:
            source = _read(rel_path).lstrip("\ufeff")
            module = ast.parse(source, filename=rel_path)
        except Exception as exc:
            errors.append(f"{rel_path}: failed to parse Python AST -> {exc}")
            continue

        if _contains_direct_tkinter_import(module):
            errors.append(
                f"{rel_path}: direct tkinter/ttk import is forbidden; use bw_gui.runtime and shared bw_gui modules"
            )

        for node in ast.walk(module):
            if not isinstance(node, ast.ClassDef):
                continue

            if node.name in SHARED_PRIMITIVE_CLASS_NAMES:
                marker = f"{rel_path}:{node.name}"
                if marker not in SHARED_PRIMITIVE_CLASS_ALLOWLIST:
                    errors.append(
                        f"{rel_path}:{node.lineno} class '{node.name}' redefines a reserved shared primitive; "
                        "import it from bw_gui.runtime/dialogs/widgets instead"
                    )

            bases = _local_ui_bases(node)
            if not bases:
                continue
            marker = f"{rel_path}:{node.name}"
            if marker in LEGACY_UI_BASECLASS_ALLOWLIST:
                continue
            errors.append(
                f"{rel_path}:{node.lineno} class '{node.name}' uses local UI base {bases}; "
                "move reusable widget implementation to bw-gui"
            )


def _check_gui_migration_backlog(errors: list[str]) -> None:
    """Require explicit backlog tracking for all active GUI exemption baselines/allowlists."""

    backlog = _read(GUI_MIGRATION_BACKLOG_PATH)
    _require_substring(backlog, "## Active Exemptions", GUI_MIGRATION_BACKLOG_PATH, errors)
    _require_substring(backlog, "remove_by:", GUI_MIGRATION_BACKLOG_PATH, errors)

    for rel_path in sorted(FUTURE_GUI_ENTRY_BASELINES):
        _require_substring(backlog, f"- {rel_path}", GUI_MIGRATION_BACKLOG_PATH, errors)

    for marker in sorted(LEGACY_UI_BASECLASS_ALLOWLIST):
        _require_substring(backlog, f"- {marker}", GUI_MIGRATION_BACKLOG_PATH, errors)


def _check_laufkern_fallback_sunset(errors: list[str]) -> None:
    """Wave-3 sunset gate: no ModuleNotFoundError fallback branches remain."""

    for rel_path in _iter_python_files_under(LAUFKERN_FALLBACK_SCAN_ROOTS):
        if "except ModuleNotFoundError" in _read(rel_path):
            errors.append(
                f"{rel_path}: ModuleNotFoundError fallback is forbidden in Wave-3; require shared imports without local fallback branches"
            )


def _check_ui_contract_bridge_decommission(errors: list[str]) -> None:
    """Phase-I decommission gate: ui_contract bridges stay thin shared re-export shims."""

    required_imports = {
        "bw_libs/ui_contract/keybinding.py": "from bw_gui.contracts.keybinding import",
        "bw_libs/ui_contract/popup.py": "from bw_gui.contracts.popup import",
        "bw_libs/ui_contract/hsm.py": "from bw_gui.contracts.hsm import",
        "bw_libs/ui_contract/laufkern.py": "from bw_gui.laufkern import",
    }
    forbidden_local_markers = {
        "bw_libs/ui_contract/keybinding.py": ("class KeyBindingDefinition", "class KeybindingRegistry"),
        "bw_libs/ui_contract/popup.py": ("class PopupPolicy", "class PopupPolicyRegistry"),
        "bw_libs/ui_contract/hsm.py": ("class HsmContract", "def build_ui_hsm_contract"),
        "bw_libs/ui_contract/laufkern.py": ("class LaufKernManifest", "def aggregate_completion("),
    }

    for rel_path, import_marker in required_imports.items():
        source = _read(rel_path).lstrip("\ufeff")
        _require_substring(source, "ensure_bw_gui_on_path", rel_path, errors)
        _require_substring(source, import_marker, rel_path, errors)
        for forbidden in forbidden_local_markers[rel_path]:
            _forbid_substring(source, forbidden, rel_path, errors)


def _check_downstream_mod_integration(errors: list[str]) -> None:
    """Validate downstream Kurzentwerfer submodule integration contracts."""

    gitmodules = _read(".gitmodules")
    section_marker = f"[submodule \"{DOWNSTREAM_MOD_SUBMODULE_NAME}\"]"
    if section_marker not in gitmodules:
        return

    _require_substring(
        gitmodules,
        f"path = {DOWNSTREAM_MOD_SUBMODULE_PATH}",
        ".gitmodules",
        errors,
    )
    _require_substring(
        gitmodules,
        f"url = {DOWNSTREAM_MOD_SUBMODULE_URL}",
        ".gitmodules",
        errors,
    )
    _require_substring(gitmodules, "branch = main", ".gitmodules", errors)

    downstream_required_files = (
        f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/.gitmodules",
        f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/tools/ci/check_ai_guardrails.py",
        f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/app/core/model.py",
        f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/app/core/validator.py",
    )

    for rel_path in downstream_required_files:
        if not (ROOT / rel_path).exists():
            errors.append(
                f"{rel_path}: missing required downstream integration file (run submodule init/update and keep phase-3 CI files in sync)"
            )

    kze_guardrail_rel = f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/tools/ci/check_ai_guardrails.py"
    if (ROOT / kze_guardrail_rel).exists():
        kze_guardrail = _read(kze_guardrail_rel)
        _require_substring(kze_guardrail, "FORBIDDEN_MARKERS", kze_guardrail_rel, errors)
        _require_substring(kze_guardrail, "KZF010", kze_guardrail_rel, errors)

    kze_model_rel = f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/app/core/model.py"
    if (ROOT / kze_model_rel).exists():
        _require_substring(
            _read(kze_model_rel),
            "FORBIDDEN_BLATTWERK_MARKERS",
            kze_model_rel,
            errors,
        )

    kze_validator_rel = f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/app/core/validator.py"
    if (ROOT / kze_validator_rel).exists():
        _require_substring(_read(kze_validator_rel), "KZF010", kze_validator_rel, errors)


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


def _collect_downstream_mod_warnings() -> list[str]:
    """Collect non-blocking warnings for staged downstream rollout alignment."""

    warnings: list[str] = []
    gitmodules = _read(".gitmodules")
    section_marker = f"[submodule \"{DOWNSTREAM_MOD_SUBMODULE_NAME}\"]"
    if section_marker not in gitmodules:
        return warnings

    kze_gitmodules_rel = f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/.gitmodules"
    if not (ROOT / kze_gitmodules_rel).exists():
        warnings.append(
            f"downstream-mod: {kze_gitmodules_rel} missing in workspace (did you run git submodule update --init --recursive?)"
        )
    else:
        kze_gitmodules = _read(kze_gitmodules_rel)
        if f"url = {DOWNSTREAM_BW_GUI_URL}" not in kze_gitmodules:
            warnings.append(
                "downstream-mod: kurzentwerfer submodule still references non-GitHub bw-gui URL; align to GitHub remote for CI portability"
            )

    kze_ci_rel = f"{DOWNSTREAM_MOD_SUBMODULE_PATH}/.github/workflows/quality-guardrails.yml"
    if not (ROOT / kze_ci_rel).exists():
        warnings.append(
            f"downstream-mod: {kze_ci_rel} not found; kurzentwerfer CI gate appears not yet available on tracked submodule commit"
        )

    return warnings


def _is_ci_environment() -> bool:
    """Return whether the check runs in a CI environment."""
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


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
    _read("bw_libs/ui_contract/keybinding.py")
    _read("bw_libs/ui_contract/popup.py")
    _read("bw_libs/ui_contract/hsm.py")
    _read("bw_libs/ui_contract/laufkern.py")
    _read("bw_libs/app_paths.py")

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
    _check_changelog_updated(staged, errors)
    _check_marker_token_consistency(errors)
    _check_extension_validator_sync(errors)
    _check_blattwerker_solution_rule(errors)
    _check_shared_ui_contract_hardening(errors)
    _check_laufkern_fallback_sunset(errors)
    _check_ui_contract_bridge_decommission(errors)
    _check_downstream_mod_integration(errors)
    _check_future_gui_entry_contracts(errors)
    _check_repo_wide_gui_contracts(errors)
    _check_gui_migration_backlog(errors)
    warnings = _collect_process_guidance_warnings()
    warnings.extend(_collect_shortcut_coverage_warnings())
    warnings.extend(_collect_downstream_mod_warnings())

    if errors:
        print("AI guardrail check failed:")
        for item in errors:
            print(f" - {item}")
        return 2

    if warnings and not _is_ci_environment():
        print("AI guardrail process warnings (non-blocking):")
        for item in warnings:
            print(f" - {item}")

    print("AI guardrail check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
