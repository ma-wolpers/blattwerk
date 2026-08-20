"""Regressionstest: Modul-Splits (300-Zeilen-Konvention) aendern keine oeffentlichen Importpfade.

Deckt insbesondere die Namen ab, die `tools/ci/check_ai_guardrails.py` und
diverse `app/core`-Module per `from app.core.blatt_validator import ...`
bzw. `from .blatt_kern_shared import ...` nutzen.
"""

from app.core.blatt_kern_shared import parse_blocks, split_front_matter
from app.core.blatt_validator import (
    BuildDiagnostic,
    InspectedDocument,
    inspect_markdown_text,
)
from app.core.blatt_validator_constants import (
    BLOCK_ALLOWED_OPTIONS,
    KNOWN_BLOCK_TYPES,
    REQUIRED_FRONTMATTER_FIELDS,
)
from app.core.kurzentwurf_runtime.dsl import parse_kurzentwerfer_text


def test_blatt_kern_shared_reexports_are_callable():
    assert callable(parse_blocks)
    assert callable(split_front_matter)


def test_blatt_validator_reexports_are_usable():
    assert callable(inspect_markdown_text)
    assert BuildDiagnostic is not None
    assert InspectedDocument is not None


def test_blatt_validator_constants_still_importable_from_original_module():
    assert "task" in KNOWN_BLOCK_TYPES
    assert "Titel" in REQUIRED_FRONTMATTER_FIELDS
    assert "points" in BLOCK_ALLOWED_OPTIONS["task"]


def test_kurzentwurf_dsl_public_entry_point_still_works():
    parsed = parse_kurzentwerfer_text(
        "---\ntitle: T\n---\n#einstieg t=5\nS> Impuls\nA>\ns< Erste Vermutung\nant< Fehlannahme\n"
    )
    assert parsed.title == "T"
    assert len(parsed.phases) == 1
    assert parsed.phases[0].phase == "einstieg"
