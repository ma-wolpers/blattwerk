from app.core.crossword_placement import (
    CrosswordEntry,
    build_crossword_layout,
    parse_crossword_entries,
)


def _entries(*words):
    return [CrosswordEntry(word=word, clue="") for word in words]


def test_parse_crossword_entries_reads_words_and_clues():
    content = """
words:
  - word: HAUS
    clue: Wo man wohnt
  - word: BAUM
    clue: Hat Blaetter
"""
    entries = parse_crossword_entries(content)

    assert entries == [
        CrosswordEntry(word="HAUS", clue="Wo man wohnt"),
        CrosswordEntry(word="BAUM", clue="Hat Blaetter"),
    ]


def test_parse_crossword_entries_accepts_german_key_aliases():
    content = """
woerter:
  - lösung: KATZE
    hinweis: Miaut
"""
    entries = parse_crossword_entries(content)

    assert entries == [CrosswordEntry(word="KATZE", clue="Miaut")]


def test_parse_crossword_entries_normalizes_but_keeps_duplicate_words():
    # A word repeated after normalization is no longer silently dropped --
    # both entries (and both distinct clues) are kept; the placement
    # algorithm has no word-uniqueness assumption. Deliberate duplicates
    # are flagged separately via CW004 (see crossword_validation.py), not
    # by discarding content here.
    content = """
words:
  - word: haus
    clue: erste Nennung
  - word: HAUS
    clue: zweite Nennung bleibt erhalten
"""
    entries = parse_crossword_entries(content)

    assert entries == [
        CrosswordEntry(word="HAUS", clue="erste Nennung"),
        CrosswordEntry(word="HAUS", clue="zweite Nennung bleibt erhalten"),
    ]


def test_parse_crossword_entries_rejects_bare_list_root():
    # A bare list at the YAML root (instead of a `words:` mapping) is not the
    # expected shape -- consistent with every other YAML_ANSWER_TYPES block,
    # which requires a dict root (see AN004 in blatt_validator_document.py).
    content = "- word: HAUS\n  clue: Wo man wohnt\n"
    assert parse_crossword_entries(content) == []


def test_parse_crossword_entries_handles_empty_and_invalid_content():
    assert parse_crossword_entries("") == []
    assert parse_crossword_entries("   \n  ") == []
    assert parse_crossword_entries("words: [not, a, dict, :::broken") == []


def test_build_crossword_layout_places_all_words_with_valid_intersections():
    words = ["SCHULE", "LEHRER", "KREIDE", "TAFEL", "HEFT", "STIFT", "PAUSE", "KLASSE"]
    layout = build_crossword_layout(_entries(*words), maxw=15, maxh=15)

    assert layout is not None
    placed_words = {placement.word for placement in layout.placements}
    assert placed_words == set(words)

    cells = layout.cells()
    for placement in layout.placements:
        d_row, d_col = (0, 1) if placement.direction == "H" else (1, 0)
        for index, letter in enumerate(placement.word):
            position = (placement.row + d_row * index, placement.col + d_col * index)
            assert cells[position].letter == letter

    # At least one crossing exists (the words share letters, so a proper
    # crossword should have more than one word fully isolated on its own).
    assert any(len(cell.words) > 1 for cell in cells.values())


def test_build_crossword_layout_is_deterministic_for_identical_inputs():
    words = ["SCHULE", "LEHRER", "KREIDE", "TAFEL", "HEFT", "STIFT", "PAUSE", "KLASSE"]
    first = build_crossword_layout(_entries(*words), maxw=15, maxh=15)
    second = build_crossword_layout(_entries(*words), maxw=15, maxh=15)

    assert first == second


def test_build_crossword_layout_returns_none_when_a_word_cannot_possibly_fit():
    layout = build_crossword_layout(_entries("ELEFANTENHAUS"), maxw=5, maxh=5)
    assert layout is None


def test_build_crossword_layout_returns_none_for_empty_entries():
    assert build_crossword_layout([], maxw=10, maxh=10) is None


def test_build_crossword_layout_returns_none_gracefully_when_geometrically_infeasible():
    # HAUS/BAUM/AUTO all share the adjacent letter pair "AU", which forces
    # every possible crossing arrangement of the three into a forbidden
    # "words touching without crossing" configuration in this bounded grid --
    # a real, verified-by-exhaustive-search infeasible case, not a crash.
    layout = build_crossword_layout(_entries("HAUS", "BAUM", "AUTO"), maxw=12, maxh=12)
    assert layout is None


def test_build_crossword_layout_no_two_parallel_words_touch_without_crossing():
    words = ["SCHULE", "LEHRER", "KREIDE", "TAFEL", "HEFT", "STIFT", "PAUSE", "KLASSE"]
    layout = build_crossword_layout(_entries(*words), maxw=15, maxh=15)
    assert layout is not None

    cells = layout.cells()
    for placement in layout.placements:
        d_row, d_col = (0, 1) if placement.direction == "H" else (1, 0)
        perpendicular = (1, 0) if placement.direction == "H" else (0, 1)
        for index, letter in enumerate(placement.word):
            row = placement.row + d_row * index
            col = placement.col + d_col * index
            is_intersection = len(cells[(row, col)].words) > 1
            if is_intersection:
                continue
            for n_row, n_col in (
                (row - perpendicular[0], col - perpendicular[1]),
                (row + perpendicular[0], col + perpendicular[1]),
            ):
                neighbour = cells.get((n_row, n_col))
                assert neighbour is None, (
                    f"{placement.word} cell ({row},{col}) touches an unrelated "
                    f"letter at ({n_row},{n_col}) without crossing it"
                )


def test_build_crossword_layout_code_row_places_code_word_as_its_own_row():
    entries = _entries("IGEL", "MOND", "HUND")
    layout = build_crossword_layout(entries, maxw=15, maxh=15, code_row=True, code_word="GEHEIM")

    assert layout is not None
    code_placement = next(p for p in layout.placements if p.is_code_row)
    assert code_placement.word == "GEHEIM"
    assert code_placement.direction == "H"

    # Every regular word must be vertical and cross the code row.
    regular_placements = [p for p in layout.placements if not p.is_code_row]
    assert {p.word for p in regular_placements} == {"IGEL", "MOND", "HUND"}
    for placement in regular_placements:
        assert placement.direction == "V"
        crosses_code_row = (
            placement.row <= code_placement.row < placement.row + len(placement.word)
        )
        assert crosses_code_row


def test_build_crossword_layout_code_row_rejects_code_word_shorter_than_entry_count():
    # Every regular word needs its own crossing position on the code row --
    # a code word shorter than the entry count can't provide that.
    entries = _entries("IGEL", "MOND", "HUND", "REGEN")
    layout = build_crossword_layout(entries, maxw=15, maxh=15, code_row=True, code_word="AB")
    assert layout is None


def test_build_crossword_layout_code_row_rejects_code_word_longer_than_maxw():
    layout = build_crossword_layout(
        _entries("IGEL"), maxw=5, maxh=15, code_row=True, code_word="GEHEIMNIS"
    )
    assert layout is None
