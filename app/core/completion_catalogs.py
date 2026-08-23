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
    """Returns allowed option keys for a block type.

    Excludes key aliases (`BLOCK_OPTION_KEY_ALIASES`, e.g. `columns.ratio`,
    an alias of `widths`) from the suggestions -- they remain fully valid,
    validated syntax, just not offered as a completion candidate. Filtering
    is block-scoped, not a global string exclusion: `qrcode.width` is an
    alias of `w`, but `table`'s own `width` is primary and stays offered.
    """

    block_type_key = str(block_type or "").strip().lower()
    allowed = validator.BLOCK_ALLOWED_OPTIONS.get(block_type_key, set())
    aliases = validator.BLOCK_OPTION_KEY_ALIASES.get(block_type_key, frozenset())
    return tuple(sorted(key for key in allowed if key not in aliases))


def _resolve_style_filtered_values(
    allowed_values: frozenset[str], style: str
) -> tuple[str, ...] | None:
    """Returns one value per concept in the given language style, if catalogued.

    Looks up `allowed_values` by exact set equality against
    `OPTION_VALUE_STYLE_CATALOGS` (not by option name) -- an unrelated or
    altered value set (e.g. `table.alignment`'s own, narrower set) simply
    yields `None`, no heuristic partial matching.
    """

    for known_set, style_table in validator.OPTION_VALUE_STYLE_CATALOGS:
        if allowed_values != known_set:
            continue
        return tuple(concept[style] for concept in style_table if style in concept)

    return None


def _resolve_style_abbreviation_hints(
    allowed_values: frozenset[str], style: str
) -> dict[str, str]:
    """Returns {value: abbreviation} for the given language style, if catalogued.

    Abbreviations are curated, language-specific catalog data (see
    `OPTION_VALUE_STYLE_CATALOGS`), never derived from the value itself.
    """

    abbreviation_field = f"abbreviation_{style}"
    for known_set, style_table in validator.OPTION_VALUE_STYLE_CATALOGS:
        if allowed_values != known_set:
            continue
        return {
            concept[style]: concept[abbreviation_field]
            for concept in style_table
            if style in concept and abbreviation_field in concept
        }

    return {}


def get_completion_option_values(
    block_type: str, option_key: str, value_style: str | None = None
) -> tuple[str, ...]:
    """Returns the value catalog for a (block_type, option_key) combination.

    Reads `allowed_values` directly from the per-block `BLOCK_OPTION_SPECS`
    catalog (single source of truth shared with the validator's `OP002`
    checks), so suggestions can never list a value that the validator would
    itself reject for that specific block type -- e.g. `:::info type=`
    only ever suggests `default`/`warning`/`note`, never unrelated block
    types like `grid`/`lines`. Returns an empty tuple when the option has
    no fixed value catalog (free-form kinds like `text`/`integer`/`css_length`)
    or when `(block_type, option_key)` is unknown -- no exception either way.

    `value_style` (`"german"`/`"english"`/`None`) narrows a catalogued
    value set (`work`/`action`/`align`/`hint`) down to one value per
    concept in that language. `None` (default) preserves prior behaviour:
    the full, unfiltered value set.
    """

    block_type_key = str(block_type or "").strip().lower()
    option_key_key = str(option_key or "").strip().lower()

    for spec in validator.BLOCK_OPTION_SPECS.get(block_type_key, ()):
        if spec.name != option_key_key:
            continue
        if not spec.allowed_values:
            return ()
        if value_style:
            styled = _resolve_style_filtered_values(spec.allowed_values, value_style)
            if styled is not None:
                return tuple(sorted(styled))
        return tuple(sorted(spec.allowed_values))

    return ()


def get_completion_option_value_abbreviation_hints(
    block_type: str, option_key: str, value_style: str
) -> dict[str, str]:
    """Returns {value: abbreviation} hints for a (block_type, option_key, style).

    Empty dict when the option has no curated abbreviation catalog for that
    style, or when `(block_type, option_key)` is unknown.
    """

    block_type_key = str(block_type or "").strip().lower()
    option_key_key = str(option_key or "").strip().lower()

    for spec in validator.BLOCK_OPTION_SPECS.get(block_type_key, ()):
        if spec.name == option_key_key and spec.allowed_values:
            return _resolve_style_abbreviation_hints(spec.allowed_values, value_style)

    return {}


def get_self_closing_block_types() -> frozenset[str]:
    """Returns block types that are always self-closing markers without a body."""

    return _SELF_CLOSING_BLOCK_TYPES
