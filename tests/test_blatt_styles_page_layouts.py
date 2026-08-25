from app.styles.blatt_styles import (
    build_page_layout_css,
    resolve_printable_height_cm,
    resolve_printable_width_cm,
)


def test_a6_portrait_resolves_to_a6_physical_width():
    # A6 ist per ISO 216 exakt 10.5cm breit -- deckt sich bewusst mit der
    # DIN-A6-Kartenbreite der Lernhilfen (siehe HELP_CARD_WIDTH_CM).
    width_cm = resolve_printable_width_cm("a6_portrait")
    assert 9.0 < width_cm < 10.5


def test_a6_portrait_page_size_css_is_explicit_not_a4_fallback():
    css = build_page_layout_css("a6_portrait")
    assert "10.5cm 14.8cm" in css
    assert "A4" not in css


def test_a6_portrait_unknown_falls_back_to_a4_only_for_missing_keys():
    # Regressionsschutz: ein spaeter versehentlich entfernter a6_portrait-Key
    # duerfte NICHT still auf A4 zurueckfallen -- dieser Test dokumentiert,
    # dass "a6_portrait" ein eigenstaendiger, registrierter Schluessel ist.
    from app.styles.blatt_styles import PAGE_LAYOUTS

    assert "a6_portrait" in PAGE_LAYOUTS
    assert PAGE_LAYOUTS["a6_portrait"]["page_size_css"] == "10.5cm 14.8cm"


def test_resolve_printable_height_cm_a4_portrait_is_taller_than_wide():
    width_cm = resolve_printable_width_cm("a4_portrait")
    height_cm = resolve_printable_height_cm("a4_portrait")
    assert height_cm > width_cm


def test_resolve_printable_height_cm_landscape_is_wider_than_tall():
    width_cm = resolve_printable_width_cm("a5_landscape")
    height_cm = resolve_printable_height_cm("a5_landscape")
    assert width_cm > height_cm


def test_resolve_printable_height_cm_ignores_hole_punch(monkeypatch):
    # Hole-punch margins only exist for the left/right (binding) side in
    # PAGE_LAYOUTS -- height must resolve identically either way.
    without_hole_punch = resolve_printable_height_cm("a4_portrait", hole_punch_enabled=False)
    with_hole_punch = resolve_printable_height_cm("a4_portrait", hole_punch_enabled=True)
    assert without_hole_punch == with_hole_punch


def test_resolve_printable_height_cm_unknown_format_falls_back_to_a4_portrait():
    assert resolve_printable_height_cm("does-not-exist") == resolve_printable_height_cm("a4_portrait")
