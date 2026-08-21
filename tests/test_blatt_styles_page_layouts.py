from app.styles.blatt_styles import build_page_layout_css, resolve_printable_width_cm


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
