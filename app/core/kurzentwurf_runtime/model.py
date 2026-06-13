from __future__ import annotations

from dataclasses import dataclass

ALLOWED_PHASES: tuple[str, ...] = (
    "Einstieg",
    "Erarbeitung",
    "Ergebnissicherung",
    "Vertiefung",
    "Hausaufgabe",
    "Didaktische Reserve",
)

FORBIDDEN_BLATTWERK_MARKERS: tuple[str, ...] = (
    ":::",
    "§{",
    "%{",
    "&{",
)

LEGACY_ROW_MARKERS: tuple[str, ...] = (
    "[row",
    "[/row]",
    "[schritte]",
    "[/schritte]",
    "[aktivitaeten]",
    "[/aktivitaeten]",
    "[umgebung]",
    "[/umgebung]",
)


@dataclass(frozen=True)
class Diagnostic:
    """Static diagnostic output from parser/validator/export stages."""

    code: str
    severity: str
    message: str
    line: int | None = None


@dataclass(frozen=True)
class RawSegment:
    """Raw segment inside one phase block before semantic validation."""

    schritte: str | None
    aktivitaeten: str | None
    umgebung: str | None
    antizipiert: str | None
    line: int


@dataclass(frozen=True)
class RawPhaseBlock:
    """Raw phase block produced by the V2 parser."""

    phase: str
    duration_minutes: int | None
    start_time: str
    segments: tuple[RawSegment, ...]
    line: int


@dataclass(frozen=True)
class RawRow:
    """Legacy row representation kept temporarily for transition safety."""

    phase: str
    time: str
    schritte: str
    aktivitaeten: str
    umgebung: str
    line: int


@dataclass(frozen=True)
class KurzentwurfRow:
    """Legacy validated row model kept temporarily for transition safety."""

    phase: str
    display_phase: str
    time: str
    schritte: str
    aktivitaeten: str
    umgebung: str
    line: int


@dataclass(frozen=True)
class KurzentwurfSegment:
    """Validated segment with explicit inheritance flags for rowspan rendering."""

    schritte: str
    aktivitaeten: str
    umgebung: str
    antizipiert: str
    inherit_schritte: bool
    inherit_aktivitaeten: bool
    inherit_umgebung: bool
    line: int


@dataclass(frozen=True)
class KurzentwurfPhaseBlock:
    """Validated phase block model used for V2 rendering/export."""

    phase: str
    display_phase: str
    start_minutes: int | None
    end_minutes: int | None
    segments: tuple[KurzentwurfSegment, ...]
    line: int


@dataclass(frozen=True)
class KurzentwurfDocument:
    """Validated document model."""

    title: str
    subtitle: str
    rows: tuple[KurzentwurfRow, ...] = ()
    phases: tuple[KurzentwurfPhaseBlock, ...] = ()


@dataclass(frozen=True)
class InspectionResult:
    """Combined semantic validation and diagnostics result."""

    document: KurzentwurfDocument | None
    diagnostics: tuple[Diagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(diag.severity.lower() == "error" for diag in self.diagnostics)
