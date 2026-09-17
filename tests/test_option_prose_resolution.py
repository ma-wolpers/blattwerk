"""Tests for `app.core.option_prose_resolution` -- the shared resolver deciding
which `PROSE_SECTIONS` key explains a block option (moved from
`tools/docs/authoring_guide_coverage.py`, now the single source both the
doc generator and the editor completion overlay use).
"""

from dataclasses import replace

from app.core.blatt_validator_constants import BlockOptionSpec, MISSING
from app.core.markdown_conventions import collect_markdown_conventions
from app.core.option_prose_resolution import (
    OptionProseResolution,
    build_majority_variant_map,
    resolve_option_prose_key,
)


def test_resolve_returns_named_result_object_not_a_tuple():
    catalog = collect_markdown_conventions()
    variants = build_majority_variant_map(catalog)
    task_work_spec = next(spec for block in catalog.blocks if block.name == "task" for spec in block.options if spec.name == "work")

    result = resolve_option_prose_key("task", task_work_spec, majority_variants=variants)

    assert isinstance(result, OptionProseResolution)
    assert hasattr(result, "key")
    assert hasattr(result, "allow_block_supplement")


def test_shared_majority_concept_resolves_to_generic_option_key():
    # `work` is used with the identical (kind/allowed_values/validated)
    # shape by many blocks (task, subtask, ...) -- a clear majority.
    catalog = collect_markdown_conventions()
    variants = build_majority_variant_map(catalog)
    task_work_spec = next(spec for block in catalog.blocks if block.name == "task" for spec in block.options if spec.name == "work")

    result = resolve_option_prose_key("task", task_work_spec, majority_variants=variants)

    assert result.key == "option:work"
    assert result.allow_block_supplement is True


def test_diverging_block_specific_variant_resolves_to_block_specific_key():
    # `alignment` on `table` and `qrcode` are documented as genuinely
    # different concepts with their own narrower value sets -- no shared
    # majority, each gets its own `block:<name>.alignment` key.
    catalog = collect_markdown_conventions()
    variants = build_majority_variant_map(catalog)
    table_alignment_spec = next(
        spec for block in catalog.blocks if block.name == "table" for spec in block.options if spec.name == "alignment"
    )

    result = resolve_option_prose_key("table", table_alignment_spec, majority_variants=variants)

    assert result.key == "block:table.alignment"
    assert result.allow_block_supplement is False


def test_unknown_option_name_with_no_majority_entry_falls_back_to_specific_key():
    synthetic_spec = BlockOptionSpec(
        name="__never_seen_option__", kind="text", allowed_values=None, validated=False, default=MISSING
    )

    result = resolve_option_prose_key("task", synthetic_spec, majority_variants={})

    assert result.key == "block:task.__never_seen_option__"
    assert result.allow_block_supplement is False


def test_build_majority_variant_map_requires_at_least_two_blocks_sharing_a_variant():
    catalog = collect_markdown_conventions()
    variants = build_majority_variant_map(catalog)
    # `alignment` itself has no cross-block majority (table/qrcode diverge) --
    # it must be entirely absent from the majority map, not merely mapped
    # to one of the two variants arbitrarily.
    assert "alignment" not in variants


def test_default_majority_variants_used_when_none_explicitly_passed():
    # Calling without `majority_variants` must not raise and must resolve
    # consistently with the explicit, real-catalog map.
    catalog = collect_markdown_conventions()
    variants = build_majority_variant_map(catalog)
    task_work_spec = next(spec for block in catalog.blocks if block.name == "task" for spec in block.options if spec.name == "work")

    with_default = resolve_option_prose_key("task", task_work_spec)
    with_explicit = resolve_option_prose_key("task", task_work_spec, majority_variants=variants)

    assert with_default == with_explicit


def test_resolution_reacts_to_a_modified_synthetic_catalog_not_a_stale_cache():
    # Regression for the caching design: a caller working with a
    # DIFFERENT (synthetic/modified) catalog must get majority variants
    # computed from THAT catalog, never a stale cached real-catalog map --
    # mirrors `test_render_worksheet_presentation_guide_changes_when_catalog_changes`.
    catalog = collect_markdown_conventions()
    marker_option = BlockOptionSpec(
        name="__test_marker_option__", kind="text", allowed_values=None, validated=False, default=MISSING
    )
    # Duplicate the synthetic option onto two different blocks with an
    # identical shape -- a fresh, catalog-specific majority that only
    # exists in this modified catalog, never in the real one.
    modified_blocks = tuple(
        replace(block, options=block.options + (marker_option,))
        if block.name in {"task", "subtask"}
        else block
        for block in catalog.blocks
    )
    modified_catalog = replace(catalog, blocks=modified_blocks)

    variants = build_majority_variant_map(modified_catalog)
    result = resolve_option_prose_key("task", marker_option, majority_variants=variants)

    assert result.key == "option:__test_marker_option__"
    assert result.allow_block_supplement is True
    # The real catalog's own majority map must remain unaffected.
    assert "__test_marker_option__" not in build_majority_variant_map(catalog)
