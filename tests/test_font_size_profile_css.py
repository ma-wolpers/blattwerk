import re

from app.styles.blatt_styles import build_font_size_profile_css


def _extract_font_size_base(css_text: str) -> str:
    match = re.search(r"--font-size-base:\s*([^;]+);", css_text)
    assert match is not None
    return match.group(1).strip()


def test_font_size_profile_css_is_stable_for_same_worksheet_class():
    css_a = build_font_size_profile_css("normal", document_mode="worksheet")
    css_b = build_font_size_profile_css("normal", document_mode="worksheet")

    assert _extract_font_size_base(css_a) == _extract_font_size_base(css_b)


def test_font_size_profile_css_is_stable_for_same_presentation_class():
    css_a = build_font_size_profile_css("normal", document_mode="presentation")
    css_b = build_font_size_profile_css("normal", document_mode="presentation")

    assert _extract_font_size_base(css_a) == _extract_font_size_base(css_b)


def test_font_size_profile_css_respects_mode_specific_mapping():
    worksheet_css = build_font_size_profile_css("normal", document_mode="worksheet")
    presentation_css = build_font_size_profile_css("normal", document_mode="presentation")

    assert _extract_font_size_base(worksheet_css) != _extract_font_size_base(presentation_css)
