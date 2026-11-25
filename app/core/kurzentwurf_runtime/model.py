from __future__ import annotations

from dataclasses import dataclass


PHASE_PLACEMENT_REGULAR = "regular"
PHASE_PLACEMENT_BUFFER = "buffer"
PHASE_PLACEMENT_AFTER_LESSON = "after_lesson"
"""Werte für `PhaseSpec.placement`."""


@dataclass(frozen=True)
class PhaseSpec:
    """Einzige Quelle für eine Kurzentwurf-Phase: Anzeigename, `#`-Hashtag, Zeitpflicht.

    `display_name` ist der interne/kanonische Phasenname (verwendet in
    `KurzentwurfPhaseBlock.phase`/`display_phase` und Fehlermeldungen wie
    `KZF011`). `hashtag` ist der Text, den Autor:innen tatsächlich nach `#`
    tippen müssen -- **nicht** identisch mit `display_name` (z. B.
    `Ergebnissicherung` -> `#sicherung`, `Didaktische Reserve` -> `#reserve`).

    `placement` sagt, wohin die Phase im Verlauf gehört: `regular` überall,
    `buffer` (Didaktische Reserve) an die Stelle, an der sie inhaltlich
    stattfinden würde, nie ans Ende des Verlaufs (`KZF049`), `after_lesson`
    (Hausaufgabe) hinter die Stunde; sie zählt beim Suchen der letzten Phase
    nicht mit.
    """

    display_name: str
    hashtag: str
    requires_explicit_time: bool
    placement: str = PHASE_PLACEMENT_REGULAR


PHASE_SPECS: tuple[PhaseSpec, ...] = (
    PhaseSpec("Einstieg", "einstieg", True),
    PhaseSpec("Erarbeitung", "erarbeitung", True),
    PhaseSpec("Ergebnissicherung", "sicherung", True),
    PhaseSpec("Vertiefung", "vertiefung", True),
    PhaseSpec("Hausaufgabe", "hausaufgabe", False, PHASE_PLACEMENT_AFTER_LESSON),
    PhaseSpec("Didaktische Reserve", "reserve", False, PHASE_PLACEMENT_BUFFER),
)

ALLOWED_PHASES: tuple[str, ...] = tuple(spec.display_name for spec in PHASE_SPECS)


@dataclass(frozen=True)
class LineMarkerSpec:
    """Ein von `_MARKER_RE` (`dsl_segments.py`) erkannter Zeilenmarker -- rein strukturelle Fakten.

    `target_field` ist das `RawSegment`-Feld, in das der Marker schreibt.
    `accepts_inline_value` ist `False` für `A>`: Inhalt auf derselben Zeile
    wie `A>` ist ungültig (`KZF150`) -- `A>` schaltet nur die aktive Spalte,
    der Inhalt muss auf einer folgenden `s<`-Zeile stehen. `rejected=True`
    für `ant>`: wird vom Regex erkannt, ist aber **kein** gültiger Alias von
    `ant<` und erzeugt immer `KZF153`.
    """

    token: str
    target_field: str
    accepts_inline_value: bool
    rejected: bool = False


LINE_MARKER_SPECS: tuple[LineMarkerSpec, ...] = (
    LineMarkerSpec("S>", "schritte", True),
    LineMarkerSpec("A>", "aktivitaeten", False),
    LineMarkerSpec("s<", "aktivitaeten", True),
    LineMarkerSpec("U>", "umgebung", True),
    LineMarkerSpec("ant<", "antizipiert", True),
    LineMarkerSpec("ant>", "antizipiert", True, rejected=True),
)

@dataclass(frozen=True)
class SocialFormSpec:
    """Einzige Quelle für eine in `U>` erkannte Sozialform.

    `abbreviation` ist das empfohlene Kürzel, `aliases` sind weitere
    Schreibweisen, die als dieselbe Sozialform zählen (Groß/Klein egal).
    `conversation` sagt, ob in dieser Sozialform ein Unterrichtsgespräch
    stattfindet. Nur dort sind Antizipationen (`ant<`) mündliche Äußerungen
    der Lernenden, die der Kurzentwurf erwartet (`KZF152`). In reinen
    Arbeitsformen entfällt die Erwartung, statt Arbeitsergebnisse künstlich
    als Äußerungen zu formulieren.
    """

    abbreviation: str
    meaning: str
    conversation: bool
    aliases: tuple[str, ...] = ()

    @property
    def tokens(self) -> tuple[str, ...]:
        """Kürzel und alle Schreibweisen, für den Vergleich in Kleinbuchstaben."""
        return tuple(token.casefold() for token in (self.abbreviation, *self.aliases))


SOCIAL_FORM_SPECS: tuple[SocialFormSpec, ...] = (
    SocialFormSpec(
        "LSG",
        "Lehrer-Schüler-Gespräch: die Lehrkraft moderiert, Lernende antworten",
        True,
        ("Lehrer-Schüler-Gespräch", "Unterrichtsgespräch", "UG"),
    ),
    SocialFormSpec(
        "SSG",
        "Schüler-Schüler-Gespräch: Lernende geben sich gegenseitig Feedback, ohne Moderation der Lehrkraft",
        True,
        ("Schüler-Schüler-Gespräch",),
    ),
    SocialFormSpec(
        "Plenum",
        "Gespräch der ganzen Lerngruppe; unscharf, besser LSG oder SSG",
        True,
        ("Diskussion",),
    ),
    SocialFormSpec("EA", "Einzelarbeit: Lernende arbeiten allein", False, ("Einzelarbeit", "Stillarbeit")),
    SocialFormSpec("PA", "Partnerarbeit: Lernende arbeiten zu zweit", False, ("Partnerarbeit",)),
    SocialFormSpec("GA", "Gruppenarbeit: Lernende arbeiten in Kleingruppen", False, ("Gruppenarbeit",)),
)

CONVERSATION_SOCIAL_FORM_TOKENS: frozenset[str] = frozenset(
    token for spec in SOCIAL_FORM_SPECS if spec.conversation for token in spec.tokens
)
WORK_SOCIAL_FORM_TOKENS: frozenset[str] = frozenset(
    token for spec in SOCIAL_FORM_SPECS if not spec.conversation for token in spec.tokens
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
    """Static diagnostic output from parser/validator/export stages.

    `region_id`/`anchor` describe this diagnostic's acknowledgment
    occurrence (see `app.core.diagnostic_identity`) -- set by the
    Kurzentwurf validator itself for its one ackable code (`KZF136`),
    left `None` for the (currently all-error) rest.
    """

    code: str
    severity: str
    message: str
    line: int | None = None
    region_id: str | None = None
    anchor: str | None = None


ACTIVITY_KIND_STUDENT = "s"
ACTIVITY_KIND_ANTICIPATION = "ant"
"""Werte für `ActivityEntry.kind`: `s<`-Eintrag bzw. `ant<`-Block."""


@dataclass(frozen=True)
class ActivityEntry:
    """Ein Eintrag der Spalte Lernaktivitäten: ein `s<`- oder ein `ant<`-Block.

    Die Spalte ist eine **geordnete** Folge solcher Einträge in
    Quellreihenfolge, damit jede Antizipation unter dem `s<` gerendert wird,
    hinter dem sie im Quelltext steht. `text` enthält den (mehrzeiligen)
    Rohinhalt ohne Marker.
    """

    kind: str
    text: str


def activity_text(entries: tuple[ActivityEntry, ...], kind: str) -> str | None:
    """Verbindet die Texte aller Einträge einer Art (`kind`) zeilenweise.

    Einzige Ableitung der früheren Einzelfelder `aktivitaeten`/`antizipiert`
    aus `activities`; liefert `None`, wenn es keinen Eintrag dieser Art gibt.
    """
    texts = [entry.text for entry in entries if entry.kind == kind and entry.text.strip()]
    return "\n".join(texts) if texts else None


@dataclass(frozen=True)
class RawSegment:
    """Raw segment inside one phase block before semantic validation.

    `activities` ist die einzige Quelle der Spalte Lernaktivitäten;
    `aktivitaeten`/`antizipiert` sind daraus abgeleitet.
    """

    schritte: str | None
    umgebung: str | None
    line: int
    activities: tuple[ActivityEntry, ...] = ()
    full_row: bool = False

    @property
    def aktivitaeten(self) -> str | None:
        """Alle `s<`-Texte des Segments (ohne Antizipationen)."""
        return activity_text(self.activities, ACTIVITY_KIND_STUDENT)

    @property
    def antizipiert(self) -> str | None:
        """Alle `ant<`-Texte des Segments."""
        return activity_text(self.activities, ACTIVITY_KIND_ANTICIPATION)


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
    """Validated segment with explicit inheritance flags for rowspan rendering.

    `activities` enthält die Lernaktivitäten in Quellreihenfolge (ggf. mit
    geerbten `s<`-Einträgen davor); `aktivitaeten`/`antizipiert` sind daraus
    abgeleitet.
    """

    schritte: str
    umgebung: str
    inherit_schritte: bool
    inherit_aktivitaeten: bool
    inherit_umgebung: bool
    line: int
    activities: tuple[ActivityEntry, ...] = ()
    full_row: bool = False

    @property
    def aktivitaeten(self) -> str:
        """Alle `s<`-Texte des Segments (ohne Antizipationen)."""
        return activity_text(self.activities, ACTIVITY_KIND_STUDENT) or ""

    @property
    def antizipiert(self) -> str:
        """Alle `ant<`-Texte des Segments."""
        return activity_text(self.activities, ACTIVITY_KIND_ANTICIPATION) or ""


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
