"""Document-type aware diagnostics inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .blatt_validator import BuildDiagnostic, inspect_markdown_text
from .blatt_kern_shared import split_front_matter
from .document_types import (
    DOCUMENT_TYPE_KURZENTWURF,
    detect_document_type,
    normalize_document_type_detection_mode,
)
from .kurzentwurf_runtime.validator import inspect_kurzentwerfer_text


@dataclass(frozen=True)
class DocumentDiagnosticsResult:
    """Normalized diagnostics with resolved document type."""

    document_type: str
    diagnostics: tuple[BuildDiagnostic, ...]


def inspect_document_text(
    markdown_text: str,
    *,
    detection_mode: str = "yaml_keys",
    source_path: str | Path | None = None,
) -> DocumentDiagnosticsResult:
    """Inspect text with the validator matching the resolved document type."""

    meta, _content = split_front_matter(markdown_text)
    normalized_detection_mode = normalize_document_type_detection_mode(detection_mode)
    document_type = detect_document_type(
        meta or {},
        detection_mode=normalized_detection_mode,
        source_path=source_path,
        markdown_text=markdown_text,
    )

    if document_type == DOCUMENT_TYPE_KURZENTWURF:
        inspection = inspect_kurzentwerfer_text(markdown_text)
        return DocumentDiagnosticsResult(
            document_type=document_type,
            diagnostics=tuple(_normalize_kurzentwurf_diagnostic(diag) for diag in inspection.diagnostics),
        )

    inspected = inspect_markdown_text(markdown_text)
    return DocumentDiagnosticsResult(
        document_type=document_type,
        diagnostics=tuple(inspected.diagnostics),
    )


def inspect_document_path(input_path: str | Path, *, detection_mode: str = "yaml_keys") -> DocumentDiagnosticsResult:
    """Read a document from disk and inspect it with the matching validator."""

    path_obj = Path(input_path)
    text = path_obj.read_text(encoding="utf-8")
    return inspect_document_text(text, detection_mode=detection_mode, source_path=path_obj)


def document_warning_title(document_type: str, context_label: str) -> str:
    """Return the UI warning title matching the document family."""

    if str(document_type or "").strip().lower() == DOCUMENT_TYPE_KURZENTWURF:
        return f"Kurzentwurf-Warnungen ({context_label})"
    return f"Blattwerk-Warnungen ({context_label})"


def _normalize_kurzentwurf_diagnostic(diagnostic) -> BuildDiagnostic:
    line_number = getattr(diagnostic, "line", None)
    return BuildDiagnostic(
        code=str(getattr(diagnostic, "code", "KZF000") or "KZF000"),
        message=str(getattr(diagnostic, "message", "Kurzentwurf-Fehler") or "Kurzentwurf-Fehler"),
        severity=str(getattr(diagnostic, "severity", "warning") or "warning"),
        line_number=int(line_number) if isinstance(line_number, int) else None,
    )