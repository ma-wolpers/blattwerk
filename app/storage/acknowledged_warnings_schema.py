"""Pure schema helpers for the `acknowledged_warnings` config section.

No dependency on `local_config_store` (that module depends on this
one, not the other way round -- see `acknowledged_warnings_store.py`
for the import graph this keeps free of cycles). No I/O here.
"""

from __future__ import annotations


def _clean_identities(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return cleaned


def normalize_acknowledged_warnings(raw: object, recent_files: list[str]) -> dict[str, list[str]]:
    """Keeps only documents still present in `recent_files`, cleans each list.

    This is the sole pruning mechanism for documents that fall out of
    "recently opened" -- lazy, runs on every config load/save anyway.
    """

    if not isinstance(raw, dict):
        return {}

    recent_set = set(recent_files or [])
    normalized: dict[str, list[str]] = {}
    for document_path, identities in raw.items():
        if document_path not in recent_set:
            continue
        cleaned = _clean_identities(identities)
        if cleaned:
            normalized[document_path] = cleaned
    return normalized


def add_identity(identities: list[str], identity: str) -> list[str]:
    if identity in identities:
        return list(identities)
    return [*identities, identity]


def remove_identity(identities: list[str], identity: str) -> list[str]:
    return [existing for existing in identities if existing != identity]


def intersect_with_current(identities: list[str], current_identities: set[str]) -> list[str]:
    """Keeps only identities still present in `current_identities` (reconciliation math, no I/O)."""

    return [identity for identity in identities if identity in current_identities]
