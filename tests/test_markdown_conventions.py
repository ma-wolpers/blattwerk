"""Tests für den Doku-Collector (`app/core/markdown_conventions.py`)."""

from app.core.answer_grid_entries import GEOMETRY_ENTRY_ALLOWED_KEYS
from app.core.blatt_validator_constants import KNOWN_GRID_LINE_STYLES
from app.core.markdown_conventions import collect_markdown_conventions


def test_required_frontmatter_fields_contain_titel():
    catalog = collect_markdown_conventions()
    assert "Titel" in catalog.required_frontmatter_fields
    assert "Fach" in catalog.required_frontmatter_fields
    assert "Thema" in catalog.required_frontmatter_fields


def test_task_block_has_points_option():
    catalog = collect_markdown_conventions()
    task_block = next(block for block in catalog.blocks if block.name == "task")
    assert "points" in task_block.allowed_options


def test_raw_pseudo_block_type_is_excluded():
    catalog = collect_markdown_conventions()
    assert all(block.name != "raw" for block in catalog.blocks)


def test_kurzentwurf_phases_contain_einstieg():
    catalog = collect_markdown_conventions()
    assert "Einstieg" in catalog.kurzentwurf.phases


def test_kurzentwurf_legacy_detection_keys_contain_material():
    catalog = collect_markdown_conventions()
    assert "Material" in catalog.kurzentwurf.legacy_detection_only_keys


def test_kurzentwurf_identity_keys_are_disjoint_from_legacy_detection_keys():
    catalog = collect_markdown_conventions()
    identity = catalog.kurzentwurf.identity_meta_keys
    legacy = catalog.kurzentwurf.legacy_detection_only_keys
    assert not (identity & legacy)


def test_geometry_entries_match_source_of_truth_exactly():
    """Der Katalog darf GEOMETRY_ENTRY_ALLOWED_KEYS nur re-verpacken, nicht kopieren/abweichen."""
    catalog = collect_markdown_conventions()
    catalog_sections = {entry.section: entry.allowed_keys for entry in catalog.geometry.entries}
    source_sections = {
        section: frozenset(keys) for section, keys in GEOMETRY_ENTRY_ALLOWED_KEYS.items()
    }
    assert catalog_sections == source_sections


def test_geometry_line_styles_match_validator_constant():
    catalog = collect_markdown_conventions()
    assert catalog.geometry.line_styles == frozenset(KNOWN_GRID_LINE_STYLES)


def test_optional_frontmatter_fields_include_new_boolean_fields_with_distinct_vocabularies():
    catalog = collect_markdown_conventions()
    fields_by_name = {field.name: field for field in catalog.optional_frontmatter_fields}

    show_student_header = fields_by_name["show_student_header"]
    presentation_mini_header = fields_by_name["presentation_show_mini_header"]

    assert show_student_header.kind == "boolean"
    assert presentation_mini_header.kind == "boolean"
    # Zwei echte, unterschiedliche Boolean-Vokabulare -- nicht identisch.
    assert show_student_header.allowed_values != presentation_mini_header.allowed_values
