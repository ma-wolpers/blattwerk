from app.core.crossword_numbering import assign_crossword_numbers, grouped_clues
from app.core.crossword_placement import CrosswordEntry, CrosswordLayout, CrosswordPlacement


def test_two_pass_numbering_orders_all_horizontal_starts_before_vertical_starts():
    # A hand-built layout (not run through the placement search) so the
    # exact expected numbering can be reasoned about directly:
    #   row0: horizontal word starting at (0,0)
    #   row1: horizontal word starting at (1,2)
    #   a vertical word starting at (0,5) -- earlier row than both
    #   horizontals, but must still be numbered *after* all horizontals.
    layout = CrosswordLayout(
        rows=5,
        cols=8,
        placements=(
            CrosswordPlacement(word="ABC", row=0, col=0, direction="H"),
            CrosswordPlacement(word="DEF", row=1, col=2, direction="H"),
            CrosswordPlacement(word="GHI", row=0, col=5, direction="V"),
        ),
    )

    numbering = assign_crossword_numbers(layout)

    assert numbering.numbers[(0, 0)] == 1
    assert numbering.numbers[(1, 2)] == 2
    assert numbering.numbers[(0, 5)] == 3


def test_cell_starting_both_directions_keeps_pass_one_number():
    layout = CrosswordLayout(
        rows=4,
        cols=4,
        placements=(
            CrosswordPlacement(word="AB", row=1, col=1, direction="H"),
            CrosswordPlacement(word="AC", row=1, col=1, direction="V"),
        ),
    )

    numbering = assign_crossword_numbers(layout)

    assert numbering.numbers == {(1, 1): 1}


def test_row_major_order_within_each_pass():
    layout = CrosswordLayout(
        rows=5,
        cols=5,
        placements=(
            CrosswordPlacement(word="AB", row=2, col=0, direction="H"),
            CrosswordPlacement(word="CD", row=0, col=3, direction="H"),
            CrosswordPlacement(word="EF", row=1, col=0, direction="V"),
            CrosswordPlacement(word="GH", row=0, col=1, direction="V"),
        ),
    )

    numbering = assign_crossword_numbers(layout)

    # Horizontals first, row-major: (0,3) before (2,0).
    assert numbering.numbers[(0, 3)] == 1
    assert numbering.numbers[(2, 0)] == 2
    # Then verticals, row-major: (0,1) before (1,0).
    assert numbering.numbers[(0, 1)] == 3
    assert numbering.numbers[(1, 0)] == 4


def test_code_row_placement_is_excluded_from_numbering():
    layout = CrosswordLayout(
        rows=3,
        cols=6,
        placements=(
            CrosswordPlacement(word="GEHEIM", row=1, col=0, direction="H", is_code_row=True),
            CrosswordPlacement(word="IG", row=0, col=0, direction="V"),
        ),
    )

    numbering = assign_crossword_numbers(layout)

    assert (1, 0) not in numbering.numbers
    assert numbering.numbers == {(0, 0): 1}


def test_grouped_clues_splits_by_direction_and_sorts_by_number():
    layout = CrosswordLayout(
        rows=5,
        cols=5,
        placements=(
            CrosswordPlacement(word="AB", row=2, col=0, direction="H"),
            CrosswordPlacement(word="CD", row=0, col=3, direction="H"),
            CrosswordPlacement(word="EF", row=1, col=0, direction="V"),
        ),
    )
    entries = [
        CrosswordEntry(word="AB", clue="Hinweis AB"),
        CrosswordEntry(word="CD", clue="Hinweis CD"),
        CrosswordEntry(word="EF", clue="Hinweis EF"),
    ]
    numbering = assign_crossword_numbers(layout)

    horizontal, vertical = grouped_clues(layout, numbering, entries)

    assert horizontal == [(1, "CD", "Hinweis CD"), (2, "AB", "Hinweis AB")]
    assert vertical == [(3, "EF", "Hinweis EF")]


def test_grouped_clues_excludes_code_row_placement():
    layout = CrosswordLayout(
        rows=3,
        cols=6,
        placements=(
            CrosswordPlacement(word="GEHEIM", row=1, col=0, direction="H", is_code_row=True),
            CrosswordPlacement(word="IG", row=0, col=0, direction="V"),
        ),
    )
    entries = [CrosswordEntry(word="IG", clue="Hinweis IG")]
    numbering = assign_crossword_numbers(layout)

    horizontal, vertical = grouped_clues(layout, numbering, entries)

    assert horizontal == []
    assert vertical == [(1, "IG", "Hinweis IG")]
