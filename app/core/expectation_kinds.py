"""Erwartungstypen für Lösungspunkte: Katalog und einzige Auflösung des Typ-Tokens.

Ein Lösungspunkt kann im Punkt-Suffix optional einen Typ tragen, als Kürzel
oder ganzes Wort (`(0,5P An)`, `(0,5P Ansatz)`, `(−1P Bg)`). Der Typ sagt,
*was für eine Leistung* erwartet wird; der Erwartungshorizont zeigt dafür das
Symbol vor dem Text und eine Legende der tatsächlich verwendeten Typen.
„Rechnung“ ist bewusst kein eigener Typ, sondern ein Fall von Anwendung.
„Formales“ meint formale Anforderungen wie eine verlangte Schreibweise
(`S(x_S|y_S)`); sie stehen meist als Abzug bei Nichteinhaltung (`(−0,5P Fo)`).

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
        description: kurzer Erklärsatz für die Legende im Erwartungshorizont.
        aliases: weitere erlaubte Schreibweisen (zusätzlich zu Name und Kürzel).
        deduction_label: Beschriftung eines Abzugs dieses Typs im
            Erwartungshorizont, wenn er nicht „je Fehler“ gilt (`None` =
            „Abzug je Fehler“). Ein Typ mit `deduction_label` ist nur als
            Abzug sinnvoll (Warnung `SL023` sonst).
    """

    key: str
    label: str
    symbol: str
    abbreviation: str
    description: str
    aliases: tuple[str, ...] = ()
    deduction_label: str | None = None

    def tokens(self) -> tuple[str, ...]:
        """Alle erlaubten Schreibweisen (Name, Kürzel, Aliasse), kleingeschrieben."""
        return tuple(token.casefold() for token in (self.label, self.abbreviation, *self.aliases))


EXPECTATION_KINDS: tuple[ExpectationKind, ...] = (
    ExpectationKind("ansatz", "Ansatz", "💡", "An", "Ein passender Lösungsansatz bzw. das Vorgehen ist gewählt und notiert."),
    ExpectationKind("anwendung", "Anwendung", "🛠️", "Aw", "Ein Verfahren ist richtig durchgeführt, z. B. gerechnet, umgeformt oder eingesetzt."),
    ExpectationKind("antwortsatz", "Antwortsatz", "💬", "Sa", "Das Ergebnis ist in einem Satz auf die Frage bezogen formuliert."),
    ExpectationKind("fachsprache", "Fachsprache", "📚", "Fs", "Fachbegriffe sind passend und korrekt verwendet."),
    ExpectationKind("entscheidung", "Entscheidung", "⚖️", "En", "Eine Entscheidung (z. B. wahr/falsch, ja/nein, schneller/langsamer) ist richtig getroffen."),
    ExpectationKind("ergebnis", "Ergebnis", "✅", "Er", "Das (Teil-)Ergebnis ist richtig."),
    ExpectationKind("beobachtung", "Beobachtung", "🔍", "Be", "Etwas ist aus Graph, Tabelle oder Text richtig abgelesen bzw. beschrieben."),
    ExpectationKind("begruendung", "Begründung", "🧩", "Bg", "Eine Aussage ist schlüssig begründet.", ("Begruendung",)),
    ExpectationKind("einheit", "Einheit/Größe", "📏", "Ei", "Die passende Einheit bzw. Größe ist angegeben.", ("Einheit", "Größe", "Groesse")),
    ExpectationKind("darstellung", "Darstellung", "📐", "Da", "Graph, Skizze oder Tabelle ist richtig und sauber dargestellt."),
    ExpectationKind("formales", "Formales", "📝", "Fo", "Eine formale Anforderung ist erfüllt, z. B. eine verlangte Schreibweise.", ("Formal", "Form")),
    ExpectationKind(
        "lernhilfe",  # = LERNHILFE_KIND_KEY
        "Lernhilfe",
        "🛟",
        "Lh",
        "Abzug, wenn die Lernhilfe zu dieser Aufgabe genutzt wurde.",
        deduction_label="Abzug bei Nutzung der Lernhilfe",
    ),
)
"""Katalog in Legendenreihenfolge (Wunschliste Blattwerk → Klausur, 2026-10-16; „Formales“ 2026-10-21;
„Lernhilfe“ 2026-10-27: Klausur-Aufgaben mit Lernhilfe brauchen einen solchen Abzug, sonst `KL013`)."""

LERNHILFE_KIND_KEY = "lernhilfe"
"""Schlüssel des Typs, dessen Abzug in Klausuren die Lernhilfe-Nutzung wertet (`KL013`)."""

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


def is_deduction_only_kind(key: str | None) -> bool:
    """Ob ein Typ nur als Abzug Sinn ergibt (hat eine eigene `deduction_label`)."""
    return bool(key) and kind_by_key(key).deduction_label is not None


def deduction_label_for(key: str | None) -> str:
    """Beschriftung einer Abzugszeile im Erwartungshorizont: eigene des Typs oder „Abzug je Fehler“."""
    if key:
        label = kind_by_key(key).deduction_label
        if label:
            return label
    return "Abzug je Fehler"


def valid_kinds_hint() -> str:
    """Liste der gültigen Typen für Diagnosetexte, z. B. `Ansatz (An), Anwendung (Aw), …`."""
    return ", ".join(f"{kind.label} ({kind.abbreviation})" for kind in EXPECTATION_KINDS)
