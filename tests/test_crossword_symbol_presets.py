from app.core.crossword_symbol_presets import ALL_SYMBOL_THEMES, SYMBOL_THEME_NAMES, symbol_theme_by_name


def test_symbol_theme_by_name_returns_matching_theme():
    theme = symbol_theme_by_name("fruits")
    assert theme is not None
    assert theme.name == "fruits"
    assert len(theme.labels) > 0


def test_symbol_theme_by_name_returns_none_for_unknown_name():
    assert symbol_theme_by_name("does-not-exist") is None


def test_symbol_theme_names_matches_all_themes():
    assert SYMBOL_THEME_NAMES == frozenset(theme.name for theme in ALL_SYMBOL_THEMES)


def test_each_theme_has_no_duplicate_labels():
    for theme in ALL_SYMBOL_THEMES:
        assert len(set(theme.labels)) == len(theme.labels), f"duplicate label in theme {theme.name!r}"
