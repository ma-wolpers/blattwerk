"""Kurzentwurf-DSL: `#phase`-Header-Parsing und Phasen-Finalisierung.

`_build_phase_from_header` liest `t=`/`start=`-Attribute aus einer
`#phase`-Zeile; `_finalize_phase` schließt einen `_PhaseBuilder` ab und
hängt das fertige `RawPhaseBlock` an die Ergebnisliste an (Diagnose
`KZF048`, wenn die Phase keine Segmente enthält).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Diagnostic, RawPhaseBlock, RawSegment

_PHASE_ATTR_RE = re.compile(r"(?P<key>t|start)\s*=\s*(?P<value>[^\s]+)", re.IGNORECASE)


@dataclass
class _PhaseBuilder:
    phase: str
    duration_minutes: int | None
    start_time: str
    line: int
    segments: list[RawSegment]


def _build_phase_from_header(
    stripped_header_line: str,
    *,
    line_number: int,
    diagnostics: list[Diagnostic],
) -> _PhaseBuilder:
    content = stripped_header_line[1:].strip()
    attr_matches = list(_PHASE_ATTR_RE.finditer(content))

    attr_values: dict[str, str] = {}
    for match in attr_matches:
        attr_values[match.group("key").lower()] = match.group("value").strip()

    phase_text = content
    for match in reversed(attr_matches):
        phase_text = phase_text[: match.start()] + phase_text[match.end() :]
    phase_text = " ".join(phase_text.split())

    if not phase_text:
        diagnostics.append(
            Diagnostic(
                code="KZF046",
                severity="error",
                message="#phase-Zeile ohne Phasenname.",
                line=line_number,
            )
        )

    duration_minutes: int | None = None
    duration_text = attr_values.get("t", "").strip()
    if duration_text:
        try:
            duration_minutes = int(duration_text)
            if duration_minutes < 0:
                raise ValueError()
        except ValueError:
            diagnostics.append(
                Diagnostic(
                    code="KZF047",
                    severity="error",
                    message="t=... muss eine positive Ganzzahl in Minuten sein.",
                    line=line_number,
                )
            )

    return _PhaseBuilder(
        phase=phase_text,
        duration_minutes=duration_minutes,
        start_time=attr_values.get("start", "").strip(),
        line=line_number,
        segments=[],
    )


def _finalize_phase(
    phase_blocks: list[RawPhaseBlock],
    phase_builder: _PhaseBuilder | None,
    diagnostics: list[Diagnostic],
) -> None:
    if phase_builder is None:
        return

    if not phase_builder.segments:
        diagnostics.append(
            Diagnostic(
                code="KZF048",
                severity="error",
                message="#phase enthaelt keine Segmente.",
                line=phase_builder.line,
            )
        )

    phase_blocks.append(
        RawPhaseBlock(
            phase=phase_builder.phase,
            duration_minutes=phase_builder.duration_minutes,
            start_time=phase_builder.start_time,
            segments=tuple(phase_builder.segments),
            line=phase_builder.line,
        )
    )
