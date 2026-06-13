"""Build user-facing warning payloads from Blattwerk diagnostics."""

from __future__ import annotations

from pathlib import Path

from .document_diagnostics import document_warning_title, inspect_document_path


def build_warning_payload(input_path: Path, context_label: str, max_items: int = 8):
    """Create warning title/message/signature for non-blocking diagnostics.

    Returns None when there are no diagnostics or the document cannot be inspected.
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
