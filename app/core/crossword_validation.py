"""Compile-time validation for `:::crossword` blocks (`CW001`-`CW004`).

Split out of `blatt_validator_document.py` to keep that file under the
project's ~300-line convention (see `docs/intern/ARCHITEKTUR.md`) -- this is
already a self-contained concern (crossword-specific diagnostics), unlike
the generic per-block dispatch that file still owns.
"""

from __future__ import annotations

from collections import Counter

from .block_computation_cache import ComputationKey, get_or_compute
from .blatt_validator_types import BuildDiagnostic
from .crossword_code import validate_crossword_code
from .crossword_placement import (
    _CROSSWORD_ALGORITHM_VERSION,
    _crossword_seed_payload,
    build_crossword_layout,
    parse_crossword_code_options,
    parse_crossword_entries,
    resolve_crossword_bounds,
)


def validate_crossword_payload(diagnostics, index, block_type, options, content, cache):
    """Validates a `:::crossword` block's content/options, appending `CW001`-
    `CW004` diagnostics as needed.

    Also populates `cache` (a `BlockComputationCache`, see
    `app/core/block_computation_cache.py`) with the placement and code
    selection it computes here, so rendering (Slice 3,
    `answer_special_crossword.py`) can reuse the same result instead of
    recomputing it -- see the layout/code-selection key separation in
    `crossword_placement.py`/`crossword_code.py`.
    """
    entries = parse_crossword_entries(content)
    if not entries:
        return

    word_counts = Counter(entry.word for entry in entries)
    duplicate_words = sorted(word for word, count in word_counts.items() if count > 1)
    if duplicate_words:
        preview = ", ".join(duplicate_words[:5])
        remainder = len(duplicate_words) - 5
        remainder_text = f" (+{remainder} weitere)" if remainder > 0 else ""
        diagnostics.append(
            BuildDiagnostic(
                code="CW004",
                message=(
                    "Kreuzworträtsel enthält dasselbe Wort mehrfach (nach Normalisierung): "
                    f"{preview}{remainder_text}. Wird weiterhin platziert und beide Hinweise "
                    "bleiben erhalten -- prüfen, ob das beabsichtigt ist."
                ),
                block_index=index,
                block_type=block_type,
            )
        )

    maxw, maxh = resolve_crossword_bounds(options)
    code_word_raw, code_word, code_row = parse_crossword_code_options(options)

    if code_row and not code_word:
        diagnostics.append(
            BuildDiagnostic(
                code="CW003",
                message="`code_row=true` erfordert eine `code=`-Angabe.",
                severity="error",
                block_index=index,
                block_type=block_type,
            )
        )
        return

    if code_row and len(code_word) < len(entries):
        diagnostics.append(
            BuildDiagnostic(
                code="CW003",
                message=(
                    f"`code_row=true`: Das Codewort (`{code_word_raw}`) muss mindestens so lang "
                    f"sein wie die Anzahl der Rätselwörter ({len(entries)})."
                ),
                severity="error",
                block_index=index,
                block_type=block_type,
            )
        )
        return

    layout_key = ComputationKey(
        block_type="crossword",
        version=_CROSSWORD_ALGORITHM_VERSION,
        payload=_crossword_seed_payload(entries, maxw, maxh, code_row, code_word),
    )
    layout = get_or_compute(
        cache,
        layout_key,
        lambda: build_crossword_layout(entries, maxw, maxh, code_row=code_row, code_word=code_word or None),
    )

    if layout is None:
        diagnostics.append(
            BuildDiagnostic(
                code="CW001",
                message=(
                    "Kreuzworträtsel konnte mit den gegebenen Wörtern nicht innerhalb "
                    f"{maxw}×{maxh} Zellen platziert werden. Größeres Raster (`maxw=`/`maxh=`) "
                    "oder weniger/andere Wörter versuchen."
                ),
                severity="error",
                block_index=index,
                block_type=block_type,
            )
        )
        return

    if not code_word:
        return

    code_key = ComputationKey(
        block_type="crossword_code_selection",
        version=_CROSSWORD_ALGORITHM_VERSION,
        payload={**layout_key.payload, "code_word": code_word},
    )
    selection = get_or_compute(cache, code_key, lambda: validate_crossword_code(layout, code_word))

    if selection is None:
        diagnostics.append(
            BuildDiagnostic(
                code="CW002",
                message=(
                    f"Lösungscode „{code_word_raw}“ kann aus den Buchstaben der platzierten "
                    "Wörter nicht gebildet werden."
                ),
                severity="error",
                block_index=index,
                block_type=block_type,
            )
        )
