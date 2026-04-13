"""Validierung und Metadaten fuer nutzerspezifische Einstellungen."""

from __future__ import annotations

from copy import deepcopy

from ..ui.ui_constants import (
    EDITOR_VIEW_BOTH,
    VIEW_FIT_WIDTH,
    VIEW_LAYOUT_SINGLE,
)
from ..ui.ui_theme import DEFAULT_THEME, THEME_ORDER
from ..styles.blatt_styles import (
    DEFAULT_FONT_PROFILE,
    DEFAULT_FONT_SIZE_PROFILE,
    FONT_PROFILE_ORDER,
    FONT_SIZE_PROFILE_ORDER,
)
from ..styles.worksheet_design import (
    CONTRAST_PROFILE_ORDER,
    DEFAULT_COLOR_PROFILE,
    COLOR_PROFILE_ORDER,
)
from .local_config_store import (
    DEFAULT_MAX_RECENT_FILES,
    MAX_MAX_RECENT_FILES,
    MIN_MAX_RECENT_FILES,
)

TAB_ORDER = [
    "general",
    "editor_snippets",
    "editor_diagnostics",
    "view_layout",
    "design_theme",
    "export",
    "shortcuts",
    "identity",
    "document_defaults",
    "accessibility",
    "backup",
]

TAB_LABELS = {
    "general": "Allgemein",
    "editor_snippets": "Editor Snippets",
    "editor_diagnostics": "Editor Diagnostik",
    "view_layout": "Ansicht und Layout",
    "design_theme": "Design und Theme",
    "export": "Export",
    "shortcuts": "Shortcuts",
    "identity": "Identitaet und Copyright",
    "document_defaults": "Dokument Defaults",
    "accessibility": "Bedienung und Accessibility",
    "backup": "Sicherheit und Backup",
}

PREFERENCE_SPECS = {
    # Allgemein
    "max_recent_files": {
        "tab": "general",
        "label": "Maximal zuletzt geoeffnete Dateien",
        "type": "int",
        "default": DEFAULT_MAX_RECENT_FILES,
        "min": MIN_MAX_RECENT_FILES,
        "max": MAX_MAX_RECENT_FILES,
    },
    "remember_dialog_dirs": {
        "tab": "general",
        "label": "Dialog-Ordner merken",
        "type": "bool",
        "default": True,
    },
    "start_with_last_file": {
        "tab": "general",
        "label": "Beim Start letzte Datei laden",
        "type": "bool",
        "default": False,
    },
    # Editor Snippets
    "snippets_auto_enabled": {
        "tab": "editor_snippets",
        "label": "Auto-Snippet Vorschlaege",
        "type": "bool",
        "default": True,
    },
    "snippet_trigger_colon": {"tab": "editor_snippets", "label": "Trigger Doppelpunkt", "type": "bool", "default": True},
    "snippet_trigger_equals": {"tab": "editor_snippets", "label": "Trigger Gleichheitszeichen", "type": "bool", "default": True},
    "snippet_trigger_enter": {"tab": "editor_snippets", "label": "Trigger Enter", "type": "bool", "default": True},
    "completion_context_sources": {
        "tab": "editor_snippets",
        "label": "Completion-Kontextquellen",
        "type": "enum",
        "default": "smart",
        "values": ["smart", "all", "manual_only"],
    },
    "snippet_popup_width_mode": {
        "tab": "editor_snippets",
        "label": "Snippet-Popup Breite",
        "type": "enum",
        "default": "wide",
        "values": ["compact", "normal", "wide"],
    },
    "snippet_tabstop_navigation": {
        "tab": "editor_snippets",
        "label": "Tabstop-Navigation aktiv",
        "type": "bool",
        "default": True,
    },
    "snippet_auto_finish_on_flow_leave": {
        "tab": "editor_snippets",
        "label": "Snippet-Session auto-finish",
        "type": "bool",
        "default": True,
    },
    "snippet_field_highlight_enabled": {
        "tab": "editor_snippets",
        "label": "Snippet-Feldhighlight aktiv",
        "type": "bool",
        "default": True,
    },
    "snippet_field_highlight_ms": {
        "tab": "editor_snippets",
        "label": "Snippet-Feldhighlight Dauer (ms)",
        "type": "int",
        "default": 600,
        "min": 100,
        "max": 5000,
    },
    # Editor Diagnostik
    "diagnostics_live_enabled": {
        "tab": "editor_diagnostics",
        "label": "Live-Diagnostik aktiv",
        "type": "bool",
        "default": True,
    },
    "diagnostics_debounce_ms": {
        "tab": "editor_diagnostics",
        "label": "Diagnostik Debounce (ms)",
        "type": "int",
        "default": 350,
        "min": 100,
        "max": 3000,
    },
    "diagnostics_severity_threshold": {
        "tab": "editor_diagnostics",
        "label": "Diagnostik Schwellwert",
        "type": "enum",
        "default": "warning",
        "values": ["error", "warning", "info"],
    },
    "outline_visible_on_start": {
        "tab": "editor_diagnostics",
        "label": "Outline beim Start zeigen",
        "type": "bool",
        "default": True,
    },
    "outline_debounce_ms": {
        "tab": "editor_diagnostics",
        "label": "Outline Debounce (ms)",
        "type": "int",
        "default": 220,
        "min": 80,
        "max": 3000,
    },
    "syntax_warning_highlight_enabled": {
        "tab": "editor_diagnostics",
        "label": "Syntaxwarnungen hervorheben",
        "type": "bool",
        "default": True,
    },
    # Ansicht und Layout
    "startup_editor_view_mode": {
        "tab": "view_layout",
        "label": "Start Bereichsansicht",
        "type": "enum",
        "default": EDITOR_VIEW_BOTH,
        "values": ["preview_only", "both", "editor_only"],
        "live_apply": True,
    },
    "startup_fit_mode": {
        "tab": "view_layout",
        "label": "Start Fit-Modus",
        "type": "enum",
        "default": VIEW_FIT_WIDTH,
        "values": ["fit_width", "fit_page"],
        "live_apply": True,
    },
    "startup_layout_mode": {
        "tab": "view_layout",
        "label": "Start Layout",
        "type": "enum",
        "default": VIEW_LAYOUT_SINGLE,
        "values": ["single", "strip", "stack"],
        "live_apply": True,
    },
    "startup_split_ratio": {
        "tab": "view_layout",
        "label": "Start Split-Verhaeltnis",
        "type": "float",
        "default": 0.5,
        "min": 0.2,
        "max": 0.8,
    },
    "responsive_controls_wrap": {
        "tab": "view_layout",
        "label": "Responsive Control-Wrapping",
        "type": "bool",
        "default": True,
    },
    "remember_window_geometry": {
        "tab": "view_layout",
        "label": "Fenstergeometrie merken",
        "type": "bool",
        "default": False,
    },
    # Design und Theme
    "default_theme_key": {
        "tab": "design_theme",
        "label": "Theme",
        "type": "enum",
        "default": DEFAULT_THEME,
        "values": list(THEME_ORDER),
        "live_apply": True,
    },
    "default_color_profile": {
        "tab": "design_theme",
        "label": "Farbprofil",
        "type": "enum",
        "default": DEFAULT_COLOR_PROFILE,
        "values": list(COLOR_PROFILE_ORDER),
        "live_apply": True,
    },
    "default_font_profile": {
        "tab": "design_theme",
        "label": "Schriftprofil",
        "type": "enum",
        "default": DEFAULT_FONT_PROFILE,
        "values": list(FONT_PROFILE_ORDER),
        "live_apply": True,
    },
    "default_font_size_profile": {
        "tab": "design_theme",
        "label": "Schriftgroessenprofil",
        "type": "enum",
        "default": DEFAULT_FONT_SIZE_PROFILE,
        "values": list(FONT_SIZE_PROFILE_ORDER),
        "live_apply": True,
    },
    "default_contrast_profile": {
        "tab": "design_theme",
        "label": "Druckprofil",
        "type": "enum",
        "default": CONTRAST_PROFILE_ORDER[0],
        "values": list(CONTRAST_PROFILE_ORDER),
        "live_apply": True,
    },
    # Export
    "default_export_page_format": {
        "tab": "export",
        "label": "Export Seitenformat",
        "type": "enum",
        "default": "a4_portrait",
        "values": ["a4_portrait", "a5_landscape"],
    },
    "default_export_format": {
        "tab": "export",
        "label": "Export Dateiformat",
        "type": "enum",
        "default": "pdf",
        "values": ["pdf", "html", "png", "pngzip"],
    },
    "default_export_mode": {
        "tab": "export",
        "label": "Export Modus",
        "type": "enum",
        "default": "worksheet",
        "values": ["worksheet", "solution", "both"],
    },
    "solution_suffix": {
        "tab": "export",
        "label": "Loesungs-Suffix",
        "type": "str",
        "default": "_loesung",
    },
    "pre_export_diagnostics_enabled": {
        "tab": "export",
        "label": "Pre-Export Diagnostik anzeigen",
        "type": "bool",
        "default": True,
    },
    "remember_export_dir": {
        "tab": "export",
        "label": "Export-Ordner merken",
        "type": "bool",
        "default": True,
    },
    # Shortcuts
    "shortcuts_preview_group_enabled": {
        "tab": "shortcuts",
        "label": "Shortcut-Gruppe Vorschau aktiv",
        "type": "bool",
        "default": True,
    },
    "shortcuts_editor_group_enabled": {
        "tab": "shortcuts",
        "label": "Shortcut-Gruppe Editor aktiv",
        "type": "bool",
        "default": True,
    },
    "shortcuts_menu_hints_visible": {
        "tab": "shortcuts",
        "label": "Shortcut-Hinweise im Menue anzeigen",
        "type": "bool",
        "default": True,
    },
    # Allgemein neu
    "copyright_holder": {
        "tab": "identity",
        "label": "Copyright-Inhaber",
        "type": "str",
        "default": "",
    },
    "copyright_year_mode": {
        "tab": "identity",
        "label": "Copyright-Zeitraummodus",
        "type": "enum",
        "default": "current",
        "values": ["current", "fixed", "span"],
    },
    "copyright_year_fixed": {
        "tab": "identity",
        "label": "Copyright-Jahr (fix)",
        "type": "int",
        "default": 2026,
        "min": 1990,
        "max": 2100,
    },
    "default_document_author": {
        "tab": "identity",
        "label": "Dokumentautor Standard",
        "type": "str",
        "default": "",
    },
    "default_school_name": {
        "tab": "identity",
        "label": "Schulname Standard",
        "type": "str",
        "default": "",
    },
    "default_subject": {
        "tab": "identity",
        "label": "Fach Standard",
        "type": "str",
        "default": "",
    },
    "default_grade_level": {
        "tab": "identity",
        "label": "Klassenstufe Standard",
        "type": "str",
        "default": "",
    },
    "footer_extra_text": {
        "tab": "identity",
        "label": "Fusszeilen-Zusatztext",
        "type": "str",
        "default": "",
    },
    # Dokument Defaults
    "new_doc_title_prefix": {
        "tab": "document_defaults",
        "label": "Titel-Praefix neue Dokumente",
        "type": "str",
        "default": "",
    },
    "worksheet_label": {
        "tab": "document_defaults",
        "label": "Aufgabenblatt-Label",
        "type": "str",
        "default": "Aufgaben",
    },
    "solution_label": {
        "tab": "document_defaults",
        "label": "Loesungsblatt-Label",
        "type": "str",
        "default": "Loesung",
    },
    "language_variant": {
        "tab": "document_defaults",
        "label": "Sprachvariante",
        "type": "enum",
        "default": "de-DE",
        "values": ["de-DE", "de-AT", "de-CH"],
    },
    "date_format": {
        "tab": "document_defaults",
        "label": "Datumsformat",
        "type": "enum",
        "default": "DD.MM.YYYY",
        "values": ["DD.MM.YYYY", "YYYY-MM-DD"],
    },
    "default_work_emoji_visible": {
        "tab": "document_defaults",
        "label": "Arbeits-Emoji standardmaessig sichtbar",
        "type": "bool",
        "default": True,
    },
    # Accessibility
    "tooltips_enabled": {
        "tab": "accessibility",
        "label": "Tooltips anzeigen",
        "type": "bool",
        "default": True,
    },
    "ui_scale_percent": {
        "tab": "accessibility",
        "label": "UI-Skalierung (Prozent)",
        "type": "int",
        "default": 100,
        "min": 90,
        "max": 130,
    },
    "reduce_motion": {
        "tab": "accessibility",
        "label": "Bewegungsreduktion",
        "type": "bool",
        "default": False,
    },
    "ui_density": {
        "tab": "accessibility",
        "label": "UI-Dichte",
        "type": "enum",
        "default": "comfort",
        "values": ["comfort", "compact"],
    },
    # Backup
    "backup_on_save": {
        "tab": "backup",
        "label": "Backup beim Speichern",
        "type": "bool",
        "default": False,
    },
    "backup_versions_keep": {
        "tab": "backup",
        "label": "Anzahl Backup-Versionen",
        "type": "int",
        "default": 3,
        "min": 1,
        "max": 50,
    },
}


def default_user_preferences() -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, spec in PREFERENCE_SPECS.items():
        payload[key] = deepcopy(spec.get("default"))
    return payload


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _coerce_int(value: object, default: int, min_value: int | None, max_value: int | None) -> int:
    try:
        normalized = int(value)
    except Exception:
        normalized = int(default)
    if min_value is not None:
        normalized = max(min_value, normalized)
    if max_value is not None:
        normalized = min(max_value, normalized)
    return normalized


def _coerce_float(value: object, default: float, min_value: float | None, max_value: float | None) -> float:
    try:
        normalized = float(value)
    except Exception:
        normalized = float(default)
    if min_value is not None:
        normalized = max(min_value, normalized)
    if max_value is not None:
        normalized = min(max_value, normalized)
    return normalized


def _coerce_enum(value: object, default: str, allowed_values: list[str]) -> str:
    text = str(value or "").strip()
    return text if text in allowed_values else str(default)


def _coerce_str(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text if text else str(default)


def normalize_user_preferences(raw: object) -> dict[str, object]:
    defaults = default_user_preferences()
    if not isinstance(raw, dict):
        return defaults

    normalized = defaults
    for key, spec in PREFERENCE_SPECS.items():
        default_value = defaults[key]
        raw_value = raw.get(key, default_value)
        pref_type = spec.get("type")

        if pref_type == "bool":
            normalized[key] = _coerce_bool(raw_value, bool(default_value))
            continue

        if pref_type == "int":
            normalized[key] = _coerce_int(
                raw_value,
                int(default_value),
                spec.get("min"),
                spec.get("max"),
            )
            continue

        if pref_type == "float":
            normalized[key] = _coerce_float(
                raw_value,
                float(default_value),
                spec.get("min"),
                spec.get("max"),
            )
            continue

        if pref_type == "enum":
            normalized[key] = _coerce_enum(raw_value, str(default_value), list(spec.get("values", [])))
            continue

        normalized[key] = _coerce_str(raw_value, str(default_value))

    return normalized


def get_tab_specs() -> list[tuple[str, str, list[tuple[str, dict[str, object]]]]]:
    result: list[tuple[str, str, list[tuple[str, dict[str, object]]]]] = []
    for tab_key in TAB_ORDER:
        tab_specs: list[tuple[str, dict[str, object]]] = []
        for key, spec in PREFERENCE_SPECS.items():
            if spec.get("tab") == tab_key:
                tab_specs.append((key, spec))
        result.append((tab_key, TAB_LABELS.get(tab_key, tab_key), tab_specs))
    return result
