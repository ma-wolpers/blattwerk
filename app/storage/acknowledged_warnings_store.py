"""I/O layer for "acknowledged" (abgehakte) warnings, keyed by document path.

Implements `app.core.diagnostic_acknowledgment.AcknowledgedWarningsRepository`
structurally (no inheritance needed for a `Protocol`). Depends on
`local_config_store` (generic config read/write) and
`acknowledged_warnings_schema` (pure normalization) -- never the other
way round, so there is no import cycle back to `local_config_store`.
"""

from __future__ import annotations

from . import acknowledged_warnings_schema as schema
from .history_paths_adapter import normalize_recent_path
from .local_config_store import ACKNOWLEDGED_WARNINGS_KEY, load_local_config, save_local_config


def _normalize_path(document_path: str) -> str:
    """Canonical key for a document -- same normalizer `recent_files` already uses.

    Deliberately not `app/ui/blatt_ui_base.py::_normalize_document_path`
    (native OS separators, e.g. `\\` on Windows): that would be a
    `storage -> ui` dependency, and would silently mismatch the
    `.as_posix()` form `recent_files` entries are stored in, making the
    prune-against-`recent_files` step below permanently a no-op.
    """

    return normalize_recent_path(document_path)


def get_acknowledged(document_path: str) -> set[str]:
    """Reads the acknowledged identities for one document. No side effect."""

    config = load_local_config()
    acknowledged_warnings = config.get(ACKNOWLEDGED_WARNINGS_KEY)
    if not isinstance(acknowledged_warnings, dict):
        return set()
    return set(acknowledged_warnings.get(_normalize_path(document_path), []))


def set_acknowledged(document_path: str, identity: str, acknowledged: bool) -> set[str]:
    """Explicit setter (not a blind toggle) -- checkbox click, context menu, and
    "show all again" all call this same function with an explicit boolean."""

    normalized_path = _normalize_path(document_path)
    config = load_local_config()
    acknowledged_warnings = config.get(ACKNOWLEDGED_WARNINGS_KEY)
    if not isinstance(acknowledged_warnings, dict):
        acknowledged_warnings = {}

    current = list(acknowledged_warnings.get(normalized_path, []))
    updated = schema.add_identity(current, identity) if acknowledged else schema.remove_identity(current, identity)

    acknowledged_warnings = dict(acknowledged_warnings)
    if updated:
        acknowledged_warnings[normalized_path] = updated
    else:
        acknowledged_warnings.pop(normalized_path, None)

    config[ACKNOWLEDGED_WARNINGS_KEY] = acknowledged_warnings
    save_local_config(config)
    return set(updated)


def clear_acknowledged(document_path: str) -> None:
    """Removes all acknowledgments for one document. Never affects other documents."""

    normalized_path = _normalize_path(document_path)
    config = load_local_config()
    acknowledged_warnings = config.get(ACKNOWLEDGED_WARNINGS_KEY)
    if not isinstance(acknowledged_warnings, dict) or normalized_path not in acknowledged_warnings:
        return

    acknowledged_warnings = dict(acknowledged_warnings)
    acknowledged_warnings.pop(normalized_path, None)
    config[ACKNOWLEDGED_WARNINGS_KEY] = acknowledged_warnings
    save_local_config(config)


def reconcile_acknowledged_warnings(document_path: str, current_identities: set[str]) -> set[str]:
    """Prunes identities no longer present in `current_identities`, persists only on change.

    The sole place with this persistence side effect -- a diagnostic
    that stops being reported (fixed, or briefly changed severity) is
    dropped here, so it counts as "new" if the same occurrence appears
    again later. Repeated calls with an unchanged `current_identities`
    (e.g. compiling twice without edits) never trigger a second write.
    """

    normalized_path = _normalize_path(document_path)
    config = load_local_config()
    acknowledged_warnings = config.get(ACKNOWLEDGED_WARNINGS_KEY)
    if not isinstance(acknowledged_warnings, dict):
        acknowledged_warnings = {}

    existing = list(acknowledged_warnings.get(normalized_path, []))
    reconciled = schema.intersect_with_current(existing, current_identities)

    if reconciled == existing:
        return set(existing)

    acknowledged_warnings = dict(acknowledged_warnings)
    if reconciled:
        acknowledged_warnings[normalized_path] = reconciled
    else:
        acknowledged_warnings.pop(normalized_path, None)

    config[ACKNOWLEDGED_WARNINGS_KEY] = acknowledged_warnings
    save_local_config(config)
    return set(reconciled)
