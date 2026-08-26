"""Crossword entry parsing and deterministic intersecting word placement.

Pure domain logic, no HTML -- see `answer_special_crossword.py` for
rendering and `crossword_numbering.py` for the clue-numbering pass.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

import yaml

_CROSSWORD_ALGORITHM_VERSION = 2
"""Bumped whenever placement/candidate-ranking logic changes, so stale
`BlockComputationCache` entries from an older algorithm version are never
silently reused (see `app/core/block_computation_cache.py`). Bumped to 2
when word normalization started keeping digits (see
`_normalize_crossword_token`) -- a cached layout computed under the old,
digit-stripping normalization must never be served for the new one."""

_CROSSWORD_TOKEN_PATTERN = re.compile(r"[^A-Za-z0-9ÄÖÜäöü]")


def _normalize_crossword_token(word):
    """Normalizes a crossword word/code-word to an upper-case token, keeping digits.

    Deliberately **not** `wordsearch_placement.py::_normalize_wordsearch_token`
    (which strips digits too) -- for a wordsearch grid every cell is
    genuinely just a letter, but a crossword answer's digits are part of
    its actual identity (e.g. distinguishing `Wort1`/`Wort2`, or an answer
    like `H2O`). Stripping them silently collapsed distinct author-intended
    words into the same normalized string. Still strips everything else
    (whitespace, punctuation) -- a placed word is one character per grid
    cell, so it must stay a single contiguous token either way.
    """
    if word is None:
        return ""
    text = str(word).strip()
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    text = _CROSSWORD_TOKEN_PATTERN.sub("", text)
    return text.upper()


_DIRECTION_DELTAS = {"H": (0, 1), "V": (1, 0)}
_MAX_CANDIDATES_PER_WORD = 40
_MAX_PLACEMENT_ATTEMPTS = 20000
"""Global backtracking step budget -- a defensive guard against pathological
word lists producing runaway recursion; ordinary worksheet-sized crossword
lists (a handful to a few dozen words) never come close to this."""


@dataclass(frozen=True)
class CrosswordEntry:
    """One clued crossword word, as authored (word already normalized)."""

    word: str
    clue: str


@dataclass(frozen=True)
class CrosswordPlacement:
    """One placed word: its top-left start cell, reading direction, and clue.

    `clue` is carried directly from the originating `CrosswordEntry` at
    placement time (see `build_crossword_layout`), not looked up by word
    text afterwards -- `crossword_numbering.py::grouped_clues` used to
    build a `{word: clue}` dict from `entries` and look each placement's
    clue up by its word string, which silently collapsed two entries that
    share the same word (deliberately allowed, see `parse_crossword_entries`)
    onto a single clue. Carrying the clue on the placement itself makes that
    class of bug structurally impossible: each placement is definitionally
    tied to the one entry it came from, regardless of what any other entry's
    word happens to be. `is_code_row` marks the special `code_row=True`
    code-word placement (see Slice 2 plan section 2.3) -- it has no clue
    (default `""`) and must be excluded from clue-numbering.
    """

    word: str
    row: int
    col: int
    direction: str  # "H" or "V"
    clue: str = ""
    is_code_row: bool = False


@dataclass(frozen=True)
class CrosswordCell:
    """A single occupied grid cell: its letter and the word(s) covering it."""

    letter: str
    words: tuple[str, ...]


@dataclass(frozen=True)
class CrosswordLayout:
    """A complete, successfully placed crossword grid."""

    rows: int
    cols: int
    placements: tuple[CrosswordPlacement, ...]

    def cells(self) -> dict[tuple[int, int], CrosswordCell]:
        """Builds the (row, col) -> CrosswordCell map from `placements`.

        Recomputed on demand rather than cached on the (frozen) dataclass --
        crossword grids are small enough that this is cheap, and it keeps
        `CrosswordLayout` a plain, JSON-round-trippable value.
        """
        letters: dict[tuple[int, int], str] = {}
        owners: dict[tuple[int, int], list[str]] = {}
        for placement in self.placements:
            d_row, d_col = _DIRECTION_DELTAS[placement.direction]
            for index, letter in enumerate(placement.word):
                position = (placement.row + d_row * index, placement.col + d_col * index)
                letters[position] = letter
                owners.setdefault(position, []).append(placement.word)
        return {
            position: CrosswordCell(letter=letters[position], words=tuple(owners[position]))
            for position in letters
        }


def parse_crossword_entries(content: str) -> list[CrosswordEntry]:
    """Parses the `:::crossword` YAML content into normalized entries.

    Expected shape (a dict at the YAML root, consistent with every other
    `YAML_ANSWER_TYPES` block type -- a bare list at the root would trip the
    generic `AN004` "expected mapping" validator diagnosis):

        words:
          - word: HAUS
            clue: Wo man wohnt
          - lösung: BAUM
            hinweis: Hat Blätter

    Accepts `words`/`woerter`/`wörter` as the root key and `word`/`wort`/
    `lösung`/`loesung` plus `clue`/`hinweis` as per-entry key aliases.
    Entries with an empty/unnormalizable word are skipped. Unlike
    `parse_wordsearch_words`, entries whose normalized word collides with an
    earlier one (e.g. two entries genuinely spelled the same way, up to
    case) are **kept** (not silently dropped) -- the placement algorithm
    has no word-uniqueness assumption (each entry is placed independently),
    and silently discarding a duplicate previously also discarded its
    distinct clue with zero diagnostic. Each placement keeps its own
    originating clue (`CrosswordPlacement.clue`, set in
    `build_crossword_layout`) rather than looking it up by word text
    afterwards, so two entries that do end up with the same word never lose
    or swap their distinct clues downstream. Callers that want to flag
    likely-accidental duplicates do so separately via `CW004` in
    `crossword_validation.py`.
    """
    if not (content or "").strip():
        return []

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError:
        return []

    if not isinstance(parsed, dict):
        return []

    raw_entries = parsed.get("words") or parsed.get("woerter") or parsed.get("wörter")
    if not isinstance(raw_entries, list):
        return []

    entries: list[CrosswordEntry] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            continue
        raw_word = raw_entry.get("word") or raw_entry.get("wort") or raw_entry.get("lösung") or raw_entry.get("loesung")
        word = _normalize_crossword_token(raw_word)
        if not word:
            continue
        clue = str(raw_entry.get("clue") or raw_entry.get("hinweis") or "").strip()
        entries.append(CrosswordEntry(word=word, clue=clue))

    return entries


_DEFAULT_CROSSWORD_MAXW = 18
_DEFAULT_CROSSWORD_MAXH = 18
"""Fallback grid bounds used only when neither an explicit `maxw=`/`maxh=`
option nor a render-time printable-area estimate is available -- notably
during validation, which runs before the export page format is chosen (see
Slice 3 for the render-time, page-format-aware default). When the author
leaves both options unset, the validator's pre-check and the renderer's
actual computation may therefore resolve different bounds and land on
different `BlockComputationCache` keys, each computing its own layout once
-- an accepted, narrow gap in the "don't compute twice" optimization (the
cache is documented as a fail-safe performance aid, never a correctness
requirement), not a bug. Setting `maxw=`/`maxh=` explicitly makes both
passes agree and reuse the same cached layout."""


def _safe_int_option(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_crossword_bounds(options, cell_size_cm=0.72, printable_width_cm=None, printable_height_cm=None):
    """Resolves `(maxw, maxh)`: explicit options first, then a printable-area
    estimate (if the caller has one -- only the renderer does, see Slice 3),
    else the fixed fallback above."""
    maxw = _safe_int_option((options or {}).get("maxw"))
    if maxw is None:
        maxw = max(1, int(printable_width_cm // cell_size_cm)) if printable_width_cm else _DEFAULT_CROSSWORD_MAXW

    maxh = _safe_int_option((options or {}).get("maxh"))
    if maxh is None:
        maxh = max(1, int(printable_height_cm // cell_size_cm)) if printable_height_cm else _DEFAULT_CROSSWORD_MAXH

    return maxw, maxh


def parse_crossword_code_options(options):
    """Parses `code=`/`code_row=` identically for validation and rendering.

    Returns `(code_word_raw, code_word_normalized, code_row)` -- shared by
    `crossword_validation.py` and `answer_special_crossword.py` so both
    interpret the same option strings the same way (a divergence here
    would mean the validator's pre-check and the renderer's actual
    computation could disagree about whether a code is even present).
    """
    code_word_raw = str((options or {}).get("code") or "").strip()
    code_word = _normalize_crossword_token(code_word_raw) if code_word_raw else ""
    code_row = str((options or {}).get("code_row") or "").strip().lower() in {"1", "true", "yes", "on"}
    return code_word_raw, code_word, code_row


def _crossword_seed_payload(entries, maxw, maxh, code_row, code_word):
    """Builds the normalized, JSON-serializable payload shared by the RNG
    seed and the `BlockComputationCache` layout key (see Slice 1) -- kept
    as one function so seed and cache key can never silently diverge.

    `code_word` is only part of the payload when `code_row=True`: only then
    does the code word change the grid's *geometry* (the code row's length),
    so only then must two different code words invalidate each other's
    cached layout (see plan Slice 2, "Layout-Key").
    """
    payload = {
        "entries": [[entry.word, ] for entry in entries],
        "maxw": int(maxw),
        "maxh": int(maxh),
        "code_row": bool(code_row),
    }
    if code_row:
        payload["code_word"] = _normalize_crossword_token(code_word)
    return payload


def _fits_in_bounds(rows, cols, start_row, start_col, d_row, d_col, length):
    end_row = start_row + d_row * (length - 1)
    end_col = start_col + d_col * (length - 1)
    return 0 <= start_row and 0 <= start_col and end_row < rows and end_col < cols


def _is_valid_placement(grid, rows, cols, word, start_row, start_col, d_row, d_col):
    """Checks bounds, letter conflicts, and the "no touching without crossing" rule."""
    if not _fits_in_bounds(rows, cols, start_row, start_col, d_row, d_col, len(word)):
        return False

    before_row, before_col = start_row - d_row, start_col - d_col
    if 0 <= before_row < rows and 0 <= before_col < cols and grid[before_row][before_col] is not None:
        return False
    after_row = start_row + d_row * len(word)
    after_col = start_col + d_col * len(word)
    if 0 <= after_row < rows and 0 <= after_col < cols and grid[after_row][after_col] is not None:
        return False

    perpendicular = (1, 0) if (d_row, d_col) == (0, 1) else (0, 1)
    for index, letter in enumerate(word):
        row = start_row + d_row * index
        col = start_col + d_col * index
        existing = grid[row][col]
        if existing is not None:
            if existing != letter:
                return False
            continue
        # Empty cell about to receive a fresh letter: its perpendicular
        # neighbours must be empty too, or this word would silently run
        # parallel/adjacent to another one without an actual crossing.
        for n_row, n_col in (
            (row - perpendicular[0], col - perpendicular[1]),
            (row + perpendicular[0], col + perpendicular[1]),
        ):
            if 0 <= n_row < rows and 0 <= n_col < cols and grid[n_row][n_col] is not None:
                return False

    return True


def _candidate_intersection_count(grid, word, start_row, start_col, d_row, d_col):
    count = 0
    for index, letter in enumerate(word):
        row = start_row + d_row * index
        col = start_col + d_col * index
        if grid[row][col] == letter:
            count += 1
    return count


def _enumerate_candidates(word, anchor_placements):
    """Yields every (start_row, start_col, d_row, d_col) where `word` shares
    a letter with one of `anchor_placements`, running perpendicular to it."""
    seen = set()
    for anchor in anchor_placements:
        a_d_row, a_d_col = _DIRECTION_DELTAS[anchor.direction]
        for a_index, a_letter in enumerate(anchor.word):
            for w_index, w_letter in enumerate(word):
                if a_letter != w_letter:
                    continue
                if anchor.direction == "H":
                    d_row, d_col = 1, 0
                    start_row = anchor.row - w_index
                    start_col = anchor.col + a_index
                else:
                    d_row, d_col = 0, 1
                    start_row = anchor.row + a_index
                    start_col = anchor.col - w_index
                key = (start_row, start_col, d_row, d_col)
                if key in seen:
                    continue
                seen.add(key)
                yield key


def _first_word_anchor_candidates(word, maxh, maxw):
    """Spread-out candidate anchors for the very first (unanchored) word.

    Tries the word horizontally at every row (column centered) and
    vertically at every column (row centered) -- deliberately more than
    one fixed spot, since which anchor works out depends on how the *rest*
    of the entries end up crossing it, which isn't knowable in advance
    (see the comment at its call site in `build_crossword_layout`).
    """
    candidates = []
    length = len(word)
    if length <= maxw:
        centered_col = max(0, (maxw - length) // 2)
        for row in range(maxh):
            candidates.append((row, centered_col, 0, 1))
    if length <= maxh:
        centered_row = max(0, (maxh - length) // 2)
        for col in range(maxw):
            candidates.append((centered_row, col, 1, 0))
    return candidates


def build_crossword_layout(entries, maxw, maxh, code_row=False, code_word=None, rng=None):
    """Deterministically places all `entries` (and, if `code_row`, the code
    word) into a `maxw` x `maxh` grid via intersection-seeking backtracking.

    Returns `None` when no valid placement exists within bounds -- callers
    (`answer_special_crossword.py`'s renderer, and the `crossword` branch of
    `_validate_yaml_answer_payload`) turn that into a `CW001` diagnostic
    rather than silently rendering an empty block.

    `rng` should be seeded deterministically from the same inputs that form
    the `BlockComputationCache` key (`_crossword_seed_payload`) -- see the
    determinism invariant in `app/core/block_computation_cache.py` and plan
    Slice 2/Smell-Check 7: a cache hit must be indistinguishable from a
    fresh computation. Callers normally omit `rng` and let this function
    derive its own seeded instance.
    """
    if not entries:
        return None

    maxw = max(1, int(maxw))
    maxh = max(1, int(maxh))
    normalized_code_word = _normalize_crossword_token(code_word) if code_row else None

    if code_row:
        if not normalized_code_word or len(normalized_code_word) > maxw:
            return None
        if len(normalized_code_word) < len(entries):
            return None

    if rng is None:
        seed_payload = _crossword_seed_payload(entries, maxw, maxh, code_row, code_word)
        rng = random.Random(repr(sorted(seed_payload.items())))

    sorted_entries = sorted(entries, key=lambda entry: len(entry.word), reverse=True)
    if any(len(entry.word) > max(maxw, maxh) for entry in sorted_entries):
        return None

    grid = [[None for _ in range(maxw)] for _ in range(maxh)]
    placements: list[CrosswordPlacement] = []
    attempts_remaining = [_MAX_PLACEMENT_ATTEMPTS]

    code_row_placement = None
    if code_row:
        code_row_row = maxh // 2
        code_row_col = max(0, (maxw - len(normalized_code_word)) // 2)
        if not _fits_in_bounds(maxh, maxw, code_row_row, code_row_col, 0, 1, len(normalized_code_word)):
            return None
        for index, letter in enumerate(normalized_code_word):
            grid[code_row_row][code_row_col + index] = letter
        code_row_placement = CrosswordPlacement(
            word=normalized_code_word,
            row=code_row_row,
            col=code_row_col,
            direction="H",
            is_code_row=True,
        )
        placements.append(code_row_placement)

    def _place(word, start_row, start_col, d_row, d_col):
        for index, letter in enumerate(word):
            grid[start_row + d_row * index][start_col + d_col * index] = letter

    def _unplace(word, start_row, start_col, d_row, d_col, previously_filled):
        for index in range(len(word)):
            position = (start_row + d_row * index, start_col + d_col * index)
            if position not in previously_filled:
                grid[position[0]][position[1]] = None

    def _recurse(entry_index):
        if entry_index >= len(sorted_entries):
            return True

        entry = sorted_entries[entry_index]
        word = entry.word
        anchor_placements = [code_row_placement] if code_row else placements
        anchor_candidates = list(_enumerate_candidates(word, anchor_placements))

        scored = []
        for start_row, start_col, d_row, d_col in anchor_candidates:
            if not _is_valid_placement(grid, maxh, maxw, word, start_row, start_col, d_row, d_col):
                continue
            score = _candidate_intersection_count(grid, word, start_row, start_col, d_row, d_col)
            scored.append((score, start_row, start_col, d_row, d_col))

        rng.shuffle(scored)
        scored.sort(key=lambda item: item[0], reverse=True)

        for score, start_row, start_col, d_row, d_col in scored[:_MAX_CANDIDATES_PER_WORD]:
            if attempts_remaining[0] <= 0:
                return False
            attempts_remaining[0] -= 1

            previously_filled = {
                (start_row + d_row * i, start_col + d_col * i)
                for i in range(len(word))
                if grid[start_row + d_row * i][start_col + d_col * i] is not None
            }
            _place(word, start_row, start_col, d_row, d_col)
            placements.append(
                CrosswordPlacement(
                    word=word, row=start_row, col=start_col, direction="H" if d_row == 0 else "V", clue=entry.clue
                )
            )

            if _recurse(entry_index + 1):
                return True

            placements.pop()
            _unplace(word, start_row, start_col, d_row, d_col, previously_filled)

        return False

    if code_row:
        success = _recurse(0)
    else:
        # The first word has no existing placement to intersect with, so its
        # anchor can't be derived the way every other word's can. A single
        # fixed anchor (e.g. dead-centered) sometimes makes *every* later
        # word's crossing land on a forbidden adjacency purely because of
        # that one arbitrary choice -- so multiple spread-out anchors are
        # tried, sharing the same backtracking search (and attempts budget)
        # for the remaining words, stopping at the first full success.
        first_entry = sorted_entries[0]
        first_word = first_entry.word
        anchors = _first_word_anchor_candidates(first_word, maxh, maxw)
        rng.shuffle(anchors)
        success = False
        for start_row, start_col, d_row, d_col in anchors:
            if attempts_remaining[0] <= 0:
                break
            if not _is_valid_placement(grid, maxh, maxw, first_word, start_row, start_col, d_row, d_col):
                continue
            attempts_remaining[0] -= 1
            _place(first_word, start_row, start_col, d_row, d_col)
            placements.append(
                CrosswordPlacement(
                    word=first_word,
                    row=start_row,
                    col=start_col,
                    direction="H" if d_row == 0 else "V",
                    clue=first_entry.clue,
                )
            )
            if _recurse(1):
                success = True
                break
            placements.pop()
            _unplace(first_word, start_row, start_col, d_row, d_col, previously_filled=set())

    if not success:
        return None

    return CrosswordLayout(rows=maxh, cols=maxw, placements=tuple(placements))
