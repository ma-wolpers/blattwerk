"""Kurzentwurf-DSL V2: Haupteinstiegspunkt (öffentliche Fassade).

Schlanker Orchestrator (300-Zeilen-Konvention): die Zeilen-für-Zeile-
Zustandsmaschine bleibt hier, aber Segment-Aufbau (`dsl_segments.py`),
Phasen-Header-Parsing (`dsl_phases.py`) und Frontmatter/Meta-Zeilen-
Parsing (`dsl_frontmatter.py`) sind ausgelagert. Externer Code
importiert weiterhin `parse_kurzentwerfer_text` unverändert aus
`app.core.kurzentwurf_runtime.dsl` (siehe `validator.py`).
"""

from __future__ import annotations

from dataclasses import dataclass

from .dsl_frontmatter import _META_RE, _canonical_meta_key, _parse_front_matter, _strip_optional_quotes
from .dsl_phases import _PhaseBuilder, _build_phase_from_header, _finalize_phase
from .dsl_segments import _MARKER_RE, _SegmentBuilder, _finalize_segment, _is_column_switch_line
from .model import Diagnostic, RawPhaseBlock


@dataclass(frozen=True)
class ParsedKurzentwurf:
    """Syntactic parse result for Kurzentwerfer source text."""

    title: str
    subtitle: str
    global_start_time: str
    phases: tuple[RawPhaseBlock, ...]
    diagnostics: tuple[Diagnostic, ...]


def parse_kurzentwerfer_text(source: str) -> ParsedKurzentwurf:
    """Parse Kurzentwerfer DSL V2 into raw phase blocks."""

    lines = source.splitlines()
    title = "Kurzentwurf"
    subtitle = ""
    global_start_time = ""
    phases: list[RawPhaseBlock] = []
    diagnostics: list[Diagnostic] = []

    phase_builder: _PhaseBuilder | None = None
    segment_builder = _SegmentBuilder()

    line_index = 0
    front_matter, line_index = _parse_front_matter(lines, diagnostics)
    if "title" in front_matter:
        title = front_matter["title"]
    if "subtitle" in front_matter:
        subtitle = front_matter["subtitle"]
    if "start" in front_matter:
        global_start_time = front_matter["start"]

    while line_index < len(lines):
        raw_line = lines[line_index]
        stripped = raw_line.strip()

        if not stripped:
            line_index += 1
            continue

        if stripped.startswith("#"):
            _finalize_segment(phase_builder, segment_builder, diagnostics)
            segment_builder = _SegmentBuilder()
            _finalize_phase(phases, phase_builder, diagnostics)

            phase_builder = _build_phase_from_header(stripped, line_number=line_index + 1, diagnostics=diagnostics)
            line_index += 1
            continue

        meta_match = _META_RE.match(stripped)
        if meta_match and phase_builder is None:
            canonical_key = _canonical_meta_key(meta_match.group("key"))
            value = _strip_optional_quotes(meta_match.group("value").strip())
            if canonical_key == "title":
                title = value
            elif canonical_key == "subtitle":
                subtitle = value
            elif canonical_key == "start":
                global_start_time = value
            line_index += 1
            continue

        if phase_builder is None:
            line_index += 1
            continue

        if stripped == "---":
            if phase_builder is None:
                line_index += 1
                continue
            if segment_builder.is_empty():
                diagnostics.append(
                    Diagnostic(
                        code="KZF041",
                        severity="error",
                        message="Leerer Segmenttrenner '---' ohne Inhalte.",
                        line=line_index + 1,
                    )
                )
            else:
                _finalize_segment(phase_builder, segment_builder, diagnostics)
                segment_builder = _SegmentBuilder()
            line_index += 1
            continue

        marker_match = _MARKER_RE.match(stripped)
        if marker_match:
            marker = marker_match.group("marker").lower()
            value = marker_match.group("value").strip()

            if marker == "s>":
                segment_builder.set_marker("schritte", value, line=line_index + 1)
                line_index += 1
                continue

            if marker == "u>":
                segment_builder.set_marker("umgebung", value, line=line_index + 1)
                line_index += 1
                continue

            if marker == "a>":
                segment_builder.has_any_marker = True
                segment_builder.active_column_key = "aktivitaeten"
                segment_builder.last_marker_key = None
                if value:
                    segment_builder.append_implicit_line(value, line=line_index + 1)
                    diagnostics.append(
                        Diagnostic(
                            code="KZF150",
                            severity="error",
                            message=(
                                "Lernaktivitaeten muessen mit s< beginnen. "
                                "A> markiert nur die Spalte Lernaktivitaeten."
                            ),
                            line=line_index + 1,
                        )
                    )
                line_index += 1
                continue

            if marker == "s<":
                segment_builder.active_column_key = "aktivitaeten"
                segment_builder.has_s_marker = True
                segment_builder.set_marker("aktivitaeten", value, line=line_index + 1)
                line_index += 1
                continue

            if marker == "ant>":
                diagnostics.append(
                    Diagnostic(
                        code="KZF153",
                        severity="error",
                        message="Marker ant> ist ungueltig. Bitte ant< verwenden.",
                        line=line_index + 1,
                    )
                )

            if marker == "ant<" or marker == "ant>":
                segment_builder.active_column_key = "aktivitaeten"
                segment_builder.has_ant_marker = True
                segment_builder.set_marker("antizipiert", value, line=line_index + 1)
                # Keep antizipation active so multiline ant< content continues
                # without triggering KZF151 on following lines.
                line_index += 1
                continue

            line_index += 1
            continue

        if _is_column_switch_line(stripped):
            segment_builder.switch_column(len(stripped))
            line_index += 1
            continue

        if "|" in stripped:
            diagnostics.append(
                Diagnostic(
                    code="KZF042",
                    severity="error",
                    message=(
                        "Inline-Pipe-Syntax ist ungueltig. "
                        "Nur alleinstehende '|' in einer Zeile markieren Spaltenwechsel."
                    ),
                    line=line_index + 1,
                )
            )
            line_index += 1
            continue

        target_key = segment_builder.append_implicit_line(raw_line.rstrip(), line=line_index + 1)
        if target_key == "aktivitaeten":
            if not segment_builder.has_s_marker:
                diagnostics.append(
                    Diagnostic(
                        code="KZF151",
                        severity="error",
                        message="Lernaktivitaeten-Zeilen muessen mit s< beginnen.",
                        line=line_index + 1,
                    )
                )
            line_index += 1
            continue

        line_index += 1

    _finalize_segment(phase_builder, segment_builder, diagnostics)
    _finalize_phase(phases, phase_builder, diagnostics)

    return ParsedKurzentwurf(
        title=title,
        subtitle=subtitle,
        global_start_time=global_start_time,
        phases=tuple(phases),
        diagnostics=tuple(diagnostics),
    )
