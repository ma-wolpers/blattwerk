"""Completion catalog queries sourced from core validation constants."""

from __future__ import annotations

from . import blatt_validator as validator


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
