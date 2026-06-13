"""Kurzentwurf runtime option normalization shared by preview and export."""

from __future__ import annotations

from typing import Mapping

from .kurzentwurf_runtime.column_widths import (
    DEFAULT_COLUMN_WEIGHTS_TEXT,
    normalize_column_weights_text,
)
from .kurzentwurf_runtime.render_html import (
    DEFAULT_ANT_MARKER_LABEL,
    DEFAULT_BODY_FONT_SIZE_PT,
    DEFAULT_PAGE_ORIENTATION_MODE,
    DEFAULT_PAGE_MARGIN_CM,
    DEFAULT_PHASE_ROW_SEPARATOR_MODE,
    DEFAULT_PHASE_ROW_SPACING_PX,
    DEFAULT_S_MARKER_LABEL,
    PAGE_ORIENTATION_HORIZONTAL,
    PAGE_ORIENTATION_VERTICAL,
    PHASE_SEPARATOR_LINE,
    PHASE_SEPARATOR_SPACE,
)


def resolve_kurzentwurf_runtime_options(raw: Mapping[str, object] | None) -> dict[str, object]:
    """Resolve validated runtime options for integrated Kurzentwurf rendering/export."""

    source = raw if isinstance(raw, Mapping) else {}

    column_widths_text = str(source.get("column_widths_text", "") or "").strip()
    try:
        normalized_column_widths = normalize_column_weights_text(column_widths_text)
    except Exception:
        normalized_column_widths = DEFAULT_COLUMN_WEIGHTS_TEXT

    return {
        "column_widths_text": normalized_column_widths,
        "show_document_header": _coerce_bool(source.get("show_document_header"), default=False),
        "body_font_size_pt": _coerce_float(
            source.get("body_font_size_pt"),
            default=DEFAULT_BODY_FONT_SIZE_PT,
            min_value=8.0,
            max_value=16.0,
        ),
        "page_margin_cm": _coerce_float(
            source.get("page_margin_cm"),
            default=DEFAULT_PAGE_MARGIN_CM,
            min_value=0.4,
            max_value=4.0,
        ),
        "page_orientation_mode": _coerce_page_orientation_mode(
            source.get("page_orientation_mode"),
            default=DEFAULT_PAGE_ORIENTATION_MODE,
        ),
        "phase_row_separator_mode": _coerce_separator_mode(
            source.get("phase_row_separator_mode"),
            default=DEFAULT_PHASE_ROW_SEPARATOR_MODE,
        ),
        "phase_row_spacing_px": _coerce_int(
            source.get("phase_row_spacing_px"),
            default=DEFAULT_PHASE_ROW_SPACING_PX,
            min_value=0,
            max_value=40,
        ),
        "s_marker_label": _coerce_non_empty_text(source.get("s_marker_label"), default=DEFAULT_S_MARKER_LABEL),
        "ant_marker_label": _coerce_non_empty_text(
            source.get("ant_marker_label"),
            default=DEFAULT_ANT_MARKER_LABEL,
        ),
    }


def kurzentwurf_runtime_options_from_preferences(preferences: Mapping[str, object] | None) -> dict[str, object]:
    """Map persisted user preferences to normalized runtime options."""

    prefs = preferences if isinstance(preferences, Mapping) else {}
    return resolve_kurzentwurf_runtime_options(
        {
            "column_widths_text": prefs.get("kurzentwurf_column_widths_text", DEFAULT_COLUMN_WEIGHTS_TEXT),
            "show_document_header": prefs.get("kurzentwurf_show_document_header", False),
            "body_font_size_pt": prefs.get("kurzentwurf_body_font_size_pt", DEFAULT_BODY_FONT_SIZE_PT),
            "page_margin_cm": prefs.get("kurzentwurf_page_margin_cm", DEFAULT_PAGE_MARGIN_CM),
            "page_orientation_mode": prefs.get(
                "kurzentwurf_page_orientation_mode",
                DEFAULT_PAGE_ORIENTATION_MODE,
            ),
            "phase_row_separator_mode": prefs.get(
                "kurzentwurf_phase_row_separator_mode",
                DEFAULT_PHASE_ROW_SEPARATOR_MODE,
            ),
            "phase_row_spacing_px": prefs.get(
                "kurzentwurf_phase_row_spacing_px",
                DEFAULT_PHASE_ROW_SPACING_PX,
            ),
            "s_marker_label": prefs.get("kurzentwurf_s_marker_label", DEFAULT_S_MARKER_LABEL),
            "ant_marker_label": prefs.get("kurzentwurf_ant_marker_label", DEFAULT_ANT_MARKER_LABEL),
        }
    )


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "ja", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _coerce_float(value: object, *, default: float, min_value: float, max_value: float) -> float:
    try:
        normalized = float(value)
    except Exception:
        normalized = float(default)
    return max(min_value, min(max_value, normalized))


def _coerce_int(value: object, *, default: int, min_value: int, max_value: int) -> int:
    try:
        normalized = int(value)
    except Exception:
        normalized = int(default)
    return max(min_value, min(max_value, normalized))


def _coerce_separator_mode(value: object, *, default: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {PHASE_SEPARATOR_LINE, PHASE_SEPARATOR_SPACE}:
        return normalized
    return default


def _coerce_page_orientation_mode(value: object, *, default: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {PAGE_ORIENTATION_VERTICAL, PAGE_ORIENTATION_HORIZONTAL}:
        return normalized
    return default


def _coerce_non_empty_text(value: object, *, default: str) -> str:
    normalized = str(value or "").strip()
    return normalized if normalized else default
