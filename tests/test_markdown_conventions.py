"""Tests für den Doku-Collector (`app/core/markdown_conventions.py`)."""

from app.core.answer_grid_entries import GEOMETRY_ENTRY_ALLOWED_KEYS
from app.core.blatt_validator import inspect_markdown_text
from app.core.blatt_validator_constants import (
    BLOCK_OPTION_SPECS,
    KNOWN_BLOCK_TYPES,
    KNOWN_GRID_LINE_STYLES,
)
from app.core.markdown_conventions import collect_markdown_conventions


def _option_names(block_spec):
    return {option.name for option in block_spec.options}


def test_required_frontmatter_fields_contain_titel():
    catalog = collect_markdown_conventions()
    assert "Titel" in catalog.required_frontmatter_fields
    assert "Fach" in catalog.required_frontmatter_fields
    assert "Thema" in catalog.required_frontmatter_fields


def test_task_block_has_points_option():
    catalog = collect_markdown_conventions()
    task_block = next(block for block in catalog.blocks if block.name == "task")
    assert "points" in _option_names(task_block)


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


# -- BLOCK_OPTION_SPECS: echte Cross-Consistency-Guards (kein tautologischer --
# -- Ableitungstest, siehe Review) -------------------------------------------


def test_every_known_block_type_except_raw_has_a_catalog_entry():
    expected = KNOWN_BLOCK_TYPES - {"raw"}
    assert set(BLOCK_OPTION_SPECS.keys()) == expected


def test_no_duplicate_option_names_within_a_block():
    for block_name, specs in BLOCK_OPTION_SPECS.items():
        names = [spec.name for spec in specs]
        assert len(names) == len(set(names)), f"Doppelte Option in Block {block_name!r}: {names}"


def test_every_enum_option_has_nonempty_allowed_values():
    for block_name, specs in BLOCK_OPTION_SPECS.items():
        for spec in specs:
            if spec.kind == "enum":
                assert spec.allowed_values, f"{block_name}.{spec.name}: kind=enum ohne allowed_values"


# -- Cross-Consistency: Katalogaussage vs. tatsächliches Validator-Verhalten --


def _document_with_block(block_markdown):
    return "---\nTitel: T\nFach: M\nThema: X\n---\n" + block_markdown + "\n"


def test_generic_enum_options_validated_true_actually_reject_invalid_values():
    """work/action/hint/line/mode: Katalog sagt validated=True -> ein ungültiger Wert muss OP002 auslösen."""
    cases = [
        (":::task work=nonsense\nx\n:::", "work"),
        (":::task action=nonsense\nx\n:::", "action"),
        (":::task hint=nonsense\nx\n:::", "hint"),
        (":::grid line=nonsense\n:::", "line"),
        (":::task mode=nonsense\nx\n:::", "mode"),
    ]
    for block_markdown, option_name in cases:
        codes = {d.code for d in inspect_markdown_text(_document_with_block(block_markdown)).diagnostics}
        assert "OP002" in codes, f"Erwartete OP002 für ungültigen {option_name!r}-Wert, bekam {codes}"


def test_align_is_validated_for_task_but_not_for_table_per_catalog():
    """Katalog: task.align validated=True, table.alignment validated=False -- Validatorverhalten muss übereinstimmen."""
    task_codes = {
        d.code
        for d in inspect_markdown_text(
            _document_with_block(":::task align=nonsense\nx\n:::")
        ).diagnostics
    }
    assert "OP002" in task_codes

    table_codes = {
        d.code
        for d in inspect_markdown_text(
            _document_with_block(":::table rows=1 cols=1 alignment=nonsense\ncells: [[\"x\"]]\n:::")
        ).diagnostics
    }
    assert "OP002" not in table_codes


def test_show_deprecation_still_emits_op003_not_op002():
    codes = {
        d.code
        for d in inspect_markdown_text(
            _document_with_block(":::task show=worksheet\nx\n:::")
        ).diagnostics
    }
    assert "OP003" in codes
    assert "OP002" not in codes


def test_qrcode_url_and_size_options_are_validated_per_catalog():
    qrcode_spec = BLOCK_OPTION_SPECS["qrcode"]
    url_spec = next(spec for spec in qrcode_spec if spec.name == "url")
    size_spec = next(spec for spec in qrcode_spec if spec.name == "w")
    assert url_spec.validated is True
    assert size_spec.validated is True

    codes = {
        d.code
        for d in inspect_markdown_text(
            _document_with_block(":::qrcode url=\"not a url\" w=notacssvalue\n:::")
        ).diagnostics
    }
    assert "QR002" in codes
    assert "OP002" in codes
