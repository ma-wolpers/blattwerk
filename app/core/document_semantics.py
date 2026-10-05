"""Typidentität und Konsistenzmarker eines Dokuments (Invarianten I1 und I2).

**I1 – Typidentität.** Der Typ einer gespeicherten Datei kommt ausschließlich
aus ihrer Endung (`.abw`, `.pbw`, `.kbw`, `.ebw`, `.md`; Groß/Klein egal).
`type_for_path`/`type_for_tab` sind die einzigen Zugänge; weder das
Frontmatter-Feld `document_type` noch irgendein UI-Zustand ist eine zweite
Typquelle. Für eine nicht erkannte Endung gibt es keinen Typ (``None``) -- die
UI fragt dann, ob die Datei vorübergehend als Markdown interpretiert werden
soll (`interpreted_as_markdown`, nie persistiert).

**I2 – Konsistenzmarker.** `document_type` ist redundant: Pflicht nur in den
vier Blattwerk-Endungen, optional in `.md`. `canonicalize_document_type` ist
die einzige Interpretation des Rohwerts; Quick-Fixes, Templates, Migration
und Speichern-unter schreiben immer den kanonischen Wert. Bei einem
Widerspruch gewinnt immer die Endung.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from .blatt_validator_types import BuildDiagnostic
from .document_type_registry import DOCUMENT_TYPE_MARKDOWN, spec_for_extension, spec_for_type

DOCUMENT_TYPE_KEY = "document_type"
MARKER_REGION_ID = "document:type-marker"

LEGACY_DOCUMENT_TYPE_ALIASES = {
    "arbeitsblatt": "worksheet",
    "slide_deck": "presentation",
    "lesson_plan": "kurzentwurf",
}
"""Nur die bereits existierenden Aliase; neue gibt es nur per Nutzerentscheidung."""


@dataclass(frozen=True)
class Canonical:
    """Gültiger Marker mit kanonischem Typnamen."""

    document_type: str


@dataclass(frozen=True)
class Invalid:
    """Vorhandener, aber ungültiger Marker (Rohwert zur Anzeige)."""

    raw: object


@dataclass(frozen=True)
class Absent:
    """Kein Marker (Key fehlt, `null` oder leerer String)."""


def canonicalize_document_type(raw: object):
    """Interpretiert einen `document_type`-Rohwert eindeutig.

    Regeln:
        * Key fehlt, ``None`` oder leerer bzw. nur aus Leerraum bestehender
          String → `Absent`.
        * Jeder Nicht-String (Zahl, Bool, Liste, Mapping, Datum) → `Invalid`;
          er wird nie in einen String umgewandelt.
        * Strings werden ohne Rücksicht auf Groß/Klein und Leerraum mit den
          kanonischen Typen und den bestehenden Aliasen verglichen; alles
          andere → `Invalid`.

    Returns:
        `Canonical`, `Invalid` oder `Absent`.
    """
    if raw is None:
        return Absent()
    if not isinstance(raw, str):
        return Invalid(raw)
    candidate = raw.strip().lower()
    if not candidate:
        return Absent()
    candidate = LEGACY_DOCUMENT_TYPE_ALIASES.get(candidate, candidate)
    try:
        spec_for_type(candidate)
    except KeyError:
        return Invalid(raw)
    return Canonical(candidate)


def type_for_path(path: str | PurePath | None) -> str | None:
    """Liefert den Dokumenttyp einer gespeicherten Datei allein aus ihrer Endung.

    Returns:
        Kanonischer Typname oder ``None`` bei fehlendem Pfad bzw. nicht
        erkannter Endung (die UI fragt dann nach, statt Markdown anzunehmen).
    """
    if path is None:
        return None
    spec = spec_for_extension(PurePath(str(path)).suffix)
    return spec.id if spec else None


def type_for_tab(path: str | PurePath | None, tab_document_type: str | None) -> str | None:
    """Liefert den Typ eines Tabs.

    Gespeichert (Pfad mit erkannter Endung): der Pfad gewinnt immer, auch wenn
    der Tab-Cache etwas anderes sagt. Ungespeichert bzw. unbekannte Endung:
    der explizite Tab-Typ (gesetzt im Neu-Dialog bzw. durch die Rückfrage
    "Als Markdown interpretieren?").
    """
    from_path = type_for_path(path)
    if from_path is not None:
        return from_path
    if tab_document_type is None:
        return None
    try:
        return spec_for_type(tab_document_type).id
    except KeyError:
        return None


def marker_diagnostics(meta: object, document_type: str) -> list[BuildDiagnostic]:
    """Prüft den Konsistenzmarker gegen den Endungstyp (FM009/FM008/FM010).

    * FM009: Marker fehlt -- nur bei Blattwerk-Typen (`marker_required`).
    * FM008: `document_type` passt nicht zur Dateiendung (gültiger Wert,
      anderer kanonischer Typ). Gilt allgemein, auch für `.md` -- z. B. nach
      Speichern-unter nach `.md`, das den Marker bewusst unverändert lässt.
    * FM010: ungültiger Wert.
    """
    metadata = meta if isinstance(meta, dict) else {}
    spec = spec_for_type(document_type)
    marker = canonicalize_document_type(metadata.get(DOCUMENT_TYPE_KEY))
    if isinstance(marker, Absent):
        if not spec.marker_required:
            return []
        return [
            _diagnostic(
                "FM009",
                f"Frontmatter-Feld `document_type` fehlt. Erwartet: `document_type: {spec.id}` (passend zur Endung {spec.extension}).",
            )
        ]
    if isinstance(marker, Invalid):
        return [
            _diagnostic(
                "FM010",
                f"Ungueltiger Wert fuer `document_type`: {marker.raw!r}. Passend zur Endung {spec.extension} waere `{spec.id}`.",
            )
        ]
    if marker.document_type != spec.id:
        return [
            _diagnostic(
                "FM008",
                f"`document_type: {marker.document_type}` passt nicht zur Dateiendung {spec.extension}; "
                f"es gilt die Endung ({spec.label}). Passend waere `document_type: {spec.id}`.",
            )
        ]
    return []


AID_SPLIT_BLOCK = "aidsplit"
_TASK_RELATED = frozenset({"task", "subtask", "solution"})


MAX_AID_SPLITS = 2
"""Höchstens zwei `--hm`: mit zweitem Marker trennt der erste ein Deckblatt ab."""


@dataclass(frozen=True)
class AidSplit:
    """Gültiger Hilfsmittel-Trenner.

    Attributes:
        index: Blockindex des Trenners zwischen Teil A und Teil B (bei zwei
            Markern der zweite). Alle Teil-Auswertungen nutzen nur ihn.
        cover_end: Blockindex des Deckblatt-Trenners (erster von zwei Markern)
            oder ``None``. Vor ihm stehen keine Aufgaben, daher ändert das
            Deckblatt keine Punkte-/AFB-Auswertung.
    """

    index: int
    cover_end: int | None = None


def aid_split_position_problem(blocks, index: int, start: int = 0) -> str | None:
    """Prüft die Positionsregel „nur zwischen Top-Level-Aufgaben“ (Invariante I5).

    Args:
        blocks: Blockliste des Dokuments.
        index: Blockindex des geprüften `aidsplit`.
        start: Erster Blockindex, der für „Aufgabe davor“ zählt (bei einem
            Deckblatt: direkt nach dem Deckblatt-Trenner, damit Teil A nicht
            leer sein darf).

    Returns:
        ``"KL004"`` (keine Aufgabe davor/danach oder innerhalb von `:::columns`),
        ``"KL005"`` (der nächste aufgabenbezogene Block ist kein `task`) oder ``None``.
    """
    before = [block_type for block_type, _o, _c in blocks[start:index]]
    after = [block_type for block_type, _o, _c in blocks[index + 1 :]]
    if "task" not in before or "task" not in after:
        return "KL004"
    if before.count("columns") > before.count("endcolumns"):
        return "KL004"
    return _next_task_problem(after)


def aid_cover_position_problem(blocks, index: int) -> str | None:
    """Prüft den Deckblatt-Trenner (erster von zwei `--hm`).

    Returns:
        ``"KL007"`` (vor dem Deckblatt-Trenner steht eine Aufgabe, Teilaufgabe
        oder Lösung), ``"KL004"`` (keine Aufgabe danach oder innerhalb von
        `:::columns`), ``"KL005"`` (nächster aufgabenbezogener Block kein `task`)
        oder ``None``.
    """
    before = [block_type for block_type, _o, _c in blocks[:index]]
    after = [block_type for block_type, _o, _c in blocks[index + 1 :]]
    if any(block_type in _TASK_RELATED for block_type in before):
        return "KL007"
    if "task" not in after or before.count("columns") > before.count("endcolumns"):
        return "KL004"
    return _next_task_problem(after)


def _next_task_problem(after) -> str | None:
    next_related = next((block_type for block_type in after if block_type in _TASK_RELATED), None)
    return None if next_related == "task" else "KL005"


def aid_split_indices(blocks) -> list[int]:
    """Blockindizes aller `aidsplit`-Pseudoblöcke in Dokumentreihenfolge."""
    return [index for index, (block_type, _o, _c) in enumerate(blocks) if block_type == AID_SPLIT_BLOCK]


def resolve_aid_split(blocks, document_type: str | None) -> AidSplit | None:
    """Einzige Semantik von `--hm`: nur in Klausuren, ein- oder zweimal, an gültiger Position.

    * ein Marker: Teil A | Teil B
    * zwei Marker: Deckblatt | Teil A | Teil B (das Deckblatt enthält keine Aufgaben)

    Außerhalb von `exam` (oder bei ungültigem Split) gibt es keinen Split: keine
    Teilüberschriften, kein Umbruch, keine Teil-Auswertung.
    """
    if not document_type or not spec_for_type(document_type).aid_split:
        return None
    indices = aid_split_indices(blocks)
    if len(indices) == 1:
        return None if aid_split_position_problem(blocks, indices[0]) else AidSplit(indices[0])
    if len(indices) == MAX_AID_SPLITS:
        cover, split = indices
        if aid_cover_position_problem(blocks, cover) or aid_split_position_problem(blocks, split, start=cover + 1):
            return None
        return AidSplit(split, cover_end=cover)
    return None


def annotate_aid_parts(blocks, document_type: str | None):
    """Ergänzt für das Rendern die Teilmarken A und B.

    Ohne Deckblatt steht „Teil A“ am Dokumentanfang (synthetischer Block) und
    „Teil B“ am Trenner. Mit Deckblatt bleibt die erste Seite ohne
    Teilüberschrift: „Teil A“ steht am Deckblatt-Trenner (`_aid_break`: mit
    Seitenumbruch davor), „Teil B“ am zweiten Trenner. Ohne gültigen Split
    bleibt die Blockliste unverändert (dann rendert `--hm` nichts).
    """
    split = resolve_aid_split(blocks, document_type)
    if split is None:
        return blocks
    annotated = list(blocks)
    block_type, options, content = annotated[split.index]
    annotated[split.index] = (block_type, {**options, "_aid_part": "B"}, content)
    if split.cover_end is not None:
        block_type, options, content = annotated[split.cover_end]
        annotated[split.cover_end] = (block_type, {**options, "_aid_part": "A", "_aid_break": True}, content)
        return annotated
    return [(AID_SPLIT_BLOCK, {"_aid_part": "A"}, "")] + annotated


def is_markdown(document_type: str | None) -> bool:
    """Ob der Typ schlichtes Markdown ist."""
    return document_type == DOCUMENT_TYPE_MARKDOWN


def _diagnostic(code: str, message: str) -> BuildDiagnostic:
    return BuildDiagnostic(code=code, message=message, region_id=MARKER_REGION_ID, anchor=DOCUMENT_TYPE_KEY)
