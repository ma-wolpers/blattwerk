from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Diagnostic, RawPhaseBlock, RawSegment

_META_RE = re.compile(
    r"^@(?P<key>title|subtitle|start|start_time|stundenthema|lerngruppe|startuhrzeit|startzeit)\s*:\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
_PHASE_ATTR_RE = re.compile(r"(?P<key>t|start)\s*=\s*(?P<value>[^\s]+)", re.IGNORECASE)
_MARKER_RE = re.compile(r"^(?P<marker>S>|A>|U>|s<|ant<|ant>)\s*(?P<value>.*)$", re.IGNORECASE)

_TITLE_KEYS = {"title", "stundenthema"}
_SUBTITLE_KEYS = {"subtitle", "lerngruppe"}
_START_KEYS = {"start", "start_time", "startuhrzeit", "startzeit"}


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


@dataclass
class _PhaseBuilder:
    phase: str
    duration_minutes: int | None
    start_time: str
    line: int
    segments: list[RawSegment]


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


def _parse_front_matter(
    lines: list[str],
    diagnostics: list[Diagnostic],
) -> tuple[dict[str, str], int]:
    metadata: dict[str, str] = {}

    if not lines:
        return metadata, 0

    first_non_empty = 0
    while first_non_empty < len(lines) and not lines[first_non_empty].strip():
        first_non_empty += 1

    if first_non_empty >= len(lines) or lines[first_non_empty].strip() != "---":
        return metadata, 0

    line_index = first_non_empty + 1
    while line_index < len(lines):
        stripped = lines[line_index].strip()
        if stripped == "---":
            return metadata, line_index + 1

        if not stripped:
            line_index += 1
            continue

        if ":" not in stripped:
            line_index += 1
            continue

        key, value = stripped.split(":", 1)
        canonical_key = _canonical_meta_key(key)
        if canonical_key is not None:
            metadata[canonical_key] = _strip_optional_quotes(value.strip())
        line_index += 1

    diagnostics.append(
        Diagnostic(
            code="KZF045",
            severity="error",
            message="Front-Matter wurde nicht mit --- geschlossen.",
            line=first_non_empty + 1,
        )
    )
    return metadata, len(lines)


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


def _normalize_optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def _is_column_switch_line(stripped: str) -> bool:
    return bool(stripped) and all(char == "|" for char in stripped)


def _canonical_meta_key(raw_key: str) -> str | None:
    normalized = "_".join(str(raw_key or "").strip().lower().replace("-", " ").split())
    if normalized in _TITLE_KEYS:
        return "title"
    if normalized in _SUBTITLE_KEYS:
        return "subtitle"
    if normalized in _START_KEYS:
        return "start"
    return None


def _strip_optional_quotes(text: str) -> str:
    value = str(text or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value



