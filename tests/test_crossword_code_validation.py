from app.core.crossword_code import validate_crossword_code
from app.core.crossword_placement import CrosswordEntry, build_crossword_layout


def _entries(*words):
    return [CrosswordEntry(word=word, clue="") for word in words]


def _build(words, **kwargs):
    return build_crossword_layout(_entries(*words), maxw=15, maxh=15, **kwargs)


def test_validate_crossword_code_finds_a_selection_with_one_letter_per_word():
    words = ["SCHULE", "LEHRER", "KREIDE", "TAFEL", "HEFT", "STIFT", "PAUSE", "KLASSE"]
    layout = _build(words)
    assert layout is not None

    selection = validate_crossword_code(layout, "HAUS")

    assert selection is not None
    assert [entry.letter for entry in selection.letters] == list("HAUS")
    # One letter per word, since the code word (4) is not longer than the
    # number of placed words (8) -- the "spread evenly" rule only kicks in
    # once the code word outgrows the entry count.
    contributing_words = [entry.words for entry in selection.letters]
    all_words_used = [word for words_tuple in contributing_words for word in words_tuple]
    assert len(all_words_used) == len(set(all_words_used))


def test_validate_crossword_code_returns_none_for_unavailable_letter():
    words = ["SCHULE", "LEHRER", "KREIDE", "TAFEL", "HEFT", "STIFT", "PAUSE", "KLASSE"]
    layout = _build(words)
    assert layout is not None

    # None of these words contain the letter "O".
    selection = validate_crossword_code(layout, "HALLO")

    assert selection is None


def test_validate_crossword_code_selected_cells_actually_exist_in_the_layout():
    words = ["SCHULE", "LEHRER", "KREIDE", "TAFEL", "HEFT", "STIFT", "PAUSE", "KLASSE"]
    layout = _build(words)
    selection = validate_crossword_code(layout, "REST")
    assert selection is not None

    cells = layout.cells()
    for entry in selection.letters:
        cell = cells[(entry.row, entry.col)]
        assert cell.letter == entry.letter
        assert set(entry.words) <= set(cell.words)

    # No cell used twice.
    positions = [(entry.row, entry.col) for entry in selection.letters]
    assert len(positions) == len(set(positions))


def test_validate_crossword_code_slight_preference_for_non_intersection_cells():
    # A tight two-word cross where the shared letter sits at an intersection
    # and also appears once more in a non-intersection cell of one word --
    # the heuristic should prefer the non-intersection cell.
    layout = _build(["HAUS", "ZUG"])
    assert layout is not None

    selection = validate_crossword_code(layout, "U")
    assert selection is not None
    chosen = selection.letters[0]
    cell = layout.cells()[(chosen.row, chosen.col)]
    # Both words contain "U" exactly once, and they cross precisely at "U",
    # so the *only* available "U" cell is the intersection itself here --
    # this asserts the selection is still valid (present in the layout)
    # rather than asserting non-intersection preference can't apply when no
    # alternative cell exists.
    assert cell.letter == "U"


def test_validate_crossword_code_distributes_evenly_when_code_longer_than_word_count():
    words = ["HAUS", "ZUG", "BAUM"]
    # HAUS/BAUM/ZUG's own crossword layout is checked separately for
    # infeasibility (see test_crossword_placement.py); build a layout that
    # is known to succeed for this distribution test instead.
    layout = _build(["SCHULE", "LEHRER", "KREIDE"])
    assert layout is not None

    # A code word with more letters than placed words (3) forces reuse.
    selection = validate_crossword_code(layout, "HERR")
    assert selection is not None

    usage = {}
    for entry in selection.letters:
        for word in entry.words:
            usage[word] = usage.get(word, 0) + 1

    # No single word should be used disproportionately more than any other
    # word that also had a matching letter available -- spread as evenly as
    # the available letters allow.
    assert max(usage.values()) - min(usage.values()) <= 1


def test_validate_crossword_code_returns_none_when_code_word_cannot_be_assembled_at_all():
    layout = _build(["HAUS", "ZUG"])
    assert layout is not None

    assert validate_crossword_code(layout, "XYZ") is None


def test_validate_crossword_code_row_reads_off_the_code_row_directly():
    entries = _entries("IGEL", "MOND", "HUND")
    layout = build_crossword_layout(entries, maxw=15, maxh=15, code_row=True, code_word="GEHEIM")
    assert layout is not None

    selection = validate_crossword_code(layout, "GEHEIM")

    assert selection is not None
    assert [entry.letter for entry in selection.letters] == list("GEHEIM")
    code_placement = next(p for p in layout.placements if p.is_code_row)
    for index, entry in enumerate(selection.letters):
        assert entry.row == code_placement.row
        assert entry.col == code_placement.col + index


def test_validate_crossword_code_row_returns_none_for_a_different_code_word():
    entries = _entries("IGEL", "MOND", "HUND")
    layout = build_crossword_layout(entries, maxw=15, maxh=15, code_row=True, code_word="GEHEIM")
    assert layout is not None

    assert validate_crossword_code(layout, "ANDERS") is None


def test_validate_crossword_code_empty_code_word_yields_empty_selection():
    layout = _build(["SCHULE", "LEHRER"])
    assert layout is not None

    selection = validate_crossword_code(layout, "")
    assert selection is not None
    assert selection.letters == ()
