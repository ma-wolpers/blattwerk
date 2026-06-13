from __future__ import annotations

from collections import Counter, defaultdict
import re

from .dsl import parse_kurzentwerfer_text
from .model import (
    ALLOWED_PHASES,
    FORBIDDEN_BLATTWERK_MARKERS,
    LEGACY_ROW_MARKERS,
    Diagnostic,
    InspectionResult,
    KurzentwurfDocument,
    KurzentwurfPhaseBlock,
    KurzentwurfSegment,
)

_PHASE_LOOKUP = {
    "einstieg": "Einstieg",
    "erarbeitung": "Erarbeitung",
    "ergebnissicherung": "Ergebnis- sicherung",
    "vertiefung": "Vertiefung",
    "hausaufgabe": "Hausaufgabe",
    "didaktische reserve": "Didaktische Reserve",
}

_TIME_RE = re.compile(r"^(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)$")
_COLON_MARKER_RE = re.compile(r"^\s*(S|A|U|ant)\s*:\s*", re.IGNORECASE)


def inspect_kurzentwerfer_text(source: str) -> InspectionResult:
    """Inspect source text and return validated document model plus diagnostics."""

    parsed = parse_kurzentwerfer_text(source)
    diagnostics: list[Diagnostic] = list(parsed.diagnostics)

    for marker in FORBIDDEN_BLATTWERK_MARKERS:
        if marker in source:
            diagnostics.append(
                Diagnostic(
                    code="KZF010",
                    severity="error",
                    message=(
                        f"Blattwerk-Marker '{marker}' ist in Kurzentwerfer ungueltig. "
                        "Bitte die Kurzentwerfer-DSL verwenden."
                    ),
                )
            )

    source_lines = source.splitlines()
    for marker in LEGACY_ROW_MARKERS:
        marker_prefix = marker.lower()
        for line_number, line in enumerate(source_lines, start=1):
            if marker_prefix in line.lower():
                diagnostics.append(
                    Diagnostic(
                        code="KZF100",
                        severity="error",
                        message=(
                            "Legacy-[row]-Syntax ist in DSL V2 nicht erlaubt. "
                            "Bitte #phase, --- und Marker S>/A>/U> sowie s</ant< nutzen."
                        ),
                        line=line_number,
                    )
                )

    for line_number, line in enumerate(source_lines, start=1):
        if _COLON_MARKER_RE.match(line):
            diagnostics.append(
                Diagnostic(
                    code="KZF101",
                    severity="error",
                    message="Marker mit Doppelpunkt sind ungueltig. Bitte S>/A>/U> und s</ant< verwenden.",
                    line=line_number,
                )
            )

    normalized_blocks: list[dict[str, object]] = []
    for raw_phase in parsed.phases:
        normalized_phase = _normalize_phase(raw_phase.phase)
        if normalized_phase is None:
            diagnostics.append(
                Diagnostic(
                    code="KZF011",
                    severity="error",
                    message=(
                        "Ungueltige Phase '"
                        f"{raw_phase.phase}'. Erlaubt sind: {', '.join(ALLOWED_PHASES)}."
                    ),
                    line=raw_phase.line,
                )
            )
            continue

        if not raw_phase.segments:
            diagnostics.append(
                Diagnostic(
                    code="KZF102",
                    severity="error",
                    message="#phase muss mindestens ein Segment enthalten.",
                    line=raw_phase.line,
                )
            )
            continue

        current_schritte: str | None = None
        current_aktivitaeten: str | None = None
        current_umgebung: str | None = None
        validated_segments: list[KurzentwurfSegment] = []

        for raw_segment in raw_phase.segments:
            explicit_schritte = _normalize_optional(raw_segment.schritte)
            explicit_aktivitaeten = _normalize_optional(raw_segment.aktivitaeten)
            explicit_umgebung = _normalize_optional(raw_segment.umgebung)
            antizipiert = _normalize_optional(raw_segment.antizipiert) or ""

            if explicit_schritte is None and current_schritte is None:
                diagnostics.append(
                    Diagnostic(
                        code="KZF112",
                        severity="error",
                        message="Erstes Segment einer Phase braucht Inhalt bei S> (oder Pipe-Spalte 1).",
                        line=raw_segment.line,
                    )
                )
            if explicit_aktivitaeten is None and current_aktivitaeten is None:
                diagnostics.append(
                    Diagnostic(
                        code="KZF113",
                        severity="error",
                        message="Erstes Segment einer Phase braucht Lernaktivitaeten mit s<.",
                        line=raw_segment.line,
                    )
                )
            if explicit_umgebung is None and current_umgebung is None:
                diagnostics.append(
                    Diagnostic(
                        code="KZF114",
                        severity="error",
                        message="Erstes Segment einer Phase braucht Inhalt bei U> (oder Pipe-Spalte 3).",
                        line=raw_segment.line,
                    )
                )

            inherit_schritte = explicit_schritte is None
            inherit_umgebung = explicit_umgebung is None
            inherit_aktivitaeten = explicit_aktivitaeten is None and not antizipiert

            if explicit_schritte is not None:
                current_schritte = explicit_schritte
            if explicit_aktivitaeten is not None:
                current_aktivitaeten = explicit_aktivitaeten
            if explicit_umgebung is not None:
                current_umgebung = explicit_umgebung

            validated_segments.append(
                KurzentwurfSegment(
                    schritte=current_schritte or "",
                    aktivitaeten=current_aktivitaeten or "",
                    umgebung=current_umgebung or "",
                    antizipiert=antizipiert,
                    inherit_schritte=inherit_schritte,
                    inherit_aktivitaeten=inherit_aktivitaeten,
                    inherit_umgebung=inherit_umgebung,
                    line=raw_segment.line,
                )
            )

        normalized_blocks.append(
            {
                "phase": normalized_phase,
                "duration_minutes": raw_phase.duration_minutes,
                "start_time": (raw_phase.start_time or "").strip(),
                "line": raw_phase.line,
                "segments": tuple(validated_segments),
            }
        )

    starts, ends = _resolve_phase_times(
        normalized_blocks,
        global_start_time=(parsed.global_start_time or "").strip(),
        diagnostics=diagnostics,
    )

    if any(item.severity == "error" for item in diagnostics):
        return InspectionResult(document=None, diagnostics=tuple(diagnostics))

    phase_totals = Counter(str(block["phase"]) for block in normalized_blocks)
    phase_running = defaultdict(int)
    validated_blocks: list[KurzentwurfPhaseBlock] = []

    for index, block in enumerate(normalized_blocks):
        phase = str(block["phase"])
        phase_running[phase] += 1
        display_phase = phase
        if phase_totals[phase] > 1:
            display_phase = f"{phase} {_to_roman(phase_running[phase])}"

        validated_blocks.append(
            KurzentwurfPhaseBlock(
                phase=phase,
                display_phase=display_phase,
                start_minutes=starts[index],
                end_minutes=ends[index],
                segments=tuple(block["segments"]),
                line=int(block["line"]),
            )
        )

    document = KurzentwurfDocument(
        title=parsed.title.strip() or "Kurzentwurf",
        subtitle=parsed.subtitle.strip(),
        phases=tuple(validated_blocks),
    )
    return InspectionResult(document=document, diagnostics=tuple(diagnostics))


def _resolve_phase_times(
    normalized_blocks: list[dict[str, object]],
    *,
    global_start_time: str,
    diagnostics: list[Diagnostic],
) -> tuple[list[int | None], list[int | None]]:
    if not normalized_blocks:
        return [], []

    has_duration = any(block["duration_minutes"] is not None for block in normalized_blocks)

    starts: list[int | None] = [None] * len(normalized_blocks)
    ends: list[int | None] = [None] * len(normalized_blocks)

    if has_duration:
        if not global_start_time:
            diagnostics.append(
                Diagnostic(
                    code="KZF130",
                    severity="error",
                    message="Dauer-Modus (t=...) erfordert globale Startzeit im Front-Matter (start: HH:MM).",
                )
            )
            return starts, ends

        cursor = _parse_time_to_minutes(global_start_time)
        if cursor is None:
            diagnostics.append(
                Diagnostic(
                    code="KZF131",
                    severity="error",
                    message=f"Ungueltige globale Startzeit: {global_start_time}.",
                )
            )
            return starts, ends

        for index, block in enumerate(normalized_blocks):
            duration = block["duration_minutes"]
            line = int(block["line"])
            if duration is None:
                diagnostics.append(
                    Diagnostic(
                        code="KZF132",
                        severity="error",
                        message="Alle Phasen muessen t=... setzen, wenn Dauer-Modus verwendet wird.",
                        line=line,
                    )
                )
                continue

            if cursor is None:
                continue

            start_text = str(block["start_time"] or "").strip()
            if start_text:
                explicit_start = _parse_time_to_minutes(start_text)
                if explicit_start is None:
                    diagnostics.append(
                        Diagnostic(
                            code="KZF134",
                            severity="error",
                            message=f"Ungueltige Startzeit im Header: {start_text}.",
                            line=line,
                        )
                    )
                elif explicit_start != cursor:
                    diagnostics.append(
                        Diagnostic(
                            code="KZF136",
                            severity="warning",
                            message=(
                                "start=... passt nicht zur fortlaufenden t=...-Berechnung und wird ignoriert."
                            ),
                            line=line,
                        )
                    )

            starts[index] = cursor
            cursor = cursor + int(duration)
            ends[index] = cursor

        return starts, ends

    for index, block in enumerate(normalized_blocks):
        line = int(block["line"])
        start_text = str(block["start_time"] or "").strip()
        if index == 0 and not start_text:
            start_text = global_start_time.strip()

        if not start_text:
            diagnostics.append(
                Diagnostic(
                    code="KZF133",
                    severity="error",
                    message="Startzeit-Modus erwartet start=HH:MM pro Phase (oder globale Startzeit fuer die erste Phase).",
                    line=line,
                )
            )
            continue

        parsed_start = _parse_time_to_minutes(start_text)
        if parsed_start is None:
            diagnostics.append(
                Diagnostic(
                    code="KZF134",
                    severity="error",
                    message=f"Ungueltige Startzeit im Header: {start_text}.",
                    line=line,
                )
            )
            continue

        starts[index] = parsed_start

    for index in range(len(normalized_blocks) - 1):
        if starts[index + 1] is not None:
            ends[index] = starts[index + 1]

    return starts, ends


def _normalize_phase(raw_phase: str) -> str | None:
    normalized = " ".join((raw_phase or "").strip().lower().split())
    return _PHASE_LOOKUP.get(normalized)


def _normalize_optional(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def _parse_time_to_minutes(time_text: str) -> int | None:
    match = _TIME_RE.fullmatch(str(time_text or "").strip())
    if not match:
        return None

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    return hour * 60 + minute


def _to_roman(number: int) -> str:
    if number <= 0:
        return ""

    numeral_map = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = number
    chunks: list[str] = []
    for value, symbol in numeral_map:
        while remaining >= value:
            chunks.append(symbol)
            remaining -= value
    return "".join(chunks)
