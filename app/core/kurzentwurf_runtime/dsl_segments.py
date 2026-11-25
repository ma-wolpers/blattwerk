"""Kurzentwurf-DSL: Segment-Aufbau innerhalb einer Phase (`S>`/`A>`/`U>`/`s<`/`ant<`, `|`-Spaltenwechsel).

`_SegmentBuilder` sammelt die drei Inhaltsspalten (Lernschritte,
Lernaktivitäten, Lernumgebung) plus Antizipation für ein Segment, bis es
per `_finalize_segment` an den aktuellen `_PhaseBuilder` (siehe
`dsl_phases.py`) angehängt wird.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .activity_cell import line_has_quotes
from .dsl_phases import _PhaseBuilder
from .model import (
    ACTIVITY_KIND_ANTICIPATION,
    ACTIVITY_KIND_STUDENT,
    CONVERSATION_SOCIAL_FORM_TOKENS,
    WORK_SOCIAL_FORM_TOKENS,
    ActivityEntry,
    Diagnostic,
    RawSegment,
)
from .region import compute_phase_region_id

_MARKER_RE = re.compile(r"^(?P<marker>S>|A>|U>|s<|ant<|ant>)\s*(?P<value>.*)$", re.IGNORECASE)
_SOCIAL_FORM_WORD_RE = re.compile(r"[\w-]+")
_ACTIVITY_KEY_KINDS = {"aktivitaeten": ACTIVITY_KIND_STUDENT, "antizipiert": ACTIVITY_KIND_ANTICIPATION}
"""Spaltenschlüssel, die in `_SegmentBuilder.activities` statt in ein Textfeld schreiben."""


def expects_anticipation(umgebung: str | None) -> bool:
    """Prüft, ob ein Segment Antizipationen (`ant<`) erwartet (Grundlage von `KZF152`).

    Antizipationen sind mündliche Äußerungen im Unterrichtsgespräch. Nennt
    `U>` nur Arbeitsformen (z. B. `EA`, `PA`, `GA`) und keine Gesprächsform,
    entfällt die Erwartung. Bei einer Gesprächsform (`LSG`, `SSG`, `Plenum`)
    oder wenn keine Sozialform erkennbar ist, bleibt sie bestehen: im Zweifel
    wird erinnert. Die erkannten Schreibweisen stehen nur in
    `model.SOCIAL_FORM_SPECS`.
    """
    words = {word.casefold() for word in _SOCIAL_FORM_WORD_RE.findall(str(umgebung or ""))}
    if words & CONVERSATION_SOCIAL_FORM_TOKENS:
        return True
    return not words & WORK_SOCIAL_FORM_TOKENS


def _normalize_optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def _is_column_switch_line(stripped: str) -> bool:
    return bool(stripped) and all(char == "|" for char in stripped)


@dataclass
class _SegmentBuilder:
    """Sammelt ein Segment bis zu `_finalize_segment`.

    Lernaktivitäten (`s<`) und Antizipationen (`ant<`) liegen gemeinsam und
    geordnet in `activities`, damit jede Antizipation unter ihrem `s<`
    gerendert wird; jeder dieser Marker beginnt einen eigenen Eintrag.
    """

    schritte: str | None = None
    umgebung: str | None = None
    activities: list[ActivityEntry] = field(default_factory=list)
    line: int = 0
    last_marker_key: str | None = None
    active_column_key: str = "schritte"
    has_s_marker: bool = False
    has_ant_marker: bool = False
    has_any_marker: bool = False
    pending_blank_line: bool = False
    ant_quotes_reported: bool = False

    def is_empty(self) -> bool:
        values = (self.schritte, self.umgebung, *(entry.text for entry in self.activities))
        return all(not str(item or "").strip() for item in values)

    def set_marker(self, key: str, value: str, *, line: int) -> None:
        if self.line <= 0:
            self.line = line

        self.has_any_marker = True
        self.pending_blank_line = False
        self.active_column_key = key
        if key in _ACTIVITY_KEY_KINDS:
            # Jeder s<-/ant<-Marker beginnt einen eigenen Eintrag (Quellreihenfolge).
            self.activities.append(ActivityEntry(_ACTIVITY_KEY_KINDS[key], ""))
            self.ant_quotes_reported = False
        self._append_to_key(key, value.strip())
        self.last_marker_key = key

    def report_quoted_ant_line(self, text: str) -> bool:
        """Prüft eine `ant<`-Zeile auf Anführungszeichen (Grundlage von `KZF155`).

        Liefert `True` nur für die erste betroffene Zeile eines `ant<`-Blocks,
        damit ein Block mit vielen zitierten Äußerungen nur eine Warnung
        erzeugt. Die Erkennung liegt in `activity_cell.line_has_quotes` --
        derselben Quelle, die die Zeichen beim Rendern entfernt.
        """
        if self.ant_quotes_reported or not line_has_quotes(text):
            return False
        self.ant_quotes_reported = True
        return True

    def note_blank_line(self) -> None:
        """Merkt eine Leerzeile vor, damit sie als Absatzgrenze in der aktiven Spalte landet.

        Analog zu Arbeitsblättern (`nl2br`): einfacher Zeilenumbruch = `<br>`,
        Leerzeile = neuer Absatz. Die Leerzeile wird bewusst nur *vorgemerkt*
        und erst von der nächsten Folgezeile derselben Spalte eingelöst
        (`append_implicit_line`) -- Leerzeilen vor einem neuen Marker, vor
        `---` oder vor der nächsten `#phase` bleiben damit wirkungslos wie
        bisher und erzeugen keinen leeren Absatz am Zellenende.
        """
        self.pending_blank_line = True

    def ant_outside_activities(self) -> bool:
        """Prüft, ob ein jetzt folgendes `ant<` außerhalb eines A>-Blocks stünde.

        `ant<` gehört ausschließlich hinter ein `s<` in der Spalte
        Lernaktivitäten (also in einen `A>`-Block). Außerhalb steht es, wenn
        im Segment noch kein `s<` vorkam oder die zuletzt aktive Spalte
        Lernschritte (`S>`) bzw. Lernumgebung (`U>`/`|`-Wechsel) ist. Ein
        erneutes `A>` nach `U>` holt die aktive Spalte zurück -- ein `ant<`
        danach gilt wieder als korrekt platziert.

        Wird vor dem Setzen des `ant<`-Markers aufgerufen, weil `set_marker`
        die aktive Spalte auf `antizipiert` umstellt.
        """
        return not self.has_s_marker or self.active_column_key in {"schritte", "umgebung"}

    def switch_column(self, step_count: int) -> None:
        self.has_any_marker = True
        self.pending_blank_line = False
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
        """Hängt eine Folgezeile ohne Marker an die aktive Spalte an.

        Steht eine vorgemerkte Leerzeile (`note_blank_line`) davor und hat
        die Spalte schon Inhalt, wird zusätzlich eine Leerzeile eingefügt,
        die `render_html._render_text` als Absatzgrenze rendert. Liefert den
        tatsächlich befüllten Spaltenschlüssel zurück.
        """
        if self.line <= 0:
            self.line = line

        key = self.active_column_key
        if key not in {"schritte", "aktivitaeten", "umgebung", "antizipiert"}:
            key = "schritte"
            self.active_column_key = key
        current = self._column_text(key)
        if self.pending_blank_line and current:
            self._set_column_text(key, f"{current}\n")
        self.pending_blank_line = False
        self._append_to_key(key, value.rstrip())
        self.last_marker_key = key
        return key

    def _column_text(self, key: str) -> str | None:
        """Aktueller Spaltentext; bei Lernaktivitäten der des letzten Eintrags, falls gleicher Art."""
        if key not in _ACTIVITY_KEY_KINDS:
            return getattr(self, key)
        last = self.activities[-1] if self.activities else None
        return last.text if last is not None and last.kind == _ACTIVITY_KEY_KINDS[key] else None

    def _set_column_text(self, key: str, text: str) -> None:
        """Setzt den Spaltentext; Lernaktivitäten: letzten Eintrag gleicher Art ersetzen, sonst neuer Eintrag."""
        if key not in _ACTIVITY_KEY_KINDS:
            setattr(self, key, text)
            return
        entry = ActivityEntry(_ACTIVITY_KEY_KINDS[key], text)
        if self._column_text(key) is not None:
            self.activities[-1] = entry
        else:
            self.activities.append(entry)

    def _append_to_key(self, key: str, value: str) -> None:
        text = str(value or "").rstrip()
        if not text:
            return
        current = self._column_text(key)
        self._set_column_text(key, f"{current}\n{text}" if current else text)

    def to_raw_segment(self) -> RawSegment:
        line = self.line if self.line > 0 else 1
        return RawSegment(
            schritte=_normalize_optional_text(self.schritte),
            umgebung=_normalize_optional_text(self.umgebung),
            line=line,
            activities=tuple(
                ActivityEntry(entry.kind, entry.text.strip()) for entry in self.activities if entry.text.strip()
            ),
            full_row=not self.has_any_marker,
        )


def _misplaced_ant_diagnostic(phase_builder: _PhaseBuilder, anchor_text: str, *, line: int) -> Diagnostic:
    """Baut die Warnung `KZF154` für ein `ant<` außerhalb eines A>-Blocks.

    Gerendert wird so ein `ant<` trotzdem (immer unter den Lernaktivitäten),
    daher nur eine Warnung: der Quelltext ordnet die Antizipation optisch
    einer anderen Spalte zu und trennt sie von ihrem `s<`. Die Warnung
    trägt die Phasen-Region (Pflicht für abhakbare Warnungen) und ankert am
    Zeilentext statt an der Zeilennummer, damit ein Abhaken beim Einfügen
    von Zeilen davor erhalten bleibt (wie `KZF161`).
    """
    return _ackable_line_warning(
        phase_builder,
        "KZF154",
        "ant< steht außerhalb eines A>-Blocks. "
        "Antizipationen gehören direkt hinter das zugehörige s< (nach A>), "
        "nicht in die Spalten S> oder U>.",
        anchor_text,
        line=line,
    )


def _quoted_ant_diagnostic(phase_builder: _PhaseBuilder, anchor_text: str, *, line: int) -> Diagnostic:
    """Baut die Warnung `KZF155` für Antizipationen in Anführungszeichen.

    Blattwerk setzt die Anführungszeichen um jede Äußerung selbst und
    ignoriert vorhandene beim Rendern (`activity_cell.split_utterance`);
    die Warnung erinnert an die sparsamere Schreibweise. Eine Warnung pro
    `ant<`-Block (siehe `_SegmentBuilder.report_quoted_ant_line`).
    """
    return _ackable_line_warning(
        phase_builder,
        "KZF155",
        "Antizipationen ohne Anführungszeichen schreiben, Blattwerk setzt sie selbst. "
        "Vorhandene Anführungszeichen werden beim Rendern ignoriert.",
        anchor_text,
        line=line,
    )


def _ackable_line_warning(
    phase_builder: _PhaseBuilder, code: str, message: str, anchor_text: str, *, line: int
) -> Diagnostic:
    """Abhakbare Zeilen-Warnung: Phasen-Region plus Zeilentext als Anker (`KZF154`/`KZF155`)."""
    return Diagnostic(
        code=code,
        severity="warning",
        message=message,
        line=line,
        region_id=compute_phase_region_id(
            phase_builder.phase, phase_builder.duration_minutes, phase_builder.start_time
        ),
        anchor=anchor_text,
    )


def _finalize_segment(
    phase_builder: _PhaseBuilder | None,
    segment_builder: _SegmentBuilder,
    diagnostics: list[Diagnostic],
) -> None:
    if phase_builder is None or segment_builder.is_empty():
        return

    if (
        segment_builder.has_s_marker
        and not segment_builder.has_ant_marker
        and expects_anticipation(segment_builder.umgebung)
    ):
        diagnostics.append(
            Diagnostic(
                code="KZF152",
                severity="warning",
                message=(
                    "Nach s< wurde kein ant< gefunden. Füge mündliche Äußerungen hinzu, "
                    "die du im Unterrichtsgespräch erwartest. Ist das Segment eine reine "
                    "Arbeitsphase, nenne die Sozialform in U> (z. B. EA, PA, GA)."
                ),
                line=segment_builder.line,
                region_id=compute_phase_region_id(
                    phase_builder.phase, phase_builder.duration_minutes, phase_builder.start_time
                ),
                anchor=str(segment_builder.line),
            )
        )

    phase_builder.segments.append(segment_builder.to_raw_segment())
