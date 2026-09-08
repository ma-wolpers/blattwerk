"""Region identity for Arbeitsblatt/`:::`-block diagnostics.

Belongs to the worksheet-validator family, not to the generic
acknowledgment infrastructure (`diagnostic_identity.py`) -- a different
diagnosis family, or the Kurzentwurf source, is free to define its own
notion of "region" without touching this module.
"""

from __future__ import annotations

import hashlib


def compute_block_region_id(block_type: str, options: dict) -> str:
    """Region for a diagnostic anchored to a `:::`-block's own header.

    Uses `block_type` + all current options, deliberately excluding the
    block's body text -- editing unrelated prose inside the block must
    not change its region. Two blocks of the same type with identical
    options (true duplicates) intentionally collide here; see
    `docs/intern/ARCHITEKTUR.md` for the accepted trade-off.
    """

    canonical_options = ",".join(f"{key}={options[key]}" for key in sorted(options))
    payload = f"{block_type}|{canonical_options}"
    digest = hashlib.sha1(payload.encode("utf-8"))
    return f"worksheet:block:{digest.hexdigest()[:16]}"
