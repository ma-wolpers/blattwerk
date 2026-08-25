"""Two-pass clue-numbering for crossword grids.

Deliberately **not** the standard single combined row-major pass over every
word start -- the author-specified convention (verified with the user) is:
first number every *horizontal* word start in row-major order, then a
*second* full row-major scan numbers every *vertical* word start that
wasn't already numbered in the first pass. A cell starting both a
horizontal and a vertical word keeps its pass-1 number.
"""

from __future__ import annotations

from dataclasses import dataclass

from .crossword_placement import CrosswordLayout


@dataclass(frozen=True)
class CrosswordNumbering:
    """`(row, col) -> clue number` for every placement's start cell.

    A standalone structure, not attached to `CrosswordLayout` -- the layout
    is a cached, potentially cross-pass-shared computation result
    (`BlockComputationCache`, see `block_computation_cache.py`) and must
    never be mutated with rendering-only metadata once computed.
    """

    numbers: dict[tuple[int, int], int]


def assign_crossword_numbers(layout: CrosswordLayout) -> CrosswordNumbering:
    """Runs the two-pass numbering described above over `layout`.

    The `code_row=True` code-word placement (`CrosswordPlacement.is_code_row`)
    is excluded from both passes -- it has no clue entry, so numbering it
    would produce a number with no matching item in the clue list.
    """
    horizontal_starts = set()
    vertical_starts = set()
    for placement in layout.placements:
        if placement.is_code_row:
            continue
        if placement.direction == "H":
            horizontal_starts.add((placement.row, placement.col))
        else:
            vertical_starts.add((placement.row, placement.col))

    numbers: dict[tuple[int, int], int] = {}
    counter = 1
    for row in range(layout.rows):
        for col in range(layout.cols):
            if (row, col) in horizontal_starts:
                numbers[(row, col)] = counter
                counter += 1
    for row in range(layout.rows):
        for col in range(layout.cols):
            if (row, col) in vertical_starts and (row, col) not in numbers:
                numbers[(row, col)] = counter
                counter += 1

    return CrosswordNumbering(numbers=numbers)


def grouped_clues(layout: CrosswordLayout, numbering: CrosswordNumbering, entries):
    """Builds `(horizontal, vertical)` clue lists, each `(number, word, clue)`
    tuples sorted by number -- the shape `answer_special_crossword.py` needs
    for the "Waagerecht"/"Senkrecht" clue lists, without itself having to
    know about numbering internals."""
    clue_by_word = {entry.word: entry.clue for entry in entries}
    horizontal = []
    vertical = []
    for placement in layout.placements:
        if placement.is_code_row:
            continue
        number = numbering.numbers.get((placement.row, placement.col))
        if number is None:
            continue
        clue = clue_by_word.get(placement.word, "")
        target = horizontal if placement.direction == "H" else vertical
        target.append((number, placement.word, clue))

    horizontal.sort(key=lambda item: item[0])
    vertical.sort(key=lambda item: item[0])
    return horizontal, vertical
