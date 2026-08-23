"""Validation and diagnostics for Blattwerk markdown documents (öffentliche API).

Schlanker Einstiegspunkt: definiert die öffentlichen Funktionen
(`inspect_markdown_text`, `inspect_markdown_document`,
`has_blocking_diagnostics`, `summarize_blocking_diagnostics`) sowie die
Re-Exports `BuildDiagnostic`/`InspectedDocument`/`BLOCK_OPTION_SPECS`/
`KNOWN_ANSWER_TYPES`, die externer Code (u. a. `completion_catalogs.py`
als `validator.BLOCK_OPTION_SPECS`/`validator.KNOWN_ANSWER_TYPES`)
weiterhin unverändert aus `app.core.blatt_validator` importiert. Die
eigentliche Prüflogik ist auf Nachbarmodule verteilt: Konstanten
(`blatt_validator_constants.py`), Regex-Muster (`blatt_validator_patterns.py`),
Wert-Helper (`blatt_validator_value_helpers.py`), Marker-Syntax
(`blatt_validator_marker_syntax.py`), YAML-Entry-Validierung
(`blatt_validator_yaml_entries.py`) und die vier Kern-Validierungsschritte
(`blatt_validator_document.py`) — dieses Modul ruft sie nur noch in der
richtigen Reihenfolge auf.
"""

from __future__ import annotations

from pathlib import Path

from .blatt_kern_shared import parse_blocks, split_front_matter
from .blatt_validator_constants import (
    BLOCK_ALLOWED_OPTIONS,
    BLOCK_OPTION_KEY_ALIASES,
    BLOCK_OPTION_SPECS,
    CRITICAL_DIAGNOSTIC_CODES,
    KNOWN_ANSWER_TYPES,
    KNOWN_BLOCK_TYPES,
    OPTION_VALUE_STYLE_CATALOGS,
)
from .blatt_validator_block_options import _validate_block_options
from .blatt_validator_columns import _validate_columns_structure
from .blatt_validator_document import (
    _validate_block_type_specifics,
    _validate_frontmatter,
    _validate_yaml_answer_payload,
)
from .blatt_validator_marker_syntax import _collect_block_marker_syntax_diagnostics
from .blatt_validator_types import BuildDiagnostic, InspectedDocument
from .blatt_validator_value_helpers import (
    _collect_absolute_image_paths,
    _extract_validation_content_and_base_line,
)

__all__ = [
    "BuildDiagnostic",
    "InspectedDocument",
    "BLOCK_OPTION_SPECS",
    "BLOCK_OPTION_KEY_ALIASES",
    "OPTION_VALUE_STYLE_CATALOGS",
    "KNOWN_ANSWER_TYPES",
    "has_blocking_diagnostics",
    "summarize_blocking_diagnostics",
    "inspect_markdown_text",
    "inspect_markdown_document",
]


def _collect_document_diagnostics(meta, blocks, content_text, content_base_line=1):
    """Orchestriert die vollständige Dokumentprüfung: Marker-Syntax, Frontmatter, je Block Optionen/Typ/YAML,
    abschließend die dokumentweite `columns`/`nextcol`/`endcolumns`-Paarungsprüfung (`BL007`-`BL011`)."""
    diagnostics = _collect_block_marker_syntax_diagnostics(
        content_text, base_line=content_base_line
    )
    diagnostics.extend(_validate_frontmatter(meta))

    for index, (block_type, options, content) in enumerate(blocks):
        if block_type == "answer":
            diagnostics.append(
                BuildDiagnostic(
                    code="AN008",
                    message=(
                        "Legacy-Syntax `:::answer type=...` ist nicht mehr erlaubt. "
                        "Bitte dedizierten Blocktyp nutzen, z. B. `:::grid` oder `:::lines`."
                    ),
                    severity="error",
                    block_index=index,
                    block_type=block_type,
                )
            )
            continue

        absolute_image_paths = _collect_absolute_image_paths(content)
        if absolute_image_paths:
            preview = ", ".join(absolute_image_paths[:2])
            remainder = len(absolute_image_paths) - 2
            remainder_text = f" (+{remainder} weitere)" if remainder > 0 else ""
            diagnostics.append(
                BuildDiagnostic(
                    code="PT001",
                    message=(
                        "Absolute lokale Bildpfade gefunden. "
                        "Bitte relative Projektpfade verwenden: "
                        f"{preview}{remainder_text}"
                    ),
                    block_index=index,
                    block_type=block_type,
                )
            )

        if block_type not in KNOWN_BLOCK_TYPES:
            diagnostics.append(
                BuildDiagnostic(
                    code="BL001",
                    message=f"Unbekannter Blocktyp `{block_type}` wird ignoriert.",
                    block_index=index,
                    block_type=block_type,
                )
            )
            continue

        allowed_options = BLOCK_ALLOWED_OPTIONS.get(block_type, set())
        qrcode_url_value = _validate_block_options(
            diagnostics, index, block_type, options, allowed_options
        )

        is_answer_block = _validate_block_type_specifics(
            diagnostics, index, block_type, content, qrcode_url_value
        )
        if not is_answer_block:
            continue

        _validate_yaml_answer_payload(diagnostics, index, block_type, options, content)

    diagnostics.extend(_validate_columns_structure(blocks))
    return diagnostics


def has_blocking_diagnostics(diagnostics):
    """Return true when diagnostics contain critical errors."""
    for diagnostic in diagnostics or []:
        if diagnostic.severity == "error":
            return True
        if diagnostic.code in CRITICAL_DIAGNOSTIC_CODES:
            return True
    return False


def summarize_blocking_diagnostics(diagnostics):
    """Create compact error summary text for blocking diagnostics."""
    blocking = [
        diagnostic
        for diagnostic in (diagnostics or [])
        if diagnostic.severity == "error"
        or diagnostic.code in CRITICAL_DIAGNOSTIC_CODES
    ]
    if not blocking:
        return ""

    lines = []
    for diagnostic in blocking[:5]:
        location = (
            f" [Block {diagnostic.block_index}]"
            if diagnostic.block_index is not None
            else ""
        )
        lines.append(f"- {diagnostic.code}{location}: {diagnostic.message}")

    remaining = len(blocking) - len(lines)
    if remaining > 0:
        lines.append(f"- ... und {remaining} weitere kritische Fehler")

    return "\n".join(lines)


def inspect_markdown_text(markdown_text):
    """Parse markdown text and return parsed document plus diagnostics."""
    meta, _content_unused = split_front_matter(markdown_text)
    content, content_base_line = _extract_validation_content_and_base_line(markdown_text)
    blocks = parse_blocks(content)
    diagnostics = _collect_document_diagnostics(
        meta,
        blocks,
        content,
        content_base_line=content_base_line,
    )
    return InspectedDocument(meta=meta, blocks=blocks, diagnostics=diagnostics)


def inspect_markdown_document(md_path):
    """Read markdown file and return parsed document plus diagnostics."""
    md_file = Path(md_path)
    text = md_file.read_text(encoding="utf-8")
    return inspect_markdown_text(text)
