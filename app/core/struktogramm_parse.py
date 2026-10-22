"""Parser für den Inhalt von `:::struktogramm`: Text → Elementbaum.

Syntax (Gestalt nach GO Informatik, Ergänzende Hinweise S. 5–6): eine Zeile
ist ein Element, die Einrückung (Tab = 4 Leerzeichen; die Einheit setzt die
erste eingerückte Zeile) bestimmt die Schachtelung. Schlüsselwörter am
Zeilenanfang (Groß-/Kleinschreibung egal):

=================  ==========================================================
`wenn B`           Verzweigung, Rumpf eingerückt; optional `sonst` + Rumpf
`auswahl A`        Mehrfachauswahl; darin `fall W` + Rumpf, optional `sonst`
`solange`/`für`    kopfgesteuerte Schleife (Text wird wörtlich angezeigt)
`wiederhole …`     mit weiterem Text: kopfgesteuert (`wiederhole 100-mal`)
`wiederhole`       allein: fußgesteuert, Rumpf, dann gleiche Ebene `bis B`
`rückgabe X`       Rückgabe, angezeigt als „gib X zurück“
`eingabe x`        Eingabe, angezeigt als „lies x ein“
=================  ==========================================================

Jede andere Zeile ist eine Anweisung; ein `\\` am Zeilenanfang hebt ein
Schlüsselwort auf. `<-` wird als `←` gesetzt.

Arbeitsblatt/Lösung: Die Marker `§`/`%`/`&` stehen *nach* der Einrückung
und gelten für den angezeigten Text des Elements; Inline-Tokens `%{…}` usw.
wirken auf Teiltexte. Die Marker-Logik selbst stammt unverändert aus
`answer_line_markers.py` -- hier wird nur vorher die Einrückung abgetrennt.

Der Parser ist fehlertolerant: Er liefert immer einen (ggf. unvollständigen)
Baum plus `ParseIssue`s, damit Vorschau und Validator dieselbe Quelle haben.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .answer_line_markers import MARKER_SHOW_MODE, _extract_leading_line_marker, parse_answer_line_visibility

TAB_WIDTH = 4
RETURN_TEMPLATE = ("gib ", " zurück")
"""Präfix/Suffix der Rückgabe-Anzeige (GO-Formulierung „gib … zurück“)."""
INPUT_TEMPLATE = ("lies ", " ein")
"""Präfix/Suffix der Eingabe-Anzeige; die GO gibt keine Formulierung vor."""
FOOT_LOOP_PREFIX = "wiederhole bis "

_KEYWORDS = frozenset({"wenn", "sonst", "auswahl", "fall", "solange", "für", "wiederhole", "bis", "rückgabe", "eingabe"})
_TEXT_REQUIRED = frozenset({"wenn", "auswahl", "fall", "solange", "für", "bis", "rückgabe", "eingabe"})
_HEAD_RE = re.compile(r"^(\S+)(?:\s+(.*))?$")
INDENTED_LINE_MARKER_RE = re.compile(r"^\s*([§%&])(?=\s|$)")
"""Zeilenmarker *nach* der Einrückung -- gilt nur im Inhalt von Struktogramm-Blöcken.
Gemeinsame Quelle für Editor-Highlighting (`blatt_ui_editor_highlight.py`); die
VSCode-Grammatik spiegelt dieselbe Regel (Guardrail 5, Marker-Konsistenz)."""
STRUKTOGRAMM_HEADER_RE = re.compile(r"^\s*:::(?:struktogramm|structogram)(?=\s|$)")
"""Erkennt die Kopfzeile eines Struktogramm-Blocks (Hauptname oder Alias)."""


@dataclass(frozen=True)
class Cell:
    """Angezeigter Text eines Elements als Marker-Segmente (`text`, `show`)."""

    segments: tuple[dict, ...]

    @property
    def text(self) -> str:
        """Gesamttext aller Segmente unabhängig von der Sichtbarkeit."""
        return "".join(segment["text"] for segment in self.segments)


@dataclass
class Statement:
    """Anweisung (`kind="plain"`), Rückgabe (`"return"`) oder Eingabe (`"input"`)."""

    line: int
    cell: Cell
    kind: str = "plain"


@dataclass
class Branch:
    """Verzweigung; `has_else` unterscheidet „kein sonst“ von „leerem sonst“."""

    line: int
    condition: Cell
    yes: list = field(default_factory=list)
    no: list = field(default_factory=list)
    has_else: bool = False


@dataclass
class Case:
    """Ein `fall`-Zweig einer Mehrfachauswahl."""

    line: int
    value: Cell
    body: list = field(default_factory=list)


@dataclass
class Switch:
    """Mehrfachauswahl; `default` ist `None` ohne `sonst`."""

    line: int
    expression: Cell
    cases: list = field(default_factory=list)
    default: list | None = None


@dataclass
class Loop:
    """Schleife; `kind` ist `"head"` (Kopfzeile oben) oder `"foot"` (Fußzeile unten)."""

    line: int
    kind: str
    text: Cell
    body: list = field(default_factory=list)


@dataclass(frozen=True)
class ParseIssue:
    """Strukturfehler mit Validator-Code und 1-basierter Zeile im Blockinhalt."""

    code: str
    severity: str
    line: int
    message: str


@dataclass(frozen=True)
class _Line:
    """Vorverarbeitete, nicht leere Quellzeile."""

    number: int
    level: int
    keyword: str | None
    rest: str
    body_text: str
    show: str


def _cell(text: str, show: str, prefix: str = "", suffix: str = "") -> Cell:
    """Baut eine Zelle; Inline-Tokens im Text werden per Marker-Logik zerlegt."""
    parsed = parse_answer_line_visibility(text, default_show=show) if text else {"segments": []}
    segments = [{"text": seg["text"].replace("<-", "←"), "show": seg["show"]} for seg in parsed["segments"]]
    if prefix:
        segments.insert(0, {"text": prefix, "show": show})
    if suffix:
        segments.append({"text": suffix, "show": show})
    return Cell(tuple(segments))


def _indent_width(raw_line: str) -> int:
    """Breite des führenden Leerraums, Tab = `TAB_WIDTH` Leerzeichen."""
    leading = raw_line[: len(raw_line) - len(raw_line.lstrip())]
    return len(leading.expandtabs(TAB_WIDTH))


def _split_keyword(text: str) -> tuple[str | None, str]:
    """Trennt ein führendes Schlüsselwort ab; `\\`-Präfix verhindert das."""
    if text.startswith("\\"):
        return None, text
    match = _HEAD_RE.match(text)
    word = match.group(1).lower() if match else ""
    if word not in _KEYWORDS:
        return None, text
    return word, (match.group(2) or "").strip()


def _preprocess(content: str, issues: list) -> list[_Line]:
    """Zerlegt den Blockinhalt in `_Line`s und prüft die Einrückung (`SG001`)."""
    lines: list[_Line] = []
    unit = 0
    for number, raw in enumerate(str(content or "").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        width = _indent_width(raw)
        if width and not unit:
            unit = width
        if unit and width % unit:
            issues.append(ParseIssue("SG001", "error", number, f"Einrückung passt nicht zur Einheit von {unit} Leerzeichen."))
        marker, after = _extract_leading_line_marker(stripped)
        keyword, rest = _split_keyword(after)
        level = width // unit if unit else 0
        lines.append(_Line(number, level, keyword, rest, after, MARKER_SHOW_MODE.get(marker, "both")))
    return lines


class _Parser:
    """Rekursiver Abstieg über die vorverarbeiteten Zeilen (fehlertolerant)."""

    def __init__(self, lines: list[_Line], issues: list):
        """Merkt sich Zeilen und die gemeinsame Issue-Liste."""
        self.lines = lines
        self.issues = issues
        self.pos = 0

    def _peek(self) -> _Line | None:
        """Nächste ungelesene Zeile oder `None` am Ende."""
        return self.lines[self.pos] if self.pos < len(self.lines) else None

    def _issue(self, code: str, line: _Line, message: str) -> None:
        """Hängt einen Fehler zur Zeile `line` an."""
        self.issues.append(ParseIssue(code, "error", line.number, message))

    def sequence(self, level: int) -> list:
        """Liest Elemente der Ebene `level`, bis eine flachere Zeile kommt."""
        elements = []
        while (line := self._peek()) is not None and line.level >= level:
            if line.level > level:
                # Einmal pro verwaistem Teilbaum melden, nicht pro Zeile.
                self._issue("SG002", line, "Zeile ist eingerückt, gehört aber zu keinem Kopf (wenn/auswahl/Schleife).")
                while (deeper := self._peek()) is not None and deeper.level > level:
                    self.pos += 1
                continue
            element = self._element(level)
            if element is not None:
                elements.append(element)
        return elements

    def _body(self, level: int) -> list:
        """Liest den eingerückten Rumpf unter einem Kopf der Ebene `level`."""
        line = self._peek()
        return self.sequence(level + 1) if line is not None and line.level > level else []

    def _next_is(self, level: int, keyword: str) -> bool:
        """True, wenn die nächste Zeile auf Ebene `level` mit `keyword` beginnt."""
        line = self._peek()
        return line is not None and line.level == level and line.keyword == keyword

    def _element(self, level: int):
        """Liest genau ein Element (inkl. Rumpf) ab der aktuellen Zeile."""
        line = self.lines[self.pos]
        self.pos += 1
        keyword = line.keyword
        if keyword in _TEXT_REQUIRED and not line.rest:
            self._issue("SG006", line, f"`{keyword}` braucht einen Text dahinter.")
        if keyword in {"sonst", "fall", "bis"}:
            self._issue("SG003", line, f"`{keyword}` ohne passenden Kopf (wenn/auswahl/wiederhole) davor.")
            self._body(level)
            return None
        if keyword == "wenn":
            return self._branch(line, level)
        if keyword == "auswahl":
            return self._switch(line, level)
        if keyword in {"solange", "für"} or (keyword == "wiederhole" and line.rest):
            return self._loop(line, level, "head", _cell(line.body_text, line.show))
        if keyword == "wiederhole":
            return self._foot_loop(line, level)
        if keyword == "rückgabe":
            return Statement(line.number, _cell(line.rest, line.show, *RETURN_TEMPLATE), "return")
        if keyword == "eingabe":
            return Statement(line.number, _cell(line.rest, line.show, *INPUT_TEMPLATE), "input")
        return Statement(line.number, _cell(line.body_text, line.show))

    def _branch(self, line: _Line, level: int) -> Branch:
        """`wenn` + Rumpf, optional `sonst` + Rumpf auf derselben Ebene."""
        branch = Branch(line.number, _cell(line.rest, line.show), yes=self._body(level))
        if self._next_is(level, "sonst"):
            self.pos += 1
            branch.has_else = True
            branch.no = self._body(level)
        return branch

    def _switch(self, line: _Line, level: int) -> Switch:
        """`auswahl` mit `fall`-Zeilen (und optional `sonst`) eine Ebene tiefer."""
        switch = Switch(line.number, _cell(line.rest, line.show))
        while (child := self._peek()) is not None and child.level > level:
            self.pos += 1
            if child.level != level + 1 or child.keyword not in {"fall", "sonst"} or switch.default is not None:
                self._issue("SG008", child, "In `auswahl` sind nur `fall …`-Zeilen und ein abschließendes `sonst` erlaubt.")
                self._body(child.level)
                continue
            if child.keyword == "fall":
                if not child.rest:
                    self._issue("SG006", child, "`fall` braucht einen Wert dahinter.")
                switch.cases.append(Case(child.number, _cell(child.rest, child.show), self._body(level + 1)))
            else:
                switch.default = self._body(level + 1)
        if not switch.cases:
            self._issue("SG005", line, "`auswahl` braucht mindestens einen `fall`.")
        return switch

    def _loop(self, line: _Line, level: int, kind: str, text: Cell) -> Loop:
        """Schleife mit Rumpf; ein leerer Rumpf ist `SG005`."""
        loop = Loop(line.number, kind, text, self._body(level))
        if not loop.body:
            self._issue("SG005", line, "Schleife ohne eingerückten Rumpf.")
        return loop

    def _foot_loop(self, line: _Line, level: int) -> Loop:
        """`wiederhole` allein: Rumpf, danach Pflichtzeile `bis …` (`SG004`)."""
        loop = self._loop(line, level, "foot", _cell("", line.show, FOOT_LOOP_PREFIX))
        if not self._next_is(level, "bis"):
            self._issue("SG004", line, "`wiederhole` ohne abschließendes `bis …` auf derselben Ebene.")
            return loop
        until = self.lines[self.pos]
        self.pos += 1
        if not until.rest:
            self._issue("SG006", until, "`bis` braucht eine Bedingung dahinter.")
        loop.text = _cell(until.rest, until.show, FOOT_LOOP_PREFIX)
        return loop


def parse_struktogramm(content: str) -> tuple[list, list[ParseIssue]]:
    """Parst den Blockinhalt; liefert `(elemente, issues)`, nie eine Ausnahme.

    Example:
        >>> elements, issues = parse_struktogramm("wenn x > 0\\n    rückgabe x\\nrückgabe 0")
        >>> [type(e).__name__ for e in elements], issues
        (['Branch', 'Statement'], [])
    """
    issues: list[ParseIssue] = []
    parser = _Parser(_preprocess(content, issues), issues)
    elements = parser.sequence(0)
    return elements, sorted(issues, key=lambda issue: issue.line)


def iter_cells(elements):
    """Liefert alle Zellen des Baums (Tiefensuche), z. B. für Wortsuchen."""
    for element in elements:
        if isinstance(element, Statement):
            yield element.cell
        elif isinstance(element, Branch):
            yield element.condition
            yield from iter_cells(element.yes)
            yield from iter_cells(element.no)
        elif isinstance(element, Switch):
            yield element.expression
            for case in element.cases:
                yield case.value
                yield from iter_cells(case.body)
            yield from iter_cells(element.default or [])
        elif isinstance(element, Loop):
            yield element.text
            yield from iter_cells(element.body)
