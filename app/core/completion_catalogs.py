"""Completion catalog queries for the editor -- one import path for the UI layer.

Mostly sourced from core validation constants (`blatt_validator`), plus a
thin pass-through to `operator_legend.py`'s operator-suggestion data
(`get_completion_operator_forms`) so the UI never needs to import that
module directly.
"""

from __future__ import annotations

from typing import Protocol, TypedDict

from . import authoring_guide_prose
from . import operator_legend
from . import blatt_validator as validator
from .blatt_validator_constants import MISSING, BlockOptionSpec, FrontmatterFieldSpec
from .option_prose_resolution import resolve_option_prose_key

_SELF_CLOSING_BLOCK_TYPES = frozenset(
    {"nextcol", "endcolumns", "pagebreak", "framebreak", "slidechromeoff", "sectionmark", "vspacer"}
)


class CompletionDetail(TypedDict):
    """Optional explanation for the autocomplete popup's detail overlay
    column (`blatt_ui_editor_completion_popup.py`), shown for whichever
    suggestion is currently highlighted.

    `value_hint`, when present, already carries its display prefix
    (`"Standard: …"`/`"Möglicher Wert: …"`) -- that distinction is decided
    once, here in the catalog layer, where the underlying normative data
    (`FrontmatterFieldSpec.default` vs. `.allowed_values`) is still in
    scope; the popup itself never re-derives it from a raw value.
    """

    title: str
    description: str
    value_hint: str | None
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


def get_completion_frontmatter_field_values(field_name: str) -> tuple[str, ...]:
    """Returns the value catalog for an optional enum-kind frontmatter field.

    Mirrors `get_completion_option_values`'s shape for `BlockOptionSpec`,
    just one level up (`FrontmatterFieldSpec.allowed_values`,
    `OPTIONAL_FRONTMATTER_FIELDS`) -- both read `allowed_values` directly
    from the single normative catalog, so this can never suggest a value
    the validator itself would reject. Returns an empty tuple for
    non-`enum` fields (`free_text`/`boolean`/`scalar_nonempty`) or an
    unknown field name -- no exception either way. Field-name matching is
    case-sensitive (unlike block option keys): frontmatter field names like
    `Stufe` are themselves case-sensitive in `OPTIONAL_FRONTMATTER_FIELDS`.
    """

    for spec in validator.OPTIONAL_FRONTMATTER_FIELDS:
        if spec.name != field_name:
            continue
        if spec.kind != "enum" or not spec.allowed_values:
            return ()
        return tuple(sorted(spec.allowed_values))

    return ()


def get_completion_operator_forms(fach, stufe) -> tuple[str, ...]:
    """Returns the official `!!...!!`-operator suggestion labels for `fach`/`stufe`.

    Thin pass-through to `operator_legend.list_operator_suggestions` -- the
    only place that knows what an operator or a Stufe-group means (see
    that module's docstring). Kept here so the UI layer imports operator
    data through the same catalog module as everything else, never
    `operator_legend` directly. Empty tuple for an unknown `fach` or when
    `fach`/`stufe` filtering leaves nothing available -- no exception.
    """

    return operator_legend.list_operator_suggestions(fach, stufe)


def get_completion_operator_details(fach, stufe) -> dict[str, CompletionDetail]:
    """Returns `{label: CompletionDetail}` for exactly the operator labels
    `get_completion_operator_forms` would offer for the same `fach`/`stufe`.

    Thin pass-through to `operator_legend.list_operator_suggestion_details`,
    same reasoning as `get_completion_operator_forms` above: the UI layer
    never imports `operator_legend` directly. No `value_hint` -- an
    operator label isn't a `key: value` pair.
    """

    return {
        label: CompletionDetail(title=label, description=definition, value_hint=None)
        for label, definition in operator_legend.list_operator_suggestion_details(fach, stufe).items()
    }


class _HasValueHintFields(Protocol):
    """Structural contract `_format_value_hint()` needs -- satisfied by both
    `FrontmatterFieldSpec` and `BlockOptionSpec` without unifying those two
    validator dataclasses themselves (they stay the validator's own,
    separately-owned normative types; this Protocol only names the subset
    of fields shared between them that value-hint formatting cares about)."""

    kind: str
    default: object
    allowed_values: frozenset[str] | None


def _format_value_hint(spec: _HasValueHintFields) -> str | None:
    """Builds the display-ready value hint for one option/frontmatter-field spec.

    A real `default` is shown as `"Standard: …"` -- boolean defaults as
    `ja`/`nein` (the vocabulary the field itself accepts as input, not
    Python's `True`/`False`), enum defaults verbatim. Without a `default`
    but with `allowed_values`, the alphabetically first value is shown as
    `"Möglicher Wert: …"` -- deliberately NOT labelled "Beispiel": picking
    `allowed_values`'s first entry is an arbitrary-but-valid choice, not a
    redactionally curated example. `None` for fields with neither
    (`free_text`/`scalar_nonempty`, or an `enum` with empty
    `allowed_values`) -- no invented hint.

    Works identically for `FrontmatterFieldSpec` and `BlockOptionSpec` --
    both carry the same relevant fields (`kind`/`default`/`allowed_values`),
    just in different dataclasses/field orders, so this stays one shared
    formatter rather than two near-duplicates.
    """

    if spec.default is not MISSING:
        if spec.kind == "boolean":
            return f"Standard: {'ja' if spec.default else 'nein'}"
        return f"Standard: {spec.default}"

    if spec.allowed_values:
        return f"Möglicher Wert: {sorted(spec.allowed_values)[0]}"

    return None


def _format_selected_value_hint(spec: _HasValueHintFields, value: str) -> str | None:
    """Builds the value hint for ONE already-offered candidate value (`option_value`/
    `frontmatter_value` completion kinds), as opposed to `_format_value_hint()`'s
    key-row hint (`get_completion_block_option_detail`/`get_completion_frontmatter_field_detail`).

    The candidate `value` IS already the suggestion line -- unlike the key
    row, there is nothing left to guess an example for. Only marks it
    `"Standard: …"` when it genuinely equals the spec's own default;
    otherwise `None`, never a re-derived "Möglicher Wert" (that label only
    makes sense when picking a representative value out of many for a
    *key*'s overview row, not when the value itself is the row).
    """

    if spec.default is MISSING:
        return None

    if spec.kind == "boolean":
        default_text = "ja" if spec.default else "nein"
    else:
        default_text = str(spec.default)

    return f"Standard: {value}" if str(value) == default_text else None


def _find_frontmatter_field_spec(field_name: str) -> FrontmatterFieldSpec | None:
    for spec in validator.OPTIONAL_FRONTMATTER_FIELDS:
        if spec.name == field_name:
            return spec
    return None


def _find_block_option_spec(block_type: str, option_key: str) -> BlockOptionSpec | None:
    for spec in validator.BLOCK_OPTION_SPECS.get(str(block_type or "").strip().lower(), ()):
        if spec.name == option_key:
            return spec
    return None


def get_completion_frontmatter_field_detail(field_name: str) -> CompletionDetail | None:
    """Returns the autocomplete detail overlay content for a frontmatter key.

    Description comes from `PROSE_SECTIONS["frontmatter:<field_name>"]`
    (`authoring_guide_prose.py`) -- the same redactional text the generated
    author's guide already shows for this field, never a second, separately
    maintained copy. `None` only if no such prose section exists (shouldn't
    happen for any field `_EDITOR_FRONTMATTER_KEYS` offers, given
    `assert_prose_coverage()`, but this stays defensive rather than
    assuming that invariant here too -- an unrecognised field silently gets
    no detail panel instead of a `KeyError`).
    """

    description = authoring_guide_prose.PROSE_SECTIONS.get(f"frontmatter:{field_name}")
    if description is None:
        return None

    spec = _find_frontmatter_field_spec(field_name)
    value_hint = _format_value_hint(spec) if spec is not None else None

    return CompletionDetail(title=field_name, description=description, value_hint=value_hint)


def get_completion_frontmatter_value_detail(field_name: str, value: str) -> CompletionDetail | None:
    """Returns the autocomplete detail overlay content for ONE offered frontmatter VALUE
    (e.g. `Stufe: 11`) -- reuses the field's own description
    (`get_completion_frontmatter_field_detail`'s source), since there is no
    separate per-value prose anywhere in the codebase and none should be
    invented (see `option_prose_resolution.py`'s module docstring: prose
    exists per field/option, never per individual value). `value_hint`
    marks only whether `value` happens to be the field's actual default,
    never a re-derived "Möglicher Wert" (the value itself already IS the
    suggestion row).
    """

    description = authoring_guide_prose.PROSE_SECTIONS.get(f"frontmatter:{field_name}")
    if description is None:
        return None

    spec = _find_frontmatter_field_spec(field_name)
    value_hint = _format_selected_value_hint(spec, value) if spec is not None else None

    return CompletionDetail(title=field_name, description=description, value_hint=value_hint)


def get_completion_block_type_detail(block_type: str) -> CompletionDetail | None:
    """Returns the autocomplete detail overlay content for a block type.

    Description comes from `PROSE_SECTIONS["block:<block_type>"]` -- same
    source and completeness guarantee as
    `get_completion_frontmatter_field_detail`. No `value_hint`: a block
    type isn't a `key: value` pair, there is nothing to hint at.
    """

    description = authoring_guide_prose.PROSE_SECTIONS.get(f"block:{block_type}")
    if description is None:
        return None
    return CompletionDetail(title=block_type, description=description, value_hint=None)


def _resolve_block_option_description(block_type: str, option_key: str, spec: BlockOptionSpec) -> str | None:
    """Resolves + combines a block option's prose exactly like
    `tools/docs/authoring_guide_render_worksheet.py::_option_explanation`
    does for the generated guide (generic `option:<name>` text, plus an
    optional `block:<block>.<name>` supplement) -- shared by
    `get_completion_block_option_detail`/`get_completion_option_value_detail`
    so the two don't each re-implement the same combination."""

    resolution = resolve_option_prose_key(block_type, spec)
    description = authoring_guide_prose.PROSE_SECTIONS.get(resolution.key)
    if description is None:
        return None

    if resolution.allow_block_supplement:
        supplement = authoring_guide_prose.PROSE_SECTIONS.get(f"block:{block_type}.{option_key}")
        if supplement:
            description = f"{description} *Besonderheit bei `{block_type}`:* {supplement}"

    return description


def get_completion_block_option_detail(block_type: str, option_key: str) -> CompletionDetail | None:
    """Returns the autocomplete detail overlay content for a block option key
    (e.g. `rows=` inside `:::lines`, `work=` inside `:::task`).

    Resolves the same `option:<name>` (generic, shared concept) vs.
    `block:<block>.<name>` (block-specific) prose key the generated
    author's guide already uses (`option_prose_resolution.resolve_option_prose_key`,
    moved from `tools/docs/authoring_guide_coverage.py` -- single source,
    not a completion-specific copy).
    """

    spec = _find_block_option_spec(block_type, option_key)
    if spec is None:
        return None

    description = _resolve_block_option_description(block_type, option_key, spec)
    if description is None:
        return None

    return CompletionDetail(title=option_key, description=description, value_hint=_format_value_hint(spec))


def get_completion_option_value_detail(block_type: str, option_key: str, value: str) -> CompletionDetail | None:
    """Returns the autocomplete detail overlay content for ONE offered option VALUE
    (e.g. `work=einzel`) -- reuses the option's own description
    (`get_completion_block_option_detail`'s source), no separate per-value
    prose (same reasoning as `get_completion_frontmatter_value_detail`).
    `value_hint` marks only whether `value` happens to be the option's
    actual default.
    """

    spec = _find_block_option_spec(block_type, option_key)
    if spec is None:
        return None

    description = _resolve_block_option_description(block_type, option_key, spec)
    if description is None:
        return None

    return CompletionDetail(
        title=option_key, description=description, value_hint=_format_selected_value_hint(spec, value)
    )


def get_self_closing_block_types() -> frozenset[str]:
    """Returns block types that are always self-closing markers without a body."""

    return _SELF_CLOSING_BLOCK_TYPES
