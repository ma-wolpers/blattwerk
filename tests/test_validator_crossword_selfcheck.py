"""Validator: Kreuzworträtsel (CW001 bis CW004) und Selbsteinschätzung (SC001).

Aus `test_blatt_validator.py` nach Themen aufgeteilt (300-Zeilen-Regel), Tests unverändert."""

from app.core.blatt_validator import inspect_markdown_text
from validator_doc_support import build_document


def _crossword_block(words_yaml, options=" maxw=15 maxh=15"):
    return (
        f":::crossword{options}\n"
        f"words:\n{words_yaml}"
        ":::"
    )


def test_crossword_feasible_document_has_no_cw_diagnostics():
    words_yaml = (
        "  - word: SCHULE\n    clue: a\n"
        "  - word: LEHRER\n    clue: b\n"
        "  - word: KREIDE\n    clue: c\n"
        "  - word: TAFEL\n    clue: d\n"
        "  - word: HEFT\n    clue: e\n"
        "  - word: STIFT\n    clue: f\n"
        "  - word: PAUSE\n    clue: g\n"
        "  - word: KLASSE\n    clue: h\n"
    )
    text = build_document(_crossword_block(words_yaml))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert not any(code.startswith("CW") for code in codes)


def test_crossword_infeasible_placement_emits_cw001():
    # HAUS/BAUM/AUTO share the adjacent letter pair "AU", which forces every
    # crossing arrangement into a forbidden "touching without crossing"
    # configuration -- see test_crossword_placement.py for the same,
    # exhaustively-verified infeasible case.
    words_yaml = (
        "  - word: HAUS\n    clue: a\n"
        "  - word: BAUM\n    clue: b\n"
        "  - word: AUTO\n    clue: c\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=12 maxh=12"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW001" in codes


def test_crossword_unassemblable_code_emits_cw002():
    words_yaml = (
        "  - word: SCHULE\n    clue: a\n"
        "  - word: LEHRER\n    clue: b\n"
        "  - word: KREIDE\n    clue: c\n"
        "  - word: TAFEL\n    clue: d\n"
        "  - word: HEFT\n    clue: e\n"
        "  - word: STIFT\n    clue: f\n"
        "  - word: PAUSE\n    clue: g\n"
        "  - word: KLASSE\n    clue: h\n"
    )
    # None of these words contain the letter "O".
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15 code=HALLO"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW002" in codes


def test_crossword_code_row_without_code_emits_cw003():
    words_yaml = "  - word: HAUS\n    clue: a\n"
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15 code_row=true"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW003" in codes


def test_crossword_code_row_with_too_short_code_emits_cw003():
    words_yaml = (
        "  - word: IGEL\n    clue: a\n"
        "  - word: MOND\n    clue: b\n"
        "  - word: HUND\n    clue: c\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15 code_row=true code=AB"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW003" in codes


def test_crossword_valid_code_row_has_no_cw_diagnostics():
    words_yaml = (
        "  - word: IGEL\n    clue: a\n"
        "  - word: MOND\n    clue: b\n"
        "  - word: HUND\n    clue: c\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15 code_row=true code=GEHEIM"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert not any(code.startswith("CW") for code in codes)


def test_crossword_words_differing_only_by_digit_stay_distinct_no_cw004():
    # Crossword normalization keeps digits (unlike wordsearch's) -- "Wort1"
    # and "Wort2" are genuinely different words now, not a collision at
    # all. This is the exact real-world case that used to silently drop
    # the second clue with no diagnostic; it must no longer trigger CW004
    # (there is no duplicate to warn about) and both clues must survive.
    words_yaml = (
        "  - word: Wort1\n    clue: erster Hinweis\n"
        "  - word: Wort2\n    clue: zweiter Hinweis\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW004" not in codes


def test_crossword_duplicate_normalized_word_emits_cw004():
    # A genuine collision (case-only difference, no digits involved).
    words_yaml = (
        "  - word: haus\n    clue: erster Hinweis\n"
        "  - word: HAUS\n    clue: zweiter Hinweis\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW004" in codes


def test_crossword_duplicate_word_still_builds_the_layout():
    # CW004 is a non-blocking warning -- the duplicate word is placed
    # anyway (two independent placements), not silently dropped and not
    # treated as a build-blocking error.
    words_yaml = (
        "  - word: SONNE\n    clue: a\n"
        "  - word: MOND\n    clue: b\n"
        "  - word: STERN\n    clue: c\n"
        "  - word: sonne\n    clue: d\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15"))
    diagnostics = inspect_markdown_text(text).diagnostics
    codes = {d.code for d in diagnostics}
    error_codes = {d.code for d in diagnostics if d.severity == "error"}

    assert "CW004" in codes
    assert "CW001" not in error_codes


def test_crossword_without_duplicate_words_does_not_emit_cw004():
    words_yaml = (
        "  - word: SONNE\n    clue: a\n"
        "  - word: MOND\n    clue: b\n"
        "  - word: STERN\n    clue: c\n"
    )
    text = build_document(_crossword_block(words_yaml, " maxw=15 maxh=15"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "CW004" not in codes


def _selfcheck_block(options=""):
    return f":::selfcheck{options}\n- Aussage\n:::"


def test_selfcheck_steps_in_gap_of_curated_preset_emits_sc001():
    # smiley only curates steps={3, 5} -- 4 falls in the gap between them.
    text = build_document(_selfcheck_block(" scale=smiley steps=4"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" in codes


def test_selfcheck_steps_over_scale_maximum_emits_sc001():
    # ampel only curates steps=3.
    text = build_document(_selfcheck_block(" scale=ampel steps=6"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" in codes


def test_selfcheck_steps_over_global_maximum_emits_sc001():
    text = build_document(_selfcheck_block(" steps=10"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" in codes


def test_selfcheck_steps_under_global_minimum_emits_sc001():
    text = build_document(_selfcheck_block(" steps=1"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" in codes


def test_selfcheck_steps_out_of_global_range_can_emit_two_independent_sc001_diagnostics():
    # steps=10 with the default scale=smiley violates both the global
    # range AND the smiley preset (which doesn't curate 10 either) -- both
    # conditions fire independently, no artificial merging into one.
    text = build_document(_selfcheck_block(" steps=10"))
    diagnostics = [d for d in inspect_markdown_text(text).diagnostics if d.code == "SC001"]

    assert len(diagnostics) == 2


def test_selfcheck_valid_curated_steps_does_not_emit_sc001():
    text = build_document(_selfcheck_block(" scale=smiley steps=5"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" not in codes


def test_selfcheck_scale_without_curated_cap_does_not_emit_sc001_for_scale_mismatch():
    # sterne/zahlen have no curated preset dict at all -- only the global
    # range applies to them, not a scale-specific cap.
    text = build_document(_selfcheck_block(" scale=sterne steps=6"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" not in codes


def test_selfcheck_unparsable_steps_does_not_emit_sc001():
    # Treated the same way the renderer treats it (falls back to the
    # default) -- not itself a bounds violation.
    text = build_document(_selfcheck_block(" steps=abc"))
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" not in codes


def test_selfcheck_without_steps_option_does_not_emit_sc001():
    text = build_document(_selfcheck_block())
    codes = {d.code for d in inspect_markdown_text(text).diagnostics}

    assert "SC001" not in codes
