"""Generic, source-agnostic identity for acknowledgeable diagnostics.

Deliberately knows nothing about block types, document families, or
code prefixes -- it only ever sees the `code`/`region_id`/`anchor`
triple that the diagnosing source already put on a `BuildDiagnostic`.
See `docs/intern/ARCHITEKTUR.md` for the full occurrence/identity
contract this module implements.
"""

from __future__ import annotations

import hashlib
import json

from .blatt_validator_types import BuildDiagnostic

IDENTITY_VERSION = "v1"


def canonicalize_identity_payload(diagnostic: BuildDiagnostic) -> str:
    """Deterministic, sorted JSON serialization of the identity-relevant fields.

    `message` is intentionally excluded -- a pure wording change to a
    diagnostic's text must not invalidate existing acknowledgments.
    """

    payload = {
        "version": IDENTITY_VERSION,
        "code": diagnostic.code,
        "region": diagnostic.region_id or "",
        "anchor": diagnostic.anchor or "",
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_diagnostic_identity(diagnostic: BuildDiagnostic) -> str:
    """Returns the stable acknowledgment identity for one diagnostic.

    Raises for an ackable diagnostic (`severity == "warning"`) missing
    `region_id` -- a forgotten `region_id` at a construction site would
    otherwise silently collide with every other unset-region warning
    instead of failing loudly.
    """

    if diagnostic.severity == "warning" and diagnostic.region_id is None:
        raise ValueError(
            f"Ackbare Diagnose {diagnostic.code!r} ohne region_id -- "
            "Diagnosequelle muss eine Occurrence definieren, bevor sie ackbar gemacht wird."
        )

    digest = hashlib.sha1(canonicalize_identity_payload(diagnostic).encode("utf-8"))
    return digest.hexdigest()[:16]
