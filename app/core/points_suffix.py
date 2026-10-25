"""Punkt-Suffix eines Lösungspunkts: einzige Grammatik und einzige Anzeigeform.

Ein Suffix ist eine Klammer am Ende der (sichtbaren) Kopfzeile eines
Lösungspunkts (`solution_structure`). Jede Kopfzeile hat genau einen Status:

==========  ==================================================  ==================
Status      Bedingung                                           Zahlenwert
==========  ==================================================  ==================
`none`      kein Kandidat (s. u.) -- die Klammer ist Text       --
`valid`     strenge Grammatik passt                             `value`, `path`, `cap`
`invalid`   Kandidat, aber nicht `valid`                        **keiner**
==========  ==================================================  ==================

**Kandidat** ist eine Klammer am Zeilenende, deren Inhalt mit einer Zahl
beginnt (davor optional ein Minuszeichen) und ein `P` enthält, auf das
Leerraum oder das Klammerende folgt. `(3 Punkte)` oder `(2 Pkt)` sind
keine Kandidaten und bleiben gewöhnlicher Text (wie bisher).

`invalid` trägt bewusst **keinen** Zahlenwert, damit ein unlesbares
Suffix in keine Summe eingehen kann (SL018).

Gültige Grammatik (wächst nur zusammen mit ihrer Semantik):
`([−] Zahl [Weg | /Höchstwert] P [Typ])` -- Zahl mit Komma oder Punkt, Weg
ein Kleinbuchstabe direkt vor `P`, Leerraum erlaubt (`(0,5aP)`, `(1 b P)`).
`/k` statt eines Buchstabens macht den Punkt zur **Option**: Optionen
werden summativ gewertet, zusammen höchstens k Punkte (`(1/2P)` = „1 Punkt,
alle Optionen zusammen höchstens 2“). Buchstabe und `/k` zugleich oder ein
Abzug mit `/k` sind ungültig. Typ
Typ ein Wort nach `P` (`(0,5P An)`, `(0,5aP Ansatz)`, Katalog in
`expectation_kinds`). Ein unbekannter Typ lässt das Suffix gültig (Wert und
Weg zählen), nur `kind` bleibt ``None`` (SL017). Ein Minuszeichen
(`-`, `−` oder `–`) macht den Punkt zum **Abzug je Fehler** (`value < 0`):
Abzüge zählen in keine Summe und gelten für die ganze (Teil-)Aufgabe, ein
Weg-Buchstabe daran wird ignoriert (SL016).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from .expectation_kinds import resolve_expectation_kind
from .points_model import format_points, format_signed_points, parse_points

SUFFIX_NONE = "none"
SUFFIX_VALID = "valid"
SUFFIX_INVALID = "invalid"

SUFFIX_GRAMMAR_HINT = (
    "`(Zahl P)`, für alternative Wege mit Buchstabe vor dem P, z. B. `(0,5aP)` und `(1bP)`, "
    "für summative Optionen mit Höchstwert, z. B. `(1/2P)` (alle Optionen zusammen höchstens 2 P), "
    "für Abzüge je Fehler mit Minus, z. B. `(−0,5P)`, optional mit Erwartungstyp nach dem P, z. B. `(0,5P An)`"
)
"""Kurzbeschreibung der gültigen Grammatik für Diagnosetexte (SL018)."""

_CANDIDATE_RE = re.compile(r"\((?P<body>\s*[-−–]?\s*\d[^()]*)\)\s*$")
_P_TOKEN_RE = re.compile(r"P(?=\s|$)")
_POINTS_HEAD = r"\s*(?P<sign>[-−–])?\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?:(?P<path>[a-z])|/\s*(?P<cap>\d+(?:[.,]\d+)?))?\s*P"
"""Gemeinsamer Teil von `_VALID_BODY_RE` und `_KIND_SLOT_RE`: Vorzeichen, Zahl, Weg oder Höchstwert, `P`."""
_VALID_BODY_RE = re.compile(rf"^{_POINTS_HEAD}(?:\s+(?P<kind>[^\s()]+))?\s*$")
_KIND_SLOT_RE = re.compile(rf"\({_POINTS_HEAD}\s+(?P<kind>[^\s()]*)$")


@dataclass(frozen=True)
class PointsSuffix:
    """Ergebnis von `parse_points_suffix` (siehe Tabelle im Moduldocstring).

    Attributes:
        status: `SUFFIX_NONE`, `SUFFIX_VALID` oder `SUFFIX_INVALID`.
        span: Zeichenbereich der Klammer in der Kopfzeile (ohne Leerraum am
            Ende), bei `none` ``None``.
        value: Punktzahl, nur bei `valid`; negativ bei einem Abzug.
        path: Weg-Buchstabe, nur bei `valid` mit Buchstabe (bei Abzügen
            ohne Wirkung, siehe `is_deduction`).
        cap: Höchstwert k einer Option `(x/kP)`, sonst ``None``.
        kind_token: Typ-Token wie geschrieben (`An`, `Ansatz`) oder ``None``.
        kind: Katalogschlüssel aus `expectation_kinds` oder ``None`` (kein
            oder unbekannter Typ).
    """

    status: str
    span: tuple[int, int] | None = None
    value: Decimal | None = None
    path: str | None = None
    kind_token: str | None = None
    kind: str | None = None
    cap: Decimal | None = None

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
    if valid is None or (valid.group("sign") and valid.group("cap")):
        return PointsSuffix(SUFFIX_INVALID, span)
    value = parse_points(valid.group("value"))
    kind = resolve_expectation_kind(valid.group("kind"))
    cap = parse_points(valid.group("cap")) if valid.group("cap") else None
    return PointsSuffix(
        SUFFIX_VALID, span, -value if valid.group("sign") else value, valid.group("path"),
        valid.group("kind"), kind.key if kind else None, cap,
    )


def find_kind_slot(left_text: str) -> tuple[int, str] | None:
    """Ob der Text links vom Cursor in der Typ-Stelle eines Punkt-Suffixes endet.

    Gedacht für die Editor-Completion der Erwartungstypen: `left_text` ist die
    Zeile bis zur Cursorposition. Trifft, wenn sie mit einer geöffneten Klammer
    nach derselben Grammatik wie ein gültiges Suffix endet -- Vorzeichen, Zahl,
    Weg oder Höchstwert, `P` --, gefolgt von mindestens einem Leerzeichen und
    optional einem schon teilweise getippten Typ-Wort (`(0,5P `, `(1aP An`,
    `(−1P Bg`). Die schließende Klammer muss noch nicht stehen. Ob das Wort ein
    bekannter Typ ist, prüft diese Funktion nicht (das ist Sache des Katalogs).

    Args:
        left_text: Zeilentext links vom Cursor.

    Returns:
        ``(start, prefix)`` mit der Spalte, an der das Typ-Wort beginnt, und dem
        bisher getippten Teil (ggf. leer), sonst ``None``. Ungültige Grammatik
        wie `(0,5abP ` oder ein Abzug mit Höchstwert (`(−1/2P `) trifft nicht.
    """
    match = _KIND_SLOT_RE.search(left_text or "")
    if match is None or (match.group("sign") and match.group("cap")):
        return None
    return match.start("kind"), match.group("kind")


def has_points_candidate(line: str) -> bool:
    """Ob `line` mit einem Punkt-Kandidaten endet (Grundlage für SL004 an Nicht-Kopfzeilen)."""
    return parse_points_suffix(line).status != SUFFIX_NONE


def strip_valid_suffix(head: str, suffix: PointsSuffix) -> str:
    """Kopfzeile ohne gültiges Suffix; andere Status bleiben als sichtbarer Text stehen."""
    if suffix.status != SUFFIX_VALID:
        return head
    return head[: suffix.span[0]].rstrip()


def display_suffix(suffix: PointsSuffix) -> str:
    """Anzeigeform in der Lösung: `(0,5P)`, `(0,5P, Weg A)`, `(1P, Option, max. 2P)`, `(−0,5P)`.

    Abzüge zeigen nie einen Weg (der Buchstabe ist wirkungslos, SL016). Das
    Typ-Token wird in der Lösung nie angezeigt (Symbole nur im Erwartungshorizont).
    """
    text = f"{format_signed_points(suffix.value)}P"
    if suffix.path and not suffix.is_deduction:
        text += f", {path_label(suffix.path)}"
    elif suffix.cap is not None:
        text += f", Option, max. {format_points(suffix.cap)}P"
    return f"({text})"


def path_label(letter: str) -> str:
    """Anzeigename eines Wegs: Buchstabe aus dem Suffix großgeschrieben (`a` → `Weg A`)."""
    return f"Weg {letter.upper()}"
