"""Schützt atomare Bereiche vor dem Inline-Markup-Parsing, in der autoritativen Reihenfolge.

Reihenfolge (siehe `syntax.py`): Kommentare -> Mathematik -> Code/Fences.
Jeder Schritt ersetzt seine Fundstellen durch einen neutralen Platzhalter
und liefert die entfernten Inhalte zur späteren Wiederherstellung zurück
(Kommentare: verworfen, kein Restore -- nur eine `ParseDiagnostic` bei
einem nicht geschlossenen `%%`). Kein Schritt hier kennt HTML.

Warum Kommentare vor Mathematik laufen: Kommentare sind Autorennotizen und
dürfen *beliebigen*, auch absichtlich malformten Beispieltext enthalten
(z. B. eine nicht geschlossene Formel als Warnbeispiel). Liefe der
Mathe-Schutz zuerst, könnte solcher Beispieltext über die `%%`-Grenze
hinweg mit echter Mathematik außerhalb des Kommentars "verschmelzen" und
diese beschädigen. Mit Kommentaren zuerst sieht der Mathe-Schutz derartigen
Inhalt nie -- er ist bereits entfernt, bevor `math_span_protection.py`
überhaupt zu scannen beginnt.

Warum Code-Platzhalter ANDERE Private-Use-Zeichen verwenden als
`math_span_protection.py`: beide Platzhalter-Familien müssen im selben Text
gleichzeitig existieren können (ein Absatz kann sowohl Mathematik als auch
Code enthalten) und dürfen sich nicht überschneiden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..math_span_protection import protect_math_spans
from .runs import IM001_UNCLOSED_COMMENT, ParseDiagnostic

_COMMENT_PATTERN = re.compile(r"(?<!\\)%%(.*?)(?<!\\)%%", re.DOTALL)
_UNMATCHED_COMMENT_START_PATTERN = re.compile(r"(?<!\\)%%")

_FENCE_PATTERN = re.compile(r"^```[^\n]*\n(.*?)\n^```[ \t]*$", re.DOTALL | re.MULTILINE)
_INLINE_CODE_PATTERN = re.compile(r"(?<!\\)`([^`\n]+?)(?<!\\)`")

_CODE_PLACEHOLDER_START = ""
_CODE_PLACEHOLDER_END = ""
"""Private-Use-Zeichen, bewusst in einem anderen Unicode-Bereich als
`math_span_protection.py`s `\\ue000`/`\\ue001` -- beide Platzhalter-Familien
laufen gleichzeitig durch dieselbe Pipeline und dürfen einander nie
überschneiden. Wie bei der Mathe-Variante: kommt in echtem Autor:innen-Text
praktisch nie vor, kein Inline-Prozessor reagiert darauf."""

_CODE_PLACEHOLDER_PATTERN = re.compile(f"{_CODE_PLACEHOLDER_START}(\\d+){_CODE_PLACEHOLDER_END}")


@dataclass(frozen=True)
class CodeSpan:
    """Ein geschützter Code-Bereich: sein roher (unformatierter) Inhalt und ob er ein Block ist."""

    text: str
    is_block: bool


def strip_comments(text: str) -> tuple[str, list[ParseDiagnostic]]:
    """Entfernt jeden `%%...%%`-Kommentar vollständig aus `text`.

    Escape-bewusst (`(?<!\\\\)%%`): ein `\\%\\%` in einer Formel (z. B.
    `$a\\%\\%b$`) wird nicht als Kommentar-Trenner gelesen. Ein `%%` ohne
    passendes schließendes `%%` bleibt als literaler Text stehen (kein
    stilles Verschlucken des restlichen Dokuments) und erzeugt eine
    `ParseDiagnostic`.
    """
    if not text:
        return text, []

    without_paired = _COMMENT_PATTERN.sub("", text)

    diagnostics: list[ParseDiagnostic] = []
    unmatched = _UNMATCHED_COMMENT_START_PATTERN.search(without_paired)
    if unmatched:
        diagnostics.append(
            ParseDiagnostic(
                code=IM001_UNCLOSED_COMMENT,
                severity="warning",
                message="Nicht geschlossener Kommentar-Marker '%%' -- als normaler Text belassen.",
                position=unmatched.start(),
            )
        )

    return without_paired, diagnostics


def protect_code(text: str) -> tuple[str, list[CodeSpan]]:
    """Schützt Fenced-Code-Blöcke und Inline-Code-Spans vor dem Marker-Parsing.

    Fenced-Blöcke zuerst (mehrzeilig, ` ``` `-begrenzt), danach Inline-Code
    (einzeilig, `` ` ``-begrenzt) auf dem Rest -- ein Fenced-Block kann so
    nie versehentlich als Serie von Inline-Code-Spans zerlegt werden.
    Escape-bewusst wie bei Kommentaren: `` \\` `` bleibt literal.
    """
    if not text:
        return text, []

    spans: list[CodeSpan] = []

    def _replace_fence(match: re.Match[str]) -> str:
        index = len(spans)
        spans.append(CodeSpan(text=match.group(1), is_block=True))
        return f"{_CODE_PLACEHOLDER_START}{index}{_CODE_PLACEHOLDER_END}"

    without_fences = _FENCE_PATTERN.sub(_replace_fence, text)

    def _replace_inline(match: re.Match[str]) -> str:
        index = len(spans)
        spans.append(CodeSpan(text=match.group(1), is_block=False))
        return f"{_CODE_PLACEHOLDER_START}{index}{_CODE_PLACEHOLDER_END}"

    without_code = _INLINE_CODE_PATTERN.sub(_replace_inline, without_fences)
    return without_code, spans


def find_code_placeholder(text: str, start: int = 0) -> re.Match[str] | None:
    """Sucht das nächste Code-Platzhalter-Token ab `start` -- für `emphasis.py`s Run-Expansion."""
    return _CODE_PLACEHOLDER_PATTERN.search(text, start)


def protect_all(text: str) -> tuple[str, list[str], list[CodeSpan], list[ParseDiagnostic]]:
    """Wendet Schritt 1-3 der Auswertungsreihenfolge an: Kommentare -> Mathe -> Code.

    Liefert `(geschützter_text, mathe_spans, code_spans, diagnostics)`.
    `mathe_spans[i]` ist die rohe `$...$`/`$$...$$`-Formelquelle (inkl.
    `$`-Begrenzer) für Platzhalter `i` -- identisch zum Rückgabewert von
    `math_span_protection.protect_math_spans`, unverändert durchgereicht.
    """
    without_comments, diagnostics = strip_comments(text)
    without_math, math_spans = protect_math_spans(without_comments)
    without_code, code_spans = protect_code(without_math)
    return without_code, math_spans, code_spans, diagnostics
