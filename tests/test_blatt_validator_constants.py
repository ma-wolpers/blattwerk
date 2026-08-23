from app.core.blatt_validator_constants import (
    BLOCK_ALLOWED_OPTIONS,
    BLOCK_OPTION_KEY_ALIASES,
    OPTION_VALUE_STYLE_CATALOGS,
)


def test_every_catalogued_style_value_is_in_its_known_values_set():
    for known_set, style_table in OPTION_VALUE_STYLE_CATALOGS:
        for concept in style_table:
            for style in ("english", "german"):
                if style in concept:
                    assert concept[style] in known_set, (
                        f"{concept[style]!r} ({style}) fehlt in der zugehoerigen KNOWN_*_VALUES-Menge"
                    )


def test_every_catalogued_abbreviation_is_in_its_known_values_set():
    for known_set, style_table in OPTION_VALUE_STYLE_CATALOGS:
        for concept in style_table:
            for field in ("abbreviation_english", "abbreviation_german"):
                if field in concept:
                    assert concept[field] in known_set, (
                        f"{concept[field]!r} ({field}) fehlt in der zugehoerigen KNOWN_*_VALUES-Menge"
                    )


def test_every_concept_defines_both_english_and_german_forms():
    # Der Resolver darf nie auf einen fehlenden Pflichtschluessel treffen.
    for _known_set, style_table in OPTION_VALUE_STYLE_CATALOGS:
        for concept in style_table:
            assert "english" in concept and concept["english"], concept
            assert "german" in concept and concept["german"], concept


def test_no_duplicate_abbreviation_within_the_same_option_and_language():
    for _known_set, style_table in OPTION_VALUE_STYLE_CATALOGS:
        for field in ("abbreviation_english", "abbreviation_german"):
            abbreviations = [concept[field] for concept in style_table if field in concept]
            assert len(abbreviations) == len(set(abbreviations)), (
                f"Doppelte Abkuerzung in {field}: {abbreviations}"
            )


def test_key_aliases_are_valid_option_keys_of_their_block():
    for block_type, aliases in BLOCK_OPTION_KEY_ALIASES.items():
        allowed = BLOCK_ALLOWED_OPTIONS.get(block_type, frozenset())
        for alias in aliases:
            assert alias in allowed, f"{alias!r} ist keine bekannte Option von {block_type!r}"


def test_key_aliases_leave_at_least_one_non_alias_option_key_per_block():
    # Es muss immer mindestens eine kanonische, nicht ausgeblendete Form
    # uebrigbleiben -- sonst waere die Option komplett aus der Completion
    # verschwunden statt nur konsolidiert.
    for block_type, aliases in BLOCK_OPTION_KEY_ALIASES.items():
        allowed = BLOCK_ALLOWED_OPTIONS.get(block_type, frozenset())
        assert allowed - aliases, f"{block_type!r} haette keine verbleibenden Options-Vorschlaege"
