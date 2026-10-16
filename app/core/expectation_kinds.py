"""Erwartungstypen für Lösungspunkte: Katalog und einzige Auflösung des Typ-Tokens.

Ein Lösungspunkt kann im Punkt-Suffix optional einen Typ tragen, als Kürzel
oder ganzes Wort (`(0,5P An)`, `(0,5P Ansatz)`, `(−1P Bg)`). Der Typ sagt,
*was für eine Leistung* erwartet wird; der Erwartungshorizont zeigt dafür das
Symbol vor dem Text und eine Legende der tatsächlich verwendeten Typen.
„Rechnung“ ist bewusst kein eigener Typ, sondern ein Fall von Anwendung.

Die Auflösung ignoriert Groß-/Kleinschreibung und akzeptiert Name, Kürzel
und die angegebenen Aliasse (z. B. Umlaut-Ersatzschreibungen). Alle Tokens
sind über den ganzen Katalog eindeutig (Test `test_tokens_are_unique`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectationKind:
    """Ein Erwartungstyp.

    Attributes:
        key: interner Schlüssel (stabil, z. B. für Tests).
        label: Anzeigename in der Legende.
        symbol: Emoji vor dem Erwartungstext im Erwartungshorizont.
        abbreviation: Kürzel für das Suffix.
        aliases: weitere erlaubte Schreibweisen (zusätzlich zu Name und Kürzel).
    """

    key: str
    label: str
    symbol: str
    abbreviation: str
    aliases: tuple[str, ...] = ()

    def tokens(self) -> tuple[str, ...]:
        """Alle erlaubten Schreibweisen (Name, Kürzel, Aliasse), kleingeschrieben."""
        return tuple(token.casefold() for token in (self.label, self.abbreviation, *self.aliases))


EXPECTATION_KINDS: tuple[ExpectationKind, ...] = (
    ExpectationKind("ansatz", "Ansatz", "💡", "An"),
    ExpectationKind("anwendung", "Anwendung", "🛠️", "Aw"),
    ExpectationKind("antwortsatz", "Antwortsatz", "💬", "Sa"),
    ExpectationKind("fachsprache", "Fachsprache", "📚", "Fs"),
    ExpectationKind("entscheidung", "Entscheidung", "⚖️", "En"),
    ExpectationKind("ergebnis", "Ergebnis", "✅", "Er"),
    ExpectationKind("beobachtung", "Beobachtung", "🔍", "Be"),
    ExpectationKind("begruendung", "Begründung", "🧩", "Bg", ("Begruendung",)),
    ExpectationKind("einheit", "Einheit/Größe", "📏", "Ei", ("Einheit", "Größe", "Groesse")),
    ExpectationKind("darstellung", "Darstellung", "📐", "Da"),
)
"""Katalog in Legendenreihenfolge (Wunschliste Blattwerk → Klausur, 2026-10-16)."""

_BY_TOKEN = {token: kind for kind in EXPECTATION_KINDS for token in kind.tokens()}
_BY_KEY = {kind.key: kind for kind in EXPECTATION_KINDS}


def resolve_expectation_kind(token: str | None) -> ExpectationKind | None:
    """Typ zu einem Token aus dem Suffix (ohne Groß-/Kleinschreibung), sonst ``None``."""
    if not token:
        return None
    return _BY_TOKEN.get(token.strip().casefold())


def kind_by_key(key: str) -> ExpectationKind:
    """Typ zu einem internen Schlüssel (für Anzeige aus `SolutionItem.kind`)."""
    return _BY_KEY[key]


def valid_kinds_hint() -> str:
    """Liste der gültigen Typen für Diagnosetexte, z. B. `Ansatz (An), Anwendung (Aw), …`."""
    return ", ".join(f"{kind.label} ({kind.abbreviation})" for kind in EXPECTATION_KINDS)
