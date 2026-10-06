"""Region identity for Kurzentwurf phase diagnostics.

Own, small helper local to the Kurzentwurf source -- deliberately not
shared with `blatt_validator_region.py` (Arbeitsblatt `:::`-blocks):
each diagnosis family owns its own notion of region, the generic
acknowledgment infrastructure never guesses one.
"""

from __future__ import annotations

import hashlib

KURZENTWURF_DOCUMENT_REGION_ID = "kurzentwurf:document"
"""Region for diagnostics that concern the whole document, not one phase
(e.g. the formula/internet notice `KZF160`)."""


def compute_phase_region_id(phase, duration_minutes, start_time) -> str:
    """Region for a diagnostic anchored to one phase block's own header.

    Two phases with identical (phase, duration, start_time) intentionally
    collide -- same accepted trade-off as `compute_block_region_id`.
    """

    payload = f"{phase}|{duration_minutes}|{start_time}"
    digest = hashlib.sha1(payload.encode("utf-8"))
    return f"kurzentwurf:phase:{digest.hexdigest()[:16]}"
