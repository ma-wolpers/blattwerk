"""Adapter helpers for persisted worksheet design profiles."""

from __future__ import annotations

from .blatt_styles import normalize_font_profile, normalize_font_size_profile
from .worksheet_design import normalize_color_profile, normalize_contrast_profile


def _clean_profile_value(value):
    return str(value or "").strip()


def resolve_persisted_design_profiles(ui_settings, color_profile_order):
    """Resolve persisted UI settings into normalized worksheet design profiles."""

    saved_color_profile = (ui_settings or {}).get("worksheet_color_profile")
    if not saved_color_profile:
        legacy_color_mode = ((ui_settings or {}).get("worksheet_color_mode") or "").strip().lower()
        legacy_accent = ((ui_settings or {}).get("worksheet_accent") or "").strip().lower()
        if legacy_color_mode == "bw":
            saved_color_profile = "bw"
        elif legacy_accent in color_profile_order:
            saved_color_profile = legacy_accent

    return {
        "worksheet_contrast": normalize_contrast_profile(_clean_profile_value((ui_settings or {}).get("worksheet_contrast"))),
        "worksheet_color_profile": normalize_color_profile(_clean_profile_value(saved_color_profile)),
        "worksheet_font_profile": normalize_font_profile(_clean_profile_value((ui_settings or {}).get("worksheet_font_profile"))),
        "worksheet_font_size_profile": normalize_font_size_profile(_clean_profile_value((ui_settings or {}).get("worksheet_font_size_profile"))),
    }


def normalize_design_profiles_for_persistence(
    *,
    worksheet_contrast,
    worksheet_color_profile,
    worksheet_font_profile,
    worksheet_font_size_profile,
):
    """Normalize current UI profile values before writing persisted settings."""

    return {
        "worksheet_contrast": normalize_contrast_profile(_clean_profile_value(worksheet_contrast)),
        "worksheet_color_profile": normalize_color_profile(_clean_profile_value(worksheet_color_profile)),
        "worksheet_font_profile": normalize_font_profile(_clean_profile_value(worksheet_font_profile)),
        "worksheet_font_size_profile": normalize_font_size_profile(_clean_profile_value(worksheet_font_size_profile)),
    }
