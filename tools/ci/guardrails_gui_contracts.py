"""GUI-Contract-Guardrails: Blattwerker-Loesungsregel, Shared-UI-Vertrag, GUI-Einstiegs-
und Repo-weite bw-gui-Vertraege, Migrations-Backlog, Laufkern-Sunset und Bridge-Abbau.
"""

from __future__ import annotations

import ast
import re

from guardrails_config import (
    BLAETTWERKER_SOLUTION_RULE,
    FUTURE_GUI_ENTRY_BASELINES,
    FUTURE_GUI_REQUIRED_SHARED_SNIPPETS,
    GUI_MIGRATION_BACKLOG_PATH,
    LAUFKERN_FALLBACK_SCAN_ROOTS,
    LEGACY_UI_BASECLASS_ALLOWLIST,
    SHARED_PRIMITIVE_CLASS_ALLOWLIST,
    SHARED_PRIMITIVE_CLASS_NAMES,
)
from guardrails_common import (
    _contains_direct_tkinter_import,
    _forbid_substring,
    _iter_future_gui_entry_candidates,
    _iter_python_files_under,
    _iter_repo_gui_python_files,
    _local_ui_bases,
    _read,
    _require_substring,
)


def _check_blattwerker_solution_rule(errors: list[str]) -> None:
    """Ensure Blattwerker docs keep the worksheet/solution pairing rule."""
    for rel_path in (
        ".github/agents/Blattwerker.agent.md",
        "docs/intern/AGENT_SETUP.md",
    ):
        _require_substring(
            _read(rel_path),
            BLAETTWERKER_SOLUTION_RULE,
            rel_path,
            errors,
        )

    validator_doc = _read("docs/nutzer/VALIDATOR.md")
    _require_substring(validator_doc, "AN010", "docs/nutzer/VALIDATOR.md", errors)


def _check_shared_ui_contract_hardening(errors: list[str]) -> None:
    """Require shared menu/shortcut contracts in Blattwerk UI modules.

    Der Menu-Vertrag lebt tatsaechlich in `app/ui/blatt_ui_base.py`:
    `BlattwerkAppBase` erbt von `bw_gui.runtime.BwBaseWindow` und
    ueberschreibt `build_menu()`, das `bw_gui.menu.section_spec(...)`-
    Eintraege liefert -- `BwBaseWindow` instanziiert die geteilte
    `CustomMenuBar` bereits selbst. Dieser Check prueft rein textuell
    gegen diese Datei (kein `bw_gui`-Import, keine Abhaengigkeit vom
    Schwester-Repo `bw-gui`), analog zu allen anderen Checks hier.
    """

    base_module = _read("app/ui/blatt_ui_base.py")
    for snippet in (
        "from bw_gui.runtime import BwBaseWindow",
        "from bw_gui.menu import section_spec",
        "def build_menu(self) -> list:",
    ):
        _require_substring(base_module, snippet, "app/ui/blatt_ui_base.py", errors)
    # Seit dem UI-Split erbt `BlattwerkAppBase` zusaetzlich von Mixins; Vertrag ist
    # nur, dass `BwBaseWindow` (als letzte Basis) in der Klassendefinition steht.
    if not re.search(r"^class BlattwerkAppBase\([^)]*\bBwBaseWindow\s*,?\s*\):", base_module, re.MULTILINE):
        errors.append(
            "app/ui/blatt_ui_base.py: missing required text -> class BlattwerkAppBase(... BwBaseWindow):"
        )

    # Der Hover-Text-Vertrag lebt seit dem Split in `export_dialog_base.py`.
    export_base_path = "app/ui/export_dialog_base.py"
    export_module = _read(export_base_path)
    for snippet in (
        "from bw_gui.shortcuts import compose_hover_text as compose_shared_hover_text",
        "merged = compose_shared_hover_text(desc, shortcut)",
    ):
        _require_substring(export_module, snippet, export_base_path, errors)

    for rel_path in ("app/ui/export_dialog.py", export_base_path):
        _forbid_substring(_read(rel_path), "except ModuleNotFoundError", rel_path, errors)


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


