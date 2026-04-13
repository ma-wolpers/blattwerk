"""Completion catalog queries sourced from core validation constants."""

from __future__ import annotations

from . import blatt_validator as validator


def _collect_option_value_catalogs() -> dict[str, tuple[str, ...]]:
    """Builds value catalogs from core `KNOWN_*` constants automatically."""

    by_option_key: dict[str, set[str]] = {}
    discovered_types: set[str] = set()

    for constant_name, payload in vars(validator).items():
        if not isinstance(payload, set) or not payload:
            continue
        if not all(isinstance(value, str) for value in payload):
            continue

        if constant_name.startswith("KNOWN_") and constant_name.endswith("_VALUES"):
            option_key = constant_name[len("KNOWN_") : -len("_VALUES")].strip().lower()
            if option_key:
                by_option_key.setdefault(option_key, set()).update({value.strip() for value in payload if value.strip()})
            continue

        if constant_name.startswith("KNOWN_") and constant_name.endswith("_TYPES"):
            discovered_types.update({value.strip() for value in payload if value.strip()})

    # `type=` is used across multiple block families and should include all discovered type values.
    if discovered_types:
        by_option_key.setdefault("type", set()).update(discovered_types)
    if "hint" in by_option_key:
        by_option_key.setdefault("type", set()).update(by_option_key["hint"])
    if "action" in by_option_key:
        by_option_key.setdefault("type", set()).update(by_option_key["action"])

    return {
        option_key: tuple(sorted(values))
        for option_key, values in by_option_key.items()
        if values
    }


_OPTION_VALUE_CATALOGS = _collect_option_value_catalogs()


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
    """Returns known value catalog for a (block_type, option_key) combination."""

    _ = str(block_type or "").strip().lower()
    option_key_key = str(option_key or "").strip().lower()
    return _OPTION_VALUE_CATALOGS.get(option_key_key, ())
