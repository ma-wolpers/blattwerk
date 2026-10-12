"""Export-Vorgaben der GUI: erlaubte Formate, Modi und Seitenformate je Layoutfamilie.

Reine Normalisierungslogik ohne Tk; genutzt von den Export-Mixins und dem
Praesentations-/Arbeitsblatt-Exportdialog.
"""

from __future__ import annotations

from ..core.document_type_registry import (
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    spec_for_type,
)


# Abgeleitet aus der Registry ("unterstützte Formate je Typ", keine Format-Registry).
_ALLOWED_WORKSHEET_EXPORT_FORMATS = set(spec_for_type(DOCUMENT_TYPE_WORKSHEET).export_formats)
_ALLOWED_PRESENTATION_EXPORT_FORMATS = set(spec_for_type(DOCUMENT_TYPE_PRESENTATION).export_formats)
_ALLOWED_LERNHILFEN_EXPORT_FORMATS = {"pdf", "png", "pngzip"}
_ALLOWED_EXPORT_MODES = {"worksheet", "solution", "both"}
_ALLOWED_BLACK_SCREEN_MODES = {"none", "before", "after", "both"}
_ALLOWED_SECTION_SEPARATOR_MODES = {"dot", "arrow"}
_ALLOWED_WORKSHEET_PAGE_FORMATS = {"a4_portrait", "a5_landscape"}
_ALLOWED_PRESENTATION_PAGE_FORMATS = {
    "presentation_16_9",
    "presentation_16_10",
    "presentation_4_3",
}


def _normalize_choice(value, allowed_values, default):
    """Normalize string choices against an allow-list."""
    normalized = str(value or "").strip().lower()
    if normalized in allowed_values:
        return normalized
    return default


def _resolve_export_default_format(preferences, layout_family):
    """Return the preferred export format for the worksheet vs presentation layout family."""
    if layout_family == "presentation":
        preferred = preferences.get(
            "default_export_format_presentation",
            preferences.get("default_export_format", "pptx"),
        )
        return _normalize_choice(preferred, _ALLOWED_PRESENTATION_EXPORT_FORMATS, "pptx")

    preferred = preferences.get(
        "default_export_format_worksheet",
        preferences.get("default_export_format", "pdf"),
    )
    return _normalize_choice(preferred, _ALLOWED_WORKSHEET_EXPORT_FORMATS, "pdf")


def _resolve_export_default_page_format(preferences, layout_family):
    """Return the preferred page format for the worksheet vs presentation layout family."""
    if layout_family == "presentation":
        preferred = preferences.get(
            "default_export_page_format_presentation",
            preferences.get("default_export_page_format", "presentation_16_9"),
        )
        return _normalize_choice(preferred, _ALLOWED_PRESENTATION_PAGE_FORMATS, "presentation_16_9")

    preferred = preferences.get(
        "default_export_page_format_worksheet",
        preferences.get("default_export_page_format", "a4_portrait"),
    )
    return _normalize_choice(preferred, _ALLOWED_WORKSHEET_PAGE_FORMATS, "a4_portrait")
