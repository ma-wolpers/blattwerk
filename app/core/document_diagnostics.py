"""Dokumenttypabhängige Diagnose: Konsistenzmarker plus passender Validator.

Der Typ kommt allein aus der Dateiendung bzw. dem expliziten Tab-Typ
(Invariante I1). Zuerst laufen die Marker-Diagnosen (`document_semantics`,
FM008/FM009/FM010) für jeden Typ, danach der typspezifische Validator:
Kurzentwurf-DSL, Arbeitsblatt-Pipeline (Arbeitsblatt/Präsentation/Klausur)
oder -- bei schlichtem Markdown -- keiner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .blatt_validator import BuildDiagnostic, inspect_markdown_text
from .blatt_kern_shared import split_front_matter
from .document_semantics import marker_diagnostics, type_for_path
from .document_type_registry import PIPELINE_KURZENTWURF, PIPELINE_MARKDOWN, spec_for_type
from .kurzentwurf_runtime.validator import inspect_kurzentwerfer_text


@dataclass(frozen=True)
class DocumentDiagnosticsResult:
    """Diagnosen samt dem Typ, für den sie ermittelt wurden."""

    document_type: str
    diagnostics: tuple[BuildDiagnostic, ...]


def inspect_document_text(markdown_text: str, *, document_type: str) -> DocumentDiagnosticsResult:
    """Prüft einen Dokumenttext mit Marker-Diagnose und dem Validator seines Typs.

    Args:
        markdown_text: Vollständiger Dokumenttext.
        document_type: Kanonischer Typ (aus `type_for_path`/`type_for_tab`).
    """
    spec = spec_for_type(document_type)
    try:
        meta, _content = split_front_matter(markdown_text)
    except Exception:
        meta = {}
    diagnostics = list(marker_diagnostics(meta, spec.id))

    if spec.pipeline == PIPELINE_KURZENTWURF:
        inspection = inspect_kurzentwerfer_text(markdown_text)
        diagnostics.extend(_normalize_kurzentwurf_diagnostic(diag) for diag in inspection.diagnostics)
    elif spec.pipeline != PIPELINE_MARKDOWN:
        diagnostics.extend(inspect_markdown_text(markdown_text, document_type=spec.id).diagnostics)

    return DocumentDiagnosticsResult(document_type=spec.id, diagnostics=tuple(diagnostics))


def inspect_document_path(input_path: str | Path, *, document_type: str | None = None) -> DocumentDiagnosticsResult:
    """Liest ein Dokument und prüft es; ohne expliziten Typ gilt die Dateiendung.

    Raises:
        ValueError: wenn weder ein Typ übergeben wurde noch die Endung bekannt ist
            (eine unbekannte Endung wird nie stillschweigend als Markdown behandelt).
    """
    path_obj = Path(input_path)
    resolved_type = document_type or type_for_path(path_obj)
    if resolved_type is None:
        raise ValueError(f"Unbekannte Dateiendung ohne expliziten Dokumenttyp: {path_obj.name}")
    text = path_obj.read_text(encoding="utf-8")
    return inspect_document_text(text, document_type=resolved_type)


def document_warning_title(document_type: str, context_label: str) -> str:
    """Titel des Warnungsdialogs passend zur Dokumentfamilie."""
    if document_type == "kurzentwurf":
        return f"Kurzentwurf-Warnungen ({context_label})"
    return f"Blattwerk-Warnungen ({context_label})"


def _normalize_kurzentwurf_diagnostic(diagnostic) -> BuildDiagnostic:
    line_number = getattr(diagnostic, "line", None)
    return BuildDiagnostic(
        code=str(getattr(diagnostic, "code", "KZF000") or "KZF000"),
        message=str(getattr(diagnostic, "message", "Kurzentwurf-Fehler") or "Kurzentwurf-Fehler"),
        severity=str(getattr(diagnostic, "severity", "warning") or "warning"),
        line_number=int(line_number) if isinstance(line_number, int) else None,
        region_id=getattr(diagnostic, "region_id", None),
        anchor=getattr(diagnostic, "anchor", None),
    )
