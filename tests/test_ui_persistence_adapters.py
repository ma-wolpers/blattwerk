from app.storage.system_settings_adapter import normalize_system_settings_payload
from app.styles.ui_profile_adapter import (
    normalize_design_profiles_for_persistence,
    resolve_persisted_design_profiles,
)


def test_normalize_system_settings_payload_clamps_invalid_values():
    normalized = normalize_system_settings_payload({"max_recent_files": "999"})

    assert normalized["max_recent_files"] == 20


def test_resolve_persisted_design_profiles_uses_legacy_bw_fallback():
    resolved = resolve_persisted_design_profiles(
        {
            "worksheet_color_mode": "bw",
            "worksheet_font_profile": "segoe",
            "worksheet_font_size_profile": "normal",
        },
        color_profile_order=["indigo", "bw"],
    )

    assert resolved["worksheet_color_profile"] == "bw"


def test_normalize_design_profiles_for_persistence_returns_normalized_keys():
    normalized = normalize_design_profiles_for_persistence(
        worksheet_contrast=" strong ",
        worksheet_color_profile=" BW ",
        worksheet_font_profile=" segoe ",
        worksheet_font_size_profile=" normal ",
    )

    assert normalized["worksheet_contrast"] == "strong"
    assert normalized["worksheet_color_profile"] == "bw"
    assert normalized["worksheet_font_profile"] == "segoe"
    assert normalized["worksheet_font_size_profile"] == "normal"
