"""Konfiguration der AI-Guardrails: Repo-Wurzel, Pfadlisten und Marker-Konstanten.

Reine Daten (plus das einmalige Einhaengen der Repo-Wurzel in ``sys.path``); alle
Check-Module lesen ihre Konstanten von hier, damit Pfadlisten nur an einer Stelle
gepflegt werden.
"""

# line-limit: data-only
from __future__ import annotations

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
    "docs/intern/ARCHITEKTUR.md",
    "docs/intern/ARCHITEKTUR_EINFACH.md",
    "docs/intern/AGENT_SETUP.md",
    "docs/intern/DEVELOPMENT_LOG.md",
    "docs/intern/GUI_MIGRATION_BACKLOG.md",
    "docs/nutzer/VALIDATOR.md",
    "docs/nutzer/ANLEITUNG_ARBEITSBLATT_PRAESENTATION.md",
    "docs/nutzer/ANLEITUNG_KURZENTWURF.md",
    "docs/nutzer/ANLEITUNG_KLAUSUR.md",
    "docs/nutzer/EMPFEHLUNGEN_STIL_ARBEITSBLATT_PRAESENTATION.md",
    "docs/nutzer/EMPFEHLUNGEN_STIL_KURZENTWURF.md",
    "CHANGELOG.md",
    "tools/ci/check_ai_guardrails.py",
    "tools/ci/guardrails_config.py",
    "tools/ci/guardrails_common.py",
    "tools/ci/guardrails_process.py",
    "tools/ci/guardrails_extension_sync.py",
    "tools/ci/guardrails_gui_contracts.py",
    "tools/ci/guardrails_docs_sync.py",
    "tools/docs/generate_authoring_guides.py",
    "app/core/authoring_guide_prose.py",
    "tools/docs/authoring_guide_coverage.py",
    "tools/docs/authoring_guide_render_shared.py",
    "tools/docs/authoring_guide_render_worksheet.py",
    "tools/docs/authoring_guide_render_kurzentwurf.py",
    "tools/docs/authoring_guide_render_exam.py",
    "tools/docs/authoring_guide_render_schild.py",
    "app/core/markdown_conventions.py",
    "app/core/block_insert_snippets.py",
    "app/ui/blatt_ui_editor.py",
    "app/core/blatt_validator_constants.py",
    "app/core/blatt_validator_document.py",
    "app/core/blatt_validator_block_options.py",
    "app/core/blatt_validator_patterns.py",
    "app/core/blatt_validator_yaml_entries.py",
    "app/core/answer_grid_entries.py",
    "app/core/answer_special_shared.py",
    "app/core/document_type_registry.py",
    "app/core/document_type_templates.py",
    "app/core/document_semantics.py",
    "app/core/blatt_kern_shared.py",
    "app/core/blatt_kern_shared_data.py",
    "app/core/blatt_kern_shared_parsing.py",
    "app/core/blatt_kern_shared_blocks.py",
    "app/core/blatt_kern_shared_meta.py",
    "app/core/kurzentwurf_runtime/model.py",
    "app/core/kurzentwurf_runtime/dsl.py",
    "app/core/kurzentwurf_runtime/dsl_frontmatter.py",
    "app/core/kurzentwurf_runtime/dsl_phases.py",
    "app/core/kurzentwurf_runtime/dsl_segments.py",
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
FUTURE_GUI_ENTRY_BASELINES: set[str] = {
    # app/ui/blatt_ui.py ist eine reine Fassade (kombiniert nur Mixins zu
    # `class BlattwerkApp(...)`) -- der eigentliche, bereits vertragskonforme
    # Shared-Bootstrap lebt in app/ui/blatt_ui_base.py und wird dort separat
    # von _check_shared_ui_contract_hardening geprueft. Siehe
    # docs/intern/GUI_MIGRATION_BACKLOG.md fuer Begruendung/remove_by.
    "app/ui/blatt_ui.py",
}
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
GUI_MIGRATION_BACKLOG_PATH = "docs/intern/GUI_MIGRATION_BACKLOG.md"

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
# CHANGELOG.md ist nur fuer Aenderungen gedacht, die Nutzer:innen oder Mitentwickler:innen
# beim Benutzen bemerken. Rein interne Aenderungen unter den Praefixen oben belegen das
# mit diesem Satz in ihrem gestagten DEVELOPMENT_LOG-Eintrag.
CHANGELOG_OPT_OUT_MARKER = "Kein CHANGELOG-Eintrag"
LAUFKERN_BRIDGE_PATH = "bw_libs/ui_contract/laufkern.py"
LAUFKERN_FALLBACK_SCAN_ROOTS = ("app", "bw_libs")

INTEGRATED_KURZENTWURF_RUNTIME_ROOT = "app/core/kurzentwurf_runtime"


