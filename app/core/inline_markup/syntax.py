"""Single-Source-of-Truth für die Inline-Markup-Syntax von Blattwerk.

Jeder Eintrag in `MARKER_SPECS` beschreibt EINEN Marker und seine
Eskalationsstufen. `spans.py`/`emphasis.py` (Parser), `editor_marker_shortcuts.py`
(Editor-UX) und `markdown_conventions.py` (Doku-Generator) lesen
ausschließlich aus dieser Tabelle -- keine der drei Stellen definiert
Marker-Wissen ein zweites Mal. Die tatsächlichen Erkennungs-Algorithmen
(Regex/Delimiter-Stack) leben in `spans.py`/`emphasis.py`, weil sie sich
nicht rein deklarativ aus dieser Tabelle ableiten lassen (insbesondere die
gestaffelte `*`-Eskalation `**so*etwas***`) -- aber welche Zeichenfolge
welche Bedeutung hat, steht ausschließlich hier.

Autoritative Auswertungsreihenfolge (siehe `spans.py`/`emphasis.py` für die
Umsetzung, `__init__.py::parse_inline_markup` für den Gesamtablauf):

    1. `%%...%%`-Kommentare erkennen und verwerfen
    2. `$...$`/`$$...$$`-Mathematik schützen (math_span_protection.py)
    3. Code-Spans/Fenced-Code-Blöcke schützen
    4. verbleibendes Markup parsen (diese Tabelle)
    5. `list[Run]` erzeugen
    6. rendern (html_renderer.py)

Kommentare kommen bewusst VOR Mathematik: sie dürfen beliebigen, auch
absichtlich malformten Beispieltext enthalten (z. B. eine nicht
geschlossene Formel als Warnbeispiel), und dürfen daher nie mit Mathe
außerhalb des Kommentars "verschmelzen" können. Mit Kommentaren zuerst
sieht der Mathe-Schutz einen bereits verworfenen Kommentarinhalt nie.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationLevel:
    """Eine Eskalationsstufe eines Markers: wie sie im Quelltext aussieht und was sie bedeutet."""

    delimiter: str
    """Das Marker-Zeichen wiederholt auf dieser Stufe, z. B. `"**"` für Fett."""

    example: str
    """Kurzes Beispiel für die Doku-Generierung, z. B. `"**fett**"`."""

    style_flags: tuple[str, ...]
    """Welche `Run`-Stil-Flags diese Stufe setzt, z. B. `("bold",)`."""

    description: str
    """Kurze deutsche Beschreibung für die generierte Anleitung."""


@dataclass(frozen=True)
class MarkerSpec:
    """Ein einzelner Inline-Marker: Editor-Taste, Eskalationsstufen, Anwendbarkeit."""

    name: str
    key: str
    levels: tuple[EscalationLevel, ...]
    editor_shortcut: bool
    """Ob dieser Marker direkt über eine eigene Editor-Taste ausgelöst wird.

    `False` bedeutet nicht "kein Editor-Zugriff", sondern "wird über die
    Eskalationsstufe eines anderen Eintrags ausgelöst" (z. B. `strike` über
    die zweite Stufe der `~`-Taste, `fenced_code` über mehrzeilige Auswahl
    bei der `` ` ``-Taste) oder "kein Editor-Shortcut in dieser Iteration"
    (`comment`).
    """

    applies_to: frozenset[str]
    """Dokumenttypen, in denen dieser Marker gerendert wird."""


ALL_DOCUMENT_TYPES: frozenset[str] = frozenset({"worksheet", "kurzentwurf"})

MARKER_SPECS: tuple[MarkerSpec, ...] = (
    MarkerSpec(
        name="emphasis_star",
        key="*",
        levels=(
            EscalationLevel("*", "*kursiv*", ("italic",), "Kursiv"),
            EscalationLevel("**", "**fett**", ("bold",), "Fett"),
            EscalationLevel(
                "***", "***fett und kursiv***", ("bold", "italic"), "Fett und kursiv"
            ),
        ),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="emphasis_underscore",
        key="_",
        levels=(
            EscalationLevel("_", "_kursiv_", ("italic",), "Kursiv (Alias)"),
            EscalationLevel("__", "__unterstrichen__", ("underline",), "Unterstrichen"),
        ),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="highlight",
        key="=",
        levels=(EscalationLevel("==", "==Hervorhebung==", ("highlight",), "Hervorhebung"),),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="subscript",
        key="~",
        levels=(EscalationLevel("~", "~tief~ / ~{tief}", ("subscript",), "Tiefgestellt"),),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="strike",
        key="~~",
        levels=(EscalationLevel("~~", "~~durchgestrichen~~", ("strike",), "Durchgestrichen"),),
        editor_shortcut=False,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="superscript",
        key="^",
        levels=(EscalationLevel("^", "^hoch^ / ^{hoch}", ("superscript",), "Hochgestellt"),),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="code",
        key="`",
        levels=(EscalationLevel("`", "`code`", (), "Inline-Code"),),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="fenced_code",
        key="```",
        levels=(EscalationLevel("```", "``` / code / ```", (), "Codeblock (mehrzeilig)"),),
        editor_shortcut=False,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="spoiler",
        key="|",
        levels=(
            EscalationLevel("||", "||spoiler||", ("spoiler",), "Spoiler (nur beim Markieren lesbar)"),
        ),
        editor_shortcut=True,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="comment",
        key="%%",
        levels=(EscalationLevel("%%", "%%Kommentar%%", (), "Kommentar (kein sichtbarer Output)"),),
        editor_shortcut=False,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
    MarkerSpec(
        name="operator",
        key="!!",
        levels=(
            EscalationLevel(
                "!!", "!!Bestimme!!", ("bold", "operator"), "Aufgaben-Operator (sichtbar wie Fett)"
            ),
        ),
        editor_shortcut=False,
        applies_to=ALL_DOCUMENT_TYPES,
    ),
)


def marker_spec_by_name(name: str) -> MarkerSpec:
    """Liefert die `MarkerSpec` mit gegebenem `name`; wirft `KeyError`, wenn unbekannt."""
    for spec in MARKER_SPECS:
        if spec.name == name:
            return spec
    raise KeyError(f"Unbekannter Marker: {name!r}")


def marker_spec_by_key(key: str) -> MarkerSpec | None:
    """Liefert die `MarkerSpec` mit gegebener Editor-Taste (`key`), oder `None`."""
    for spec in MARKER_SPECS:
        if spec.key == key:
            return spec
    return None
