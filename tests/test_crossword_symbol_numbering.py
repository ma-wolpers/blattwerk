"""Tests for the crossword position-numbering styles (`numbering=`/`code_numbering=`)
introduced alongside `crossword_symbol_presets.py`: label formatting and the
`CW005` symbol-overflow diagnostic.
"""

from app.core.answer_special_crossword import _format_number_label
from app.core.blatt_validator import inspect_markdown_text
from app.core.crossword_symbol_presets import symbol_theme_by_name


def _build_document(answer_block):
    return (
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "---\n"
        f"{answer_block}\n"
    )


def _crossword_block(words_yaml, options):
    return f":::crossword{options}\nwords:\n{words_yaml}:::"


def test_format_number_label_numeric():
    assert _format_number_label(3, "numeric", "fruits") == "3"


def test_format_number_label_letters():
    assert _format_number_label(1, "letters", "fruits") == "A"
    assert _format_number_label(27, "letters", "fruits") == "AA"


def test_format_number_label_symbols_looks_up_theme_by_index():
    theme = symbol_theme_by_name("fruits")
    assert _format_number_label(1, "symbols", "fruits") == theme.labels[0]
    assert _format_number_label(5, "symbols", "fruits") == theme.labels[4]


def test_crossword_numbering_symbols_overflow_emits_cw005(monkeypatch):
    import app.core.crossword_validation as crossword_validation
    from app.core.crossword_symbol_presets import SymbolTheme

    monkeypatch.setattr(
        crossword_validation,
        "symbol_theme_by_name",
        lambda name: SymbolTheme(name, ("🍎",)),
    )

    words_yaml = "  - word: HAUS\n    clue: a\n  - word: ZUG\n    clue: b\n"
    text = _build_document(_crossword_block(words_yaml, " maxw=15 maxh=15 numbering=symbols symbol_set=fruits"))
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "CW005" in codes


def test_crossword_numbering_symbols_no_overflow_stays_clean():
    words_yaml = "  - word: HAUS\n    clue: a\n  - word: ZUG\n    clue: b\n"
    text = _build_document(_crossword_block(words_yaml, " maxw=15 maxh=15 numbering=symbols symbol_set=fruits"))
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "CW005" not in codes


def test_crossword_code_numbering_symbols_overflow_emits_cw005(monkeypatch):
    import app.core.crossword_validation as crossword_validation
    from app.core.crossword_symbol_presets import SymbolTheme

    monkeypatch.setattr(
        crossword_validation,
        "symbol_theme_by_name",
        lambda name: SymbolTheme(name, ("🍎",)),
    )

    words_yaml = (
        "  - word: SCHULE\n    clue: a\n"
        "  - word: LEHRER\n    clue: b\n"
        "  - word: KREIDE\n    clue: c\n"
    )
    text = _build_document(
        _crossword_block(
            words_yaml,
            " maxw=15 maxh=15 code=ER code_numbering=symbols code_symbol_set=fruits",
        )
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "CW005" in codes


def test_crossword_code_numbering_symbols_no_overflow_stays_clean():
    words_yaml = (
        "  - word: SCHULE\n    clue: a\n"
        "  - word: LEHRER\n    clue: b\n"
        "  - word: KREIDE\n    clue: c\n"
    )
    text = _build_document(
        _crossword_block(
            words_yaml,
            " maxw=15 maxh=15 code=ER code_numbering=symbols code_symbol_set=fruits",
        )
    )
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}

    assert "CW005" not in codes
