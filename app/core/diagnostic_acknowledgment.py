"""Connects diagnostics to acknowledgment state without a `core -> storage` import.

`app/core` never imports `app/storage` (verified: no existing import
does this anywhere in the codebase). Persistence is reached only
through the `AcknowledgedWarningsRepository` protocol below, injected
by the UI layer -- `app/storage/acknowledged_warnings_store.py`
satisfies it structurally (Python `Protocol`s need no explicit
inheritance).
"""

from __future__ import annotations

from typing import Protocol

from .blatt_validator_types import BuildDiagnostic


class AcknowledgedWarningsRepository(Protocol):
    """Port implemented by `app/storage/acknowledged_warnings_store.py`."""

    def get_acknowledged(self, document_path: str) -> set[str]: ...

    def set_acknowledged(self, document_path: str, identity: str, acknowledged: bool) -> set[str]: ...

    def clear_acknowledged(self, document_path: str) -> None: ...

    def reconcile_acknowledged_warnings(self, document_path: str, current_identities: set[str]) -> set[str]: ...


def filter_unacknowledged(
    diagnostics: list[BuildDiagnostic],
    identities: list[str],
    acknowledged: set[str],
) -> list[BuildDiagnostic]:
    """Pure filter -- no persistence, no side effect.

    Defensively never filters out an error, even if its identity were
    somehow present in `acknowledged` (cannot happen via the UI, which
    only lets warnings be acknowledged, but this function does not rely
    on that).
    """

    return [
        diagnostic
        for diagnostic, identity in zip(diagnostics, identities)
        if diagnostic.severity != "warning" or identity not in acknowledged
    ]
