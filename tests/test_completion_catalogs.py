from app.core.completion_catalogs import (
    get_completion_option_value_abbreviation_hints,
    get_completion_option_values,
    get_completion_options_for_block,
    get_self_closing_block_types,
)


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


def test_value_style_none_preserves_full_unfiltered_value_set():
    # Regressionsschutz: value_style=None (Default) veraendert das Verhalten
    # gegenueber vor Einfuehrung der Sprachstil-Filterung nicht.
    full = get_completion_option_values("task", "work")
    assert get_completion_option_values("task", "work", value_style=None) == full
    assert "einzel" in full and "gruppe" in full


def test_value_style_german_returns_exactly_one_value_per_concept():
    assert set(get_completion_option_values("task", "work", value_style="german")) == {
        "einzel",
        "partner",
        "gruppe",
    }


def test_value_style_english_returns_exactly_one_value_per_concept():
    assert set(get_completion_option_values("task", "work", value_style="english")) == {
        "single",
        "partner",
        "group",
    }


def test_value_style_align_diverges_between_german_and_english_center_justify():
    german = set(get_completion_option_values("lines", "align", value_style="german"))
    english = set(get_completion_option_values("lines", "align", value_style="english"))
    assert german == {"links", "rechts", "mitte", "blocksatz"}
    assert english == {"left", "right", "center", "justify"}


def test_value_style_unknown_allowed_values_falls_back_to_unfiltered():
    # `table.alignment` hat eine eigene, engere Menge -- keine heuristische
    # Teilmengen-Zuordnung zu KNOWN_ALIGN_VALUES.
    styled = get_completion_option_values("table", "alignment", value_style="german")
    unfiltered = get_completion_option_values("table", "alignment")
    assert styled == unfiltered
    assert "mitte" not in styled


def test_abbreviation_hints_differ_by_language_for_same_concept():
    german_hints = get_completion_option_value_abbreviation_hints("lines", "align", "german")
    english_hints = get_completion_option_value_abbreviation_hints("lines", "align", "english")
    assert german_hints["mitte"] == "m"
    assert english_hints["center"] == "c"
    assert german_hints["blocksatz"] == "b"
    assert english_hints["justify"] == "j"


def test_abbreviation_hints_empty_for_option_without_catalog():
    assert get_completion_option_value_abbreviation_hints("info", "type", "german") == {}


def test_completion_options_for_block_excludes_key_aliases_but_keeps_canonical():
    qrcode_options = get_completion_options_for_block("qrcode")
    assert "w" in qrcode_options and "width" not in qrcode_options
    assert "h" in qrcode_options and "height" not in qrcode_options
    assert "maxw" in qrcode_options and "max-width" not in qrcode_options


def test_completion_options_for_block_key_alias_filtering_is_block_scoped():
    # `qrcode.width` ist ein Alias von `w`, aber `table`s eigenes `width`
    # ist primaer/kanonisch und darf nicht mitverschwinden.
    table_options = get_completion_options_for_block("table")
    assert "width" in table_options
    assert "header_columns" in table_options and "header_cols" not in table_options


def test_completion_options_for_block_columns_excludes_ratio_alias():
    columns_options = get_completion_options_for_block("columns")
    assert "widths" in columns_options and "ratio" not in columns_options
