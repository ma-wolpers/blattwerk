from app.ui.blatt_ui_export import _normalize_choice


def test_normalize_choice_accepts_known_value_case_insensitive():
    value = _normalize_choice("PDF", {"pdf", "png"}, "pdf")

    assert value == "pdf"


def test_normalize_choice_returns_default_for_unknown_value():
    value = _normalize_choice("a4_portrait", {"pdf", "png"}, "pdf")

    assert value == "pdf"
