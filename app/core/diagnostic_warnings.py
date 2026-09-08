"""Build user-facing warning payloads from Blattwerk diagnostics."""

from __future__ import annotations

from pathlib import Path

from .diagnostic_acknowledgment import AcknowledgedWarningsRepository, filter_unacknowledged
from .diagnostic_identity import compute_diagnostic_identity
from .document_diagnostics import document_warning_title, inspect_document_path


def build_warning_payload(
    input_path: Path,
    context_label: str,
    *,
    acknowledged_repo: AcknowledgedWarningsRepository,
    max_items: int = 8,
):
    """Create warning title/message/signature for non-blocking diagnostics.

    Returns None when there are no diagnostics or the document cannot be
    inspected. Already-acknowledged warnings are filtered out here, via
    `acknowledged_repo` (see `app.core.diagnostic_acknowledgment` for the
    port this must satisfy) -- `app/core` never imports the concrete
    `app/storage` implementation, the caller (UI layer) injects it.
    """

    try:
        inspected = inspect_document_path(input_path)
    except Exception:
        return None

    diagnostics = [
        diagnostic
        for diagnostic in inspected.diagnostics
        if str(getattr(diagnostic, "severity", "warning")).lower() != "error"
    ]

    try:
        document_path = str(input_path)
        identities = [compute_diagnostic_identity(d) for d in diagnostics]
        ackable_identities = {
            identity for d, identity in zip(diagnostics, identities) if d.severity == "warning"
        }
        acknowledged = acknowledged_repo.reconcile_acknowledged_warnings(document_path, ackable_identities)
        diagnostics = filter_unacknowledged(diagnostics, identities, acknowledged)
    except Exception:
        # Ack-Filterung ist rein additiv -- ein Fehler dabei (z. B. eine
        # Diagnosequelle ohne region_id) darf die Warnungen selbst nicht
        # verschlucken, nur das Abhaken bleibt fuer diesen Aufruf wirkungslos.
        pass

    signature = (
        str(Path(input_path).resolve()),
        inspected.document_type,
        tuple((d.code, d.block_index, d.line_number, d.message) for d in diagnostics),
        context_label,
    )

    if not diagnostics:
        return {
            "signature": signature,
            "title": document_warning_title(inspected.document_type, context_label),
            "message": "",
            "count": 0,
        }

    lines = []
    for diagnostic in diagnostics[: max(1, max_items)]:
        if diagnostic.line_number is not None:
            location = f" [Zeile {diagnostic.line_number}]"
        elif diagnostic.block_index is not None:
            location = f" [Block {diagnostic.block_index}]"
        else:
            location = ""
        lines.append(f"- {diagnostic.code}{location}: {diagnostic.message}")

    remaining = len(diagnostics) - len(lines)
    if remaining > 0:
        lines.append(f"- ... und {remaining} weitere Warnungen")

    return {
        "signature": signature,
        "title": document_warning_title(inspected.document_type, context_label),
        "message": "\n".join(lines),
        "count": len(diagnostics),
    }
