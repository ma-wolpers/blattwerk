from app.core.completion_catalogs import get_completion_option_values, get_self_closing_block_types


def test_info_type_completion_only_returns_info_type_values():
    assert get_completion_option_values("info", "type") == ("default", "note", "warning")


def test_grid_type_completion_returns_empty_tuple():
    # `grid` erlaubt `type` als Option ueberhaupt nicht (siehe AN009) -> kein Katalog.
    assert get_completion_option_values("grid", "type") == ()


def test_unknown_block_type_type_completion_returns_empty_tuple():
    assert get_completion_option_values("does-not-exist", "type") == ()


def test_unknown_option_key_for_known_block_returns_empty_tuple_without_error():
    # Deckt die defensive Katalogabfrage ab: ein fehlender (block_type, option_key)-
    # Eintrag darf keinen internen Fehler ausloesen, nur eine leere Vorschlagsliste.
    assert get_completion_option_values("info", "does-not-exist") == ()


def test_show_value_completion_stays_block_type_independent():
    # Regressionsschutz: `show` bleibt blockuebergreifend gleich, unabhaengig
    # vom neuen block-typ-gescopten `type`-Verhalten.
    assert set(get_completion_option_values("lines", "show")) == {"worksheet", "solution", "both"}


def test_free_form_option_without_fixed_catalog_returns_empty_tuple():
    # `rows` bei `lines` ist ein Integer ohne feste Werteliste.
    assert get_completion_option_values("lines", "rows") == ()


def test_self_closing_block_types_contains_exactly_the_bodyless_markers():
    assert get_self_closing_block_types() == {
        "nextcol",
        "endcolumns",
        "pagebreak",
        "framebreak",
        "slidechromeoff",
        "sectionmark",
        "vspacer",
    }


def test_self_closing_block_types_excludes_regular_content_blocks():
    self_closing = get_self_closing_block_types()
    for regular_block_type in ("lines", "grid", "info", "table", "columns"):
        assert regular_block_type not in self_closing
