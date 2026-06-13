from app.storage.user_preferences_adapter import normalize_user_preferences
from app.ui.blatt_ui_export import (
    _normalize_choice,
    _resolve_export_default_format,
    _resolve_export_default_page_format,
)


def test_normalize_choice_accepts_known_value_case_insensitive():
    value = _normalize_choice("PDF", {"pdf", "png"}, "pdf")

    assert value == "pdf"


def test_normalize_choice_returns_default_for_unknown_value():
    value = _normalize_choice("a4_portrait", {"pdf", "png"}, "pdf")

    assert value == "pdf"


def test_resolve_export_default_format_prefers_mode_specific_keys():
    preferences = {
        "default_export_format_worksheet": "html",
        "default_export_format_presentation": "pptx",
    }

    worksheet_value = _resolve_export_default_format(preferences, "worksheet")
    presentation_value = _resolve_export_default_format(preferences, "presentation")

    assert worksheet_value == "html"
    assert presentation_value == "pptx"


def test_resolve_export_default_format_uses_legacy_fallback_for_both_modes():
    preferences = {"default_export_format": "pngzip"}

    worksheet_value = _resolve_export_default_format(preferences, "worksheet")
    presentation_value = _resolve_export_default_format(preferences, "presentation")

    assert worksheet_value == "pngzip"
    assert presentation_value == "pngzip"


def test_resolve_export_default_format_falls_back_when_worksheet_uses_presentation_only_format():
    preferences = {
        "default_export_format_worksheet": "pptx",
        "default_export_format_presentation": "pptx",
    }

    worksheet_value = _resolve_export_default_format(preferences, "worksheet")
    presentation_value = _resolve_export_default_format(preferences, "presentation")

    assert worksheet_value == "pdf"
    assert presentation_value == "pptx"


def test_resolve_export_default_page_format_prefers_mode_specific_keys():
    preferences = {
        "default_export_page_format_worksheet": "a5_landscape",
        "default_export_page_format_presentation": "presentation_16_10",
    }

    worksheet_value = _resolve_export_default_page_format(preferences, "worksheet")
    presentation_value = _resolve_export_default_page_format(preferences, "presentation")

    assert worksheet_value == "a5_landscape"
    assert presentation_value == "presentation_16_10"


def test_normalize_user_preferences_maps_legacy_export_keys_to_split_keys():
    normalized = normalize_user_preferences(
        {
            "default_export_format": "png",
            "default_export_page_format": "a5_landscape",
        }
    )

    assert normalized["default_export_format_worksheet"] == "png"
    assert normalized["default_export_format_presentation"] == "png"
    assert normalized["default_export_page_format_worksheet"] == "a5_landscape"
    # Legacy worksheet format is invalid for presentation defaults and is normalized safely.
    assert normalized["default_export_page_format_presentation"] == "presentation_16_9"


def test_normalize_user_preferences_adds_preview_auto_refresh_defaults():
    normalized = normalize_user_preferences({})

    assert normalized["preview_auto_refresh_on_edit_idle_enabled"] is False
    assert normalized["preview_auto_refresh_on_edit_idle_delay_ms"] == 1200


def test_normalize_user_preferences_clamps_preview_auto_refresh_delay():
    low = normalize_user_preferences({"preview_auto_refresh_on_edit_idle_delay_ms": 1})
    high = normalize_user_preferences({"preview_auto_refresh_on_edit_idle_delay_ms": 99999})

    assert low["preview_auto_refresh_on_edit_idle_delay_ms"] == 200
    assert high["preview_auto_refresh_on_edit_idle_delay_ms"] == 10000


def test_normalize_user_preferences_adds_kurzentwurf_runtime_defaults():
    normalized = normalize_user_preferences({})

    assert normalized["kurzentwurf_column_widths_text"] == "10 20 60 10"
    assert normalized["kurzentwurf_show_document_header"] is False
    assert normalized["kurzentwurf_body_font_size_pt"] == 10.5
    assert normalized["kurzentwurf_page_margin_cm"] == 1.15
    assert normalized["kurzentwurf_page_orientation_mode"] == "vertical"
    assert normalized["kurzentwurf_phase_row_separator_mode"] == "line"
    assert normalized["kurzentwurf_phase_row_spacing_px"] == 10
    assert normalized["kurzentwurf_s_marker_label"] == "S:innen"
    assert normalized["kurzentwurf_ant_marker_label"] == "Antizipiert:"
