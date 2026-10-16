"""Punkt-Suffix eines Lösungspunkts: einzige Grammatik und einzige Anzeigeform.

Ein Suffix ist eine Klammer am Ende der (sichtbaren) Kopfzeile eines
Lösungspunkts (`solution_structure`). Jede Kopfzeile hat genau einen Status:

==========  ==================================================  ==================
Status      Bedingung                                           Zahlenwert
==========  ==================================================  ==================
`none`      kein Kandidat (s. u.) -- die Klammer ist Text       --
`valid`     strenge Grammatik passt                             `value`, `path`
`legacy`    alte Teilpunkt-Schreibweise `(x/nP …)`              **keiner**
`invalid`   Kandidat, aber weder `valid` noch `legacy`          **keiner**
==========  ==================================================  ==================

**Kandidat** ist eine Klammer am Zeilenende, deren Inhalt mit einer Zahl
beginnt (davor optional ein Minuszeichen) und ein `P` enthält, auf das
Leerraum oder das Klammerende folgt. `(3 Punkte)` oder `(2 Pkt)` sind
keine Kandidaten und bleiben gewöhnlicher Text (wie bisher).

Prüfreihenfolge `valid` → `legacy` → `invalid`: eine alte Schreibweise
ist nie zugleich `invalid` (keine Doppelmeldung SL014/SL018). `legacy` und
`invalid` tragen bewusst **keinen** Zahlenwert, damit sie in keine Summe
eingehen können.

Gültige Grammatik (wächst nur zusammen mit ihrer Semantik):
`([−] Zahl [Weg] P)` -- Zahl mit Komma oder Punkt, Weg ein Kleinbuchstabe
direkt vor `P`, Leerraum erlaubt (`(0,5aP)`, `(1 b P)`). Ein Minuszeichen
(`-`, `−` oder `–`) macht den Punkt zum **Abzug je Fehler** (`value < 0`):
Abzüge zählen in keine Summe und gelten für die ganze (Teil-)Aufgabe, ein
Weg-Buchstabe daran wird ignoriert (SL016).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from .points_model import format_signed_points, parse_points

SUFFIX_NONE = "none"
SUFFIX_VALID = "valid"
SUFFIX_LEGACY = "legacy"
SUFFIX_INVALID = "invalid"

SUFFIX_GRAMMAR_HINT = (
    "`(Zahl P)`, für alternative Wege mit Buchstabe vor dem P, z. B. `(0,5aP)` und `(1bP)`, "
    "für Abzüge je Fehler mit Minus, z. B. `(−0,5P)`"
)
"""Kurzbeschreibung der gültigen Grammatik für Diagnosetexte (SL014/SL018)."""

_CANDIDATE_RE = re.compile(r"\((?P<body>\s*[-−–]?\s*\d[^()]*)\)\s*$")
_P_TOKEN_RE = re.compile(r"P(?=\s|$)")
_VALID_BODY_RE = re.compile(r"^\s*(?P<sign>[-−–])?\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?P<path>[a-z])?\s*P\s*$")
_LEGACY_BODY_RE = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*/\s*\d+(?:[.,]\d+)?\s*P(?:\s[^()]*)?$")


@dataclass(frozen=True)
class PointsSuffix:
    """Ergebnis von `parse_points_suffix` (siehe Tabelle im Moduldocstring).

    Attributes:
        status: `SUFFIX_NONE`, `SUFFIX_VALID`, `SUFFIX_LEGACY` oder `SUFFIX_INVALID`.
        span: Zeichenbereich der Klammer in der Kopfzeile (ohne Leerraum am
            Ende), bei `none` ``None``.
        value: Punktzahl, nur bei `valid`; negativ bei einem Abzug.
        path: Weg-Buchstabe, nur bei `valid` mit Buchstabe (bei Abzügen
            ohne Wirkung, siehe `is_deduction`).
    """

    status: str
    span: tuple[int, int] | None = None
    value: Decimal | None = None
    path: str | None = None

    @property
    def is_deduction(self) -> bool:
        """Ob das Suffix ein Abzug je Fehler ist (gültig mit Minuszeichen)."""
        return self.value is not None and self.value < 0

    def text_in(self, head: str) -> str:
        """Der Suffix-Text in `head` (leer bei `none`), z. B. für Diagnosetexte."""
        return head[self.span[0]:self.span[1]] if self.span else ""


def parse_points_suffix(head: str) -> PointsSuffix:
    """Klassifiziert das Suffix einer sichtbaren Kopfzeile (nur dafür gedacht, nicht für beliebige Zeilen)."""
    match = _CANDIDATE_RE.search(head or "")
    if match is None or not _P_TOKEN_RE.search(match.group("body")):
        return PointsSuffix(SUFFIX_NONE)
    span = (match.start(), match.start() + len(match.group(0).rstrip()))
    valid = _VALID_BODY_RE.match(match.group("body"))
    if valid:
        value = parse_points(valid.group("value"))
        return PointsSuffix(SUFFIX_VALID, span, -value if valid.group("sign") else value, valid.group("path"))
    if _LEGACY_BODY_RE.match(match.group("body")):
        return PointsSuffix(SUFFIX_LEGACY, span)
    return PointsSuffix(SUFFIX_INVALID, span)


def has_points_candidate(line: str) -> bool:
    """Ob `line` mit einem Punkt-Kandidaten endet (Grundlage für SL004 an Nicht-Kopfzeilen)."""
    return parse_points_suffix(line).status != SUFFIX_NONE


def strip_valid_suffix(head: str, suffix: PointsSuffix) -> str:
    """Kopfzeile ohne gültiges Suffix; andere Status bleiben als sichtbarer Text stehen."""
    if suffix.status != SUFFIX_VALID:
        return head
    return head[: suffix.span[0]].rstrip()


def display_suffix(suffix: PointsSuffix) -> str:
    """Anzeigeform eines gültigen Suffixes in der Lösung: `(0,5P)`, `(0,5P, Weg a)`, `(−0,5P)`.

    Abzüge zeigen nie einen Weg (der Buchstabe ist wirkungslos, SL016).
    """
    text = f"{format_signed_points(suffix.value)}P"
    if suffix.path and not suffix.is_deduction:
        text += f", Weg {suffix.path}"
    return f"({text})"
