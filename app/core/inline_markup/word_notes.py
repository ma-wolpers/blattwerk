"""Worterklärung `??Begriff|Erklärung??` als geschützte Span-Familie.

Wie Mathe (`math_span_protection.py`) und Code (`spans.py::protect_code`)
wird eine Worterklärung VOR den Marker-Durchläufen aus dem Text
herausgelöst und durch ein Platzhalter-Token ersetzt; `placeholders.py`
macht daraus im letzten Parser-Schritt einen `Run` mit `annotation`.

Warum keine Marker-Durchlauf-Variante wie `!!...!!`: jeder Durchlauf in
`emphasis.py::_expand_runs` baut Runs nur aus den Stil-Flags neu auf und
würde ein Zusatzfeld wie `annotation` verwerfen.

"Geschützt" heißt hier: nachfolgende Parser-Durchläufe interpretieren den
Inhalt nicht als weiteres Markup und können ihn nicht beschädigen. Es heißt
NICHT, dass innerhalb einer Worterklärung verschachteltes Markup unterstützt
wird -- Begriff und Erklärung sind reiner Text (`*x*` bleibt `*x*`).

Grammatik (streng, kein stilles Tolerieren):
- Einzeilig: `??` Begriff `|` Erklärung `??`.
- `|` ist der einzige strukturelle Trenner, genau einmal. `\\|` ist ein
  wörtliches `|`, `\\??` ein wörtliches `??` (auch außerhalb einer
  Worterklärung).
- Fehlendes `|`, mehr als ein `|` oder ein leerer Begriff/eine leere
  Erklärung ist ein Parserfehler (`IM002`, `severity="error"`). Der
  fehlerhafte Text bleibt dabei unverändert als Text stehen, damit nichts
  verschwindet; der Build wird über den Validator blockiert.

Sammelmechanismus: `collect_word_notes()` öffnet einen Kontext, in dem der
Renderer jede tatsächlich gerenderte Worterklärung registriert
(`record_word_note`). So weiß das Layout explizit, ob und welche
Worterklärungen ein Dokument enthält -- ohne im fertigen HTML nach
Zeichenketten zu suchen.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from .runs import IM002_MALFORMED_WORD_NOTE, ParseDiagnostic

_WORD_NOTE_PLACEHOLDER_START = ""
_WORD_NOTE_PLACEHOLDER_END = ""
"""Private-Use-Zeichen, disjunkt von Mathe (U+E000/U+E001), Code
(U+F000/U+F001) und Escapes (ab U+F020)."""

_WORD_NOTE_PLACEHOLDER_PATTERN = re.compile(
    f"{_WORD_NOTE_PLACEHOLDER_START}(\\d+){_WORD_NOTE_PLACEHOLDER_END}"
)
_CANDIDATE_PATTERN = re.compile(r"(?<!\\)\?\?([^\n]+?)(?<!\\)\?\?")
_UNESCAPED_PIPE_PATTERN = re.compile(r"(?<!\\)\|")


@dataclass(frozen=True)
class WordNoteSpan:
    """Eine geschützte Worterklärung: Begriff und Erklärung als reiner, entescapter Text."""

    term: str
    explanation: str


def _unescape(text: str) -> str:
    return text.replace("\\|", "|").replace("\\??", "??")


def parse_word_note_content(content: str) -> tuple[WordNoteSpan | None, str | None]:
    """Zerlegt den Inhalt zwischen `??` und `??` in Begriff und Erklärung.

    Liefert `(span, None)` bei gültigem Inhalt, sonst `(None, Fehlermeldung)`.
    """
    parts = _UNESCAPED_PIPE_PATTERN.split(content)
    if len(parts) != 2:
        return None, (
            f"Worterklärung `??{content}??` braucht genau ein `|` zwischen Begriff und "
            f"Erklärung (gefunden: {len(parts) - 1}). Ein wörtliches `|` schreibt man `\\|`, "
            "ein wörtliches `??` schreibt man `\\??`."
        )
    term, explanation = _unescape(parts[0]).strip(), _unescape(parts[1]).strip()
    if not term or not explanation:
        return None, (
            f"Worterklärung `??{content}??` hat einen leeren Begriff oder eine leere Erklärung."
        )
    return WordNoteSpan(term=term, explanation=explanation), None


def protect_word_notes(text: str) -> tuple[str, list[WordNoteSpan], list[ParseDiagnostic]]:
    """Ersetzt gültige `??Begriff|Erklärung??` durch Platzhalter und meldet fehlerhafte als `IM002`.

    Läuft nach Kommentaren, Mathe und Code (deren Inhalt ist dann schon
    Platzhalter und wird nie als Worterklärung gelesen). Außerhalb von
    Worterklärungen wird ein `\\??` zu wörtlichem `??` aufgelöst.
    """
    if not text or "?" not in text:
        return text, [], []

    spans: list[WordNoteSpan] = []
    diagnostics: list[ParseDiagnostic] = []
    pieces: list[str] = []
    last_end = 0

    for match in _CANDIDATE_PATTERN.finditer(text):
        pieces.append(text[last_end : match.start()].replace("\\??", "??"))
        span, error = parse_word_note_content(match.group(1))
        if span is None:
            diagnostics.append(
                ParseDiagnostic(
                    code=IM002_MALFORMED_WORD_NOTE,
                    severity="error",
                    message=error or "",
                    position=match.start(),
                )
            )
            pieces.append(match.group(0))
        else:
            pieces.append(f"{_WORD_NOTE_PLACEHOLDER_START}{len(spans)}{_WORD_NOTE_PLACEHOLDER_END}")
            spans.append(span)
        last_end = match.end()

    pieces.append(text[last_end:].replace("\\??", "??"))
    return "".join(pieces), spans, diagnostics


def find_word_note_placeholder(text: str, start: int = 0) -> re.Match[str] | None:
    """Sucht das nächste Worterklärungs-Platzhalter-Token ab `start` -- für `placeholders.py`."""
    return _WORD_NOTE_PLACEHOLDER_PATTERN.search(text, start)


@dataclass(frozen=True)
class WordNoteOccurrence:
    """Eine tatsächlich gerenderte Worterklärung (Begriff + Erklärung), für Layout und PDF-Prüfung."""

    term: str
    explanation: str


_active_collector: ContextVar[list[WordNoteOccurrence] | None] = ContextVar(
    "word_note_collector", default=None
)


@contextmanager
def collect_word_notes():
    """Sammelt alle im Kontext gerenderten Worterklärungen in der gelieferten Liste."""
    occurrences: list[WordNoteOccurrence] = []
    token = _active_collector.set(occurrences)
    try:
        yield occurrences
    finally:
        _active_collector.reset(token)


def record_word_note(term: str, explanation: str) -> None:
    """Registriert eine gerenderte Worterklärung beim aktiven Sammler (No-Op ohne Sammler)."""
    collector = _active_collector.get()
    if collector is not None:
        collector.append(WordNoteOccurrence(term=term, explanation=explanation))
