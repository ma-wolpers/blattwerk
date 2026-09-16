from app.core.completion_catalogs import (
    get_completion_block_type_detail,
    get_completion_frontmatter_field_detail,
    get_completion_frontmatter_field_values,
    get_completion_operator_details,
    get_completion_operator_forms,
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


def test_completion_options_for_block_columns_excludes_ratio_alias():
    columns_options = get_completion_options_for_block("columns")
    assert "widths" in columns_options and "ratio" not in columns_options


def test_frontmatter_field_completion_returns_stufe_values():
    assert get_completion_frontmatter_field_values("Stufe") == (
        "10", "11", "12", "13", "5", "6", "7", "8", "9", "e", "q1", "q2", "sek1", "sek2",
    )


def test_frontmatter_field_completion_returns_existing_enum_fields_unaffected():
    # Regression: adding Stufe must not change already-working enum fields.
    assert get_completion_frontmatter_field_values("mode") == (
        "presentation", "solution", "test", "worksheet", "ws",
    )
    assert get_completion_frontmatter_field_values("document_type") == (
        "kurzentwurf", "presentation", "worksheet",
    )


def test_frontmatter_field_completion_empty_for_non_enum_field():
    assert get_completion_frontmatter_field_values("copyright") == ()


def test_frontmatter_field_completion_empty_for_unknown_field():
    assert get_completion_frontmatter_field_values("does_not_exist") == ()


def test_operator_forms_completion_returns_official_labels_for_mathematik():
    suggestions = get_completion_operator_forms("Mathematik", None)
    assert "Bestimmen" in suggestions
    assert "Ermitteln" in suggestions


def test_operator_forms_completion_filters_by_stufe():
    assert "Begründen" in get_completion_operator_forms("Mathematik", "Q1")
    assert "Begründen" not in get_completion_operator_forms("Mathematik", "7")


def test_operator_forms_completion_empty_for_unknown_fach():
    assert get_completion_operator_forms("Chemie", None) == ()


def test_operator_details_completion_covers_every_suggested_label():
    labels = get_completion_operator_forms("Mathematik", None)
    details = get_completion_operator_details("Mathematik", None)
    assert set(details.keys()) == set(labels)
    assert details["Bestimmen"]["title"] == "Bestimmen"
    assert details["Bestimmen"]["description"]  # real, non-empty prose
    assert details["Bestimmen"]["value_hint"] is None


def test_operator_details_completion_empty_for_unknown_fach():
    assert get_completion_operator_details("Chemie", None) == {}


def test_frontmatter_field_detail_enum_with_default_shows_standard_hint():
    detail = get_completion_frontmatter_field_detail("mode")
    assert detail is not None
    assert detail["title"] == "mode"
    assert detail["description"]
    assert detail["value_hint"] == "Standard: worksheet"


def test_frontmatter_field_detail_enum_without_default_shows_moeglicher_wert_hint():
    # `Stufe` has allowed_values but no `default` -- must never be labelled
    # "Beispiel", only the neutral "Möglicher Wert".
    detail = get_completion_frontmatter_field_detail("Stufe")
    assert detail is not None
    assert detail["value_hint"] is not None
    assert detail["value_hint"].startswith("Möglicher Wert: ")
    assert "Beispiel" not in detail["value_hint"]


def test_frontmatter_field_detail_boolean_default_renders_as_ja_nein_not_python_bool():
    detail = get_completion_frontmatter_field_detail("show_student_header")
    assert detail is not None
    assert detail["value_hint"] == "Standard: nein"


def test_frontmatter_field_detail_free_text_field_has_no_value_hint():
    detail = get_completion_frontmatter_field_detail("copyright")
    assert detail is not None
    assert detail["description"]
    assert detail["value_hint"] is None


def test_frontmatter_field_detail_required_field_has_description_but_no_value_hint():
    # "Titel"/"Fach"/"Thema" aren't in OPTIONAL_FRONTMATTER_FIELDS at all
    # (they're required, not optional) -- still get a description from
    # PROSE_SECTIONS, just no default/allowed_values to hint at.
    detail = get_completion_frontmatter_field_detail("Titel")
    assert detail is not None
    assert detail["description"]
    assert detail["value_hint"] is None


def test_frontmatter_field_detail_unknown_field_returns_none():
    assert get_completion_frontmatter_field_detail("does_not_exist") is None


def test_block_type_detail_returns_description_without_value_hint():
    detail = get_completion_block_type_detail("info")
    assert detail is not None
    assert detail["title"] == "info"
    assert detail["description"]
    assert detail["value_hint"] is None


def test_block_type_detail_unknown_type_returns_none():
    assert get_completion_block_type_detail("does-not-exist") is None
