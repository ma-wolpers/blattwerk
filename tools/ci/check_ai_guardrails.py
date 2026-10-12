#!/usr/bin/env python3
"""AI-Guardrail-Einstiegspunkt (lokal und in CI): ``python tools/ci/check_ai_guardrails.py``.

Fuehrt alle Checks aus den ``guardrails_*``-Modulen aus. Unbedingt laufen die
Sync-Checks (Extension, Anleitungen, KZF); die uebrigen nur, wenn guardrail-relevante
Dateien gestaged sind oder nichts gestaged ist (CI).
"""

from __future__ import annotations

import guardrails_config  # noqa: F401 -- haengt die Repo-Wurzel in sys.path ein
from guardrails_common import (
    _has_relevant_staged_changes,
    _read,
    _repo_root,
    _require_substring,
    _staged_added_lines,
    _staged_files,
)
from guardrails_process import (
    _check_changelog_updated,
    _check_development_log_updated,
    _collect_process_guidance_warnings,
    _collect_shortcut_coverage_warnings,
    _is_ci_environment,
)
from guardrails_extension_sync import (
    _check_extension_validator_sync,
    _check_marker_token_consistency,
)
from guardrails_gui_contracts import (
    _check_blattwerker_solution_rule,
    _check_future_gui_entry_contracts,
    _check_gui_migration_backlog,
    _check_laufkern_fallback_sunset,
    _check_repo_wide_gui_contracts,
    _check_shared_ui_contract_hardening,
    _check_ui_contract_bridge_decommission,
)
from guardrails_docs_sync import (
    _check_authoring_guides_sync,
    _check_integrated_kurzentwurf_runtime,
    _check_kurzentwurf_diagnostics_sync,
)


def main() -> int:
    repo_root = _repo_root()
    staged = _staged_files(repo_root)

    errors: list[str] = []

    # Laufen unconditionally, vor dem Staged-File-Skip-Gate unten: beide
    # gleichen generierte/abgeleitete Artefakte gegen Code-Konstanten ab
    # und duerfen nicht uebersprungen werden, nur weil zufaellig keine der
    # in GUARDRAIL_RELEVANT_PATHS gelisteten Dateien gestaged ist (siehe
    # _check_authoring_guides_sync-Docstring).
    _check_extension_validator_sync(errors)
    _check_authoring_guides_sync(errors)
    _check_kurzentwurf_diagnostics_sync(errors)

    if staged and not _has_relevant_staged_changes(staged, repo_root):
        if errors:
            print("AI guardrail check failed:")
            for item in errors:
                print(f" - {item}")
            return 2
        print("AI guardrail check skipped (no guardrail-relevant staged files).")
        return 0

    _read("AGENTS.md")
    _read(".github/copilot-instructions.md")
    _read("CHANGELOG.md")
    _read("docs/intern/DEVELOPMENT_LOG.md")
    _read("bw_libs/ui_contract/keybinding.py")
    _read("bw_libs/ui_contract/popup.py")
    _read("bw_libs/ui_contract/hsm.py")
    _read("bw_libs/ui_contract/laufkern.py")
    _read("bw_libs/app_paths.py")

    arch_doc = _read("docs/intern/ARCHITEKTUR.md")
    _require_substring(
        arch_doc,
        "beschreiben nur den aktuellen Architekturzustand",
        "docs/intern/ARCHITEKTUR.md",
        errors,
    )
    _require_substring(
        arch_doc,
        "docs/intern/DEVELOPMENT_LOG.md",
        "docs/intern/ARCHITEKTUR.md",
        errors,
    )

    arch_simple_doc = _read("docs/intern/ARCHITEKTUR_EINFACH.md")
    _require_substring(
        arch_simple_doc,
        "zeigen nur den aktuellen Zustand",
        "docs/intern/ARCHITEKTUR_EINFACH.md",
        errors,
    )
    _require_substring(
        arch_simple_doc,
        "docs/intern/DEVELOPMENT_LOG.md",
        "docs/intern/ARCHITEKTUR_EINFACH.md",
        errors,
    )

    _check_development_log_updated(staged, errors)
    _check_changelog_updated(
        staged, errors, _staged_added_lines(repo_root, "docs/intern/DEVELOPMENT_LOG.md")
    )
    _check_marker_token_consistency(errors)
    _check_blattwerker_solution_rule(errors)
    _check_shared_ui_contract_hardening(errors)
    _check_laufkern_fallback_sunset(errors)
    _check_ui_contract_bridge_decommission(errors)
    _check_integrated_kurzentwurf_runtime(errors)
    _check_future_gui_entry_contracts(errors)
    _check_repo_wide_gui_contracts(errors)
    _check_gui_migration_backlog(errors)
    warnings = _collect_process_guidance_warnings()
    warnings.extend(_collect_shortcut_coverage_warnings())
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
