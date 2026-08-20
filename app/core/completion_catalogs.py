"""Completion catalog queries sourced from core validation constants."""

from __future__ import annotations

from . import blatt_validator as validator

_SELF_CLOSING_BLOCK_TYPES = frozenset(
    {"nextcol", "endcolumns", "pagebreak", "framebreak", "slidechromeoff", "sectionmark", "vspacer"}
)
"""Blocktypen ohne eigenen Body, die immer als Einzeiler mit schließendem
`:::` auf derselben Zeile geschrieben werden (siehe die self-closing
Regel `_SELF_CLOSING_BLOCK_PATTERN` in `blatt_kern_shared_parsing.py`).
Anders als z. B. `:::info ... :::`, das typischerweise Body-Inhalt
zwischen öffnendem und schließendem Marker hat, tragen diese sieben
Blocktypen nie Body-Inhalt -- ein öffnender Marker ohne sofortiges
`:::` auf derselben Zeile lässt den Parser fälschlich auf einen
mehrzeiligen Body warten (siehe `parse_blocks`)."""


def get_completion_block_types() -> tuple[str, ...]:
    """Returns known block types for completion in stable sorted order."""

    return tuple(sorted(block for block in validator.KNOWN_BLOCK_TYPES if block != "raw"))


def get_completion_answer_types() -> tuple[str, ...]:
    """Returns known answer types for completion."""

    return tuple(sorted(validator.KNOWN_ANSWER_TYPES))


def get_completion_options_for_block(block_type: str) -> tuple[str, ...]:
    """Returns allowed option keys for a block type."""

    block_type_key = str(block_type or "").strip().lower()
    return tuple(sorted(validator.BLOCK_ALLOWED_OPTIONS.get(block_type_key, set())))


def get_completion_option_values(block_type: str, option_key: str) -> tuple[str, ...]:
    """Returns the value catalog for a (block_type, option_key) combination.

    Reads `allowed_values` directly from the per-block `BLOCK_OPTION_SPECS`
    catalog (single source of truth shared with the validator's `OP002`
    checks), so suggestions can never list a value that the validator would
    itself reject for that specific block type -- e.g. `:::info type=`
    only ever suggests `default`/`warning`/`note`, never unrelated block
    types like `grid`/`lines`. Returns an empty tuple when the option has
    no fixed value catalog (free-form kinds like `text`/`integer`/`css_length`)
    or when `(block_type, option_key)` is unknown -- no exception either way.
    """

    block_type_key = str(block_type or "").strip().lower()
    option_key_key = str(option_key or "").strip().lower()

    for spec in validator.BLOCK_OPTION_SPECS.get(block_type_key, ()):
        if spec.name == option_key_key:
            return tuple(sorted(spec.allowed_values)) if spec.allowed_values else ()

    return ()


def get_self_closing_block_types() -> frozenset[str]:
    """Returns block types that are always self-closing markers without a body."""

    return _SELF_CLOSING_BLOCK_TYPES
