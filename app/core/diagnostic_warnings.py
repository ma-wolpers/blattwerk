"""Build user-facing warning payloads from Blattwerk diagnostics."""

from __future__ import annotations

from pathlib import Path

from .blatt_validator import inspect_markdown_document


def build_warning_payload(input_path: Path, context_label: str, max_items: int = 8):
    """Create warning title/message/signature for non-blocking diagnostics.

    Returns None when there are no diagnostics or the document cannot be inspected.
    """

    try:
        inspected = inspect_markdown_document(str(input_path))
    except Exception:
        return None

    diagnostics = inspected.diagnostics
    signature = (
        str(Path(input_path).resolve()),
        tuple((d.code, d.block_index, d.message) for d in diagnostics),
        context_label,
    )

    if not diagnostics:
        return {
            "signature": signature,
            "title": f"Blattwerk-Warnungen ({context_label})",
            "message": "",
            "count": 0,
        }

    lines = []
    for diagnostic in diagnostics[: max(1, max_items)]:
        location = (
            f" [Block {diagnostic.block_index}]"
            if diagnostic.block_index is not None
            else ""
        )
        lines.append(f"- {diagnostic.code}{location}: {diagnostic.message}")

    remaining = len(diagnostics) - len(lines)
    if remaining > 0:
        lines.append(f"- ... und {remaining} weitere Warnungen")

    return {
        "signature": signature,
        "title": f"Blattwerk-Warnungen ({context_label})",
        "message": "\n".join(lines),
        "count": len(diagnostics),
    }
