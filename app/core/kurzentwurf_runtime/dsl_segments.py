"""Kurzentwurf-DSL: Segment-Aufbau innerhalb einer Phase (`S>`/`A>`/`U>`/`s<`/`ant<`, `|`-Spaltenwechsel).

`_SegmentBuilder` sammelt die drei Inhaltsspalten (Lernschritte,
Lernaktivitäten, Lernumgebung) plus Antizipation für ein Segment, bis es
per `_finalize_segment` an den aktuellen `_PhaseBuilder` (siehe
`dsl_phases.py`) angehängt wird.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .dsl_phases import _PhaseBuilder
from .model import Diagnostic, RawSegment

_MARKER_RE = re.compile(r"^(?P<marker>S>|A>|U>|s<|ant<|ant>)\s*(?P<value>.*)$", re.IGNORECASE)


def _normalize_optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def _is_column_switch_line(stripped: str) -> bool:
    return bool(stripped) and all(char == "|" for char in stripped)


@dataclass
class _SegmentBuilder:
    schritte: str | None = None
    aktivitaeten: str | None = None
    umgebung: str | None = None
    antizipiert: str | None = None
    line: int = 0
    last_marker_key: str | None = None
    active_column_key: str = "schritte"
    has_s_marker: bool = False
    has_ant_marker: bool = False
    has_any_marker: bool = False

    def is_empty(self) -> bool:
        values = (self.schritte, self.aktivitaeten, self.umgebung, self.antizipiert)
        return all(not str(item or "").strip() for item in values)

    def set_marker(self, key: str, value: str, *, line: int) -> None:
        if self.line <= 0:
            self.line = line

        self.has_any_marker = True
        self.active_column_key = key
        self._append_to_key(key, value.strip())
        self.last_marker_key = key

    def switch_column(self, step_count: int) -> None:
        self.has_any_marker = True
        order = ("schritte", "aktivitaeten", "umgebung")
        # antizipiert belongs to the activities column for pipe-based switching.
        if self.active_column_key == "antizipiert":
            key = "aktivitaeten"
        else:
            key = self.active_column_key if self.active_column_key in order else "schritte"
        current_index = order.index(key)
        next_index = min(len(order) - 1, current_index + max(1, int(step_count)))
        self.active_column_key = order[next_index]
        self.last_marker_key = self.active_column_key

    def append_implicit_line(self, value: str, *, line: int) -> str:
        if self.line <= 0:
            self.line = line

        key = self.active_column_key
        if key not in {"schritte", "aktivitaeten", "umgebung", "antizipiert"}:
            key = "schritte"
            self.active_column_key = key
        self._append_to_key(key, value.rstrip())
        self.last_marker_key = key
        return key

    def _append_to_key(self, key: str, value: str) -> None:
        text = str(value or "").rstrip()
        if not text:
            return
        current = getattr(self, key)
        if current:
            setattr(self, key, f"{current}\n{text}")
        else:
            setattr(self, key, text)

    def to_raw_segment(self) -> RawSegment:
        line = self.line if self.line > 0 else 1
        return RawSegment(
            schritte=_normalize_optional_text(self.schritte),
            aktivitaeten=_normalize_optional_text(self.aktivitaeten),
            umgebung=_normalize_optional_text(self.umgebung),
            antizipiert=_normalize_optional_text(self.antizipiert),
            line=line,
            full_row=not self.has_any_marker,
        )


def _finalize_segment(
    phase_builder: _PhaseBuilder | None,
    segment_builder: _SegmentBuilder,
    diagnostics: list[Diagnostic],
) -> None:
    if phase_builder is None or segment_builder.is_empty():
        return

    if segment_builder.has_s_marker and not segment_builder.has_ant_marker:
        diagnostics.append(
            Diagnostic(
                code="KZF152",
                severity="warning",
                message=(
                    "Nach s< wurde kein ant< gefunden. "
                    "Fuege ant< fuer Antizipation in dieser Segmentzeile hinzu."
                ),
                line=segment_builder.line,
            )
        )

    phase_builder.segments.append(segment_builder.to_raw_segment())
