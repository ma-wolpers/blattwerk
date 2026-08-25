"""Deterministic code-word cell selection for the `crossword` block's `code=` option.

Split out of `crossword_placement.py` to keep both files well under the
project's ~300-line convention (see `docs/ARCHITEKTUR.md`) -- placement and
code-selection are two separate `BlockComputationCache` computations (plan
Slice 2) and were already conceptually independent.
"""

from __future__ import annotations

from dataclasses import dataclass

from .crossword_placement import CrosswordLayout

_MAX_CODE_SELECTION_ATTEMPTS = 5000
"""Defensive backtracking-step budget, mirroring `crossword_placement.py`'s
`_MAX_PLACEMENT_ATTEMPTS` -- code words are short in practice, so this is
never expected to bind, only to guard against a pathological candidate set."""


@dataclass(frozen=True)
class CrosswordCodeLetter:
    """One resolved code-word letter: which grid cell spells it, and which
    placed word(s) that cell belongs to (for solution-mode highlighting)."""

    letter: str
    row: int
    col: int
    words: tuple[str, ...]


@dataclass(frozen=True)
class CrosswordCodeSelection:
    """The complete, ordered cell assignment for every letter of `code_word`."""

    letters: tuple[CrosswordCodeLetter, ...]


def validate_crossword_code(layout: CrosswordLayout, code_word: str) -> CrosswordCodeSelection | None:
    """Finds a cell assignment spelling `code_word` out of `layout`'s placed letters.

    `code_word` is a freely author-chosen string with no semantic relation
    to the clues (plan Slice 2, section 2.3) -- this only checks "can this
    specific string be spelled using letters already on the grid".

    Two paths:
    - `code_row=True` layouts (one `CrosswordPlacement` has `is_code_row=True`):
      the code word already runs as its own grid row by construction, so its
      cells are simply read off left to right -- no search needed.
    - Otherwise: a preference-ordered search over `layout`'s cells, honoring
      (in priority order) (1) spreading letters evenly across words rather
      than reusing one word early, (2) slightly preferring non-intersection
      cells over cells shared by two words, (3) deterministic position
      tie-breaks. Backtracks across the full candidate space when the
      preferred choice at some letter turns out to make a later letter
      unsatisfiable, so a solution is returned whenever the candidate cells
      permit one -- not just when the greedy-preferred path happens to work.

    Returns `None` when no valid assignment exists (callers turn that into
    a `CW002` diagnostic).
    """
    code_row_placement = next((p for p in layout.placements if p.is_code_row), None)
    if code_row_placement is not None:
        return _code_selection_from_code_row(layout, code_row_placement, code_word)
    return _code_selection_via_search(layout, code_word)


def _code_selection_from_code_row(layout, code_row_placement, code_word):
    if code_row_placement.word != code_word:
        return None

    cell_map = layout.cells()
    letters = []
    for index, letter in enumerate(code_word):
        position = (code_row_placement.row, code_row_placement.col + index)
        cell = cell_map.get(position)
        if cell is None:
            return None
        letters.append(CrosswordCodeLetter(letter=letter, row=position[0], col=position[1], words=cell.words))
    return CrosswordCodeSelection(letters=tuple(letters))


def _code_selection_via_search(layout, code_word):
    if not code_word:
        return CrosswordCodeSelection(letters=())

    order_index = {placement.word: index for index, placement in enumerate(layout.placements)}
    candidates_by_letter: dict[str, list[dict]] = {}
    for (row, col), cell in sorted(layout.cells().items()):
        candidates_by_letter.setdefault(cell.letter, []).append(
            {
                "row": row,
                "col": col,
                "is_intersection": len(cell.words) > 1,
                "words": cell.words,
            }
        )

    attempts_remaining = [_MAX_CODE_SELECTION_ATTEMPTS]

    def _search(letter_index, used_cells, usage_count):
        if letter_index >= len(code_word):
            return []

        letter = code_word[letter_index]
        options = [
            option
            for option in candidates_by_letter.get(letter, [])
            if (option["row"], option["col"]) not in used_cells
        ]

        def _sort_key(option):
            least_used_word_count = min(usage_count.get(word, 0) for word in option["words"])
            return (
                least_used_word_count,
                option["is_intersection"],
                min(order_index.get(word, 0) for word in option["words"]),
                option["row"],
                option["col"],
            )

        options.sort(key=_sort_key)

        for option in options:
            if attempts_remaining[0] <= 0:
                return None
            attempts_remaining[0] -= 1

            next_used = used_cells | {(option["row"], option["col"])}
            next_usage = dict(usage_count)
            for word in option["words"]:
                next_usage[word] = next_usage.get(word, 0) + 1

            rest = _search(letter_index + 1, next_used, next_usage)
            if rest is not None:
                chosen = CrosswordCodeLetter(
                    letter=letter,
                    row=option["row"],
                    col=option["col"],
                    words=option["words"],
                )
                return [chosen] + rest

        return None

    resolved = _search(0, frozenset(), {})
    if resolved is None:
        return None
    return CrosswordCodeSelection(letters=tuple(resolved))
