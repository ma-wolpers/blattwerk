"""Data-integrity tests for `data/operatoren/*.json`.

Runtime matching (`operator_legend.py`) uses exact `formen` lookups and
trusts that this data is internally consistent -- these checks are the
substitute for a runtime ambiguity diagnostic (see DEVELOPMENT_LOG.md:
`OPR002` was deliberately dropped as a runtime code once these checks
exist, since a duplicate-free file can never produce an ambiguous match).
"""

import json

import pytest

from app.core.blatt_validator_constants import OPTIONAL_FRONTMATTER_FIELDS
from app.core.operator_legend import OPERATOR_DATA_DIR

_STUFE_ALLOWED_VALUES = next(
    spec.allowed_values for spec in OPTIONAL_FRONTMATTER_FIELDS if spec.name == "Stufe"
)

_DATA_FILES = sorted(OPERATOR_DATA_DIR.glob("*.json")) if OPERATOR_DATA_DIR.is_dir() else []


@pytest.fixture(params=_DATA_FILES, ids=[f.name for f in _DATA_FILES])
def data_file(request):
    return request.param


def test_at_least_one_operator_data_file_exists():
    assert _DATA_FILES, "expected at least the data/operatoren/mathematik.json placeholder"


def test_operator_data_file_is_valid_json(data_file):
    json.loads(data_file.read_text(encoding="utf-8"))


def test_operator_data_file_has_no_duplicate_forms_across_keys(data_file):
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    form_to_key = {}
    for entry in raw.get("operatoren", []):
        key = entry["key"]
        for form in entry.get("formen", []):
            normalized = form.strip().lower()
            existing_key = form_to_key.get(normalized)
            assert existing_key is None or existing_key == key, (
                f"form {normalized!r} claimed by both {existing_key!r} and {key!r} in {data_file.name}"
            )
            form_to_key[normalized] = key


def test_operator_data_file_stufen_references_resolve(data_file):
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    stufengruppen = raw.get("stufengruppen") or {}
    for entry in raw.get("operatoren", []):
        for stufe_reference in entry.get("stufen", []):
            if stufengruppen:
                assert stufe_reference in stufengruppen, (
                    f"{data_file.name}: operator {entry['key']!r} references unknown "
                    f"Stufengruppe {stufe_reference!r}"
                )
            else:
                assert stufe_reference.lower() in _STUFE_ALLOWED_VALUES, (
                    f"{data_file.name}: operator {entry['key']!r} references unknown "
                    f"Stufe value {stufe_reference!r} (no stufengruppen defined in this file)"
                )


def test_operator_data_file_stufengruppen_values_are_known_stufe_values(data_file):
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    for group_name, values in (raw.get("stufengruppen") or {}).items():
        for value in values:
            assert value.lower() in _STUFE_ALLOWED_VALUES, (
                f"{data_file.name}: Stufengruppe {group_name!r} references unknown Stufe value {value!r}"
            )


def test_operator_data_file_every_operator_has_key_definition_and_forms(data_file):
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    for entry in raw.get("operatoren", []):
        assert entry.get("key")
        assert entry.get("definition")
        assert entry.get("formen"), f"{data_file.name}: operator {entry.get('key')!r} has no formen"


def test_operator_data_file_every_operator_has_a_vorschlag(data_file):
    # vorschlag is what editor autocomplete offers -- distinct from formen
    # (matching), see DEVELOPMENT_LOG.md. Missing it just means "no
    # suggestion", not a crash, but it should be an explicit oversight to
    # catch, not a silent gap.
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    for entry in raw.get("operatoren", []):
        assert entry.get("vorschlag"), f"{data_file.name}: operator {entry.get('key')!r} has no vorschlag"


def test_operator_data_file_has_no_duplicate_vorschlag_across_keys(data_file):
    raw = json.loads(data_file.read_text(encoding="utf-8"))
    vorschlag_to_key = {}
    for entry in raw.get("operatoren", []):
        key = entry["key"]
        for label in entry.get("vorschlag", []):
            existing_key = vorschlag_to_key.get(label)
            assert existing_key is None or existing_key == key, (
                f"vorschlag {label!r} claimed by both {existing_key!r} and {key!r} in {data_file.name}"
            )
            vorschlag_to_key[label] = key
