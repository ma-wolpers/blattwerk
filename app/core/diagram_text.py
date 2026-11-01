"""Gemeinsame Textbausteine aller Diagrammblöcke: Quellzeilen, Zellen, Arbeitsblatt/Lösung.

Einzige Quelle für drei Regeln, die jeder Diagrammblock gleich braucht:

* **Quellzeilen** (`iter_source_lines`): Leerzeilen und reine `%%Kommentar%%`-
  Zeilen zählen nicht, die Zeilennummer bleibt die im Block sichtbare. Der
  Marker `§`/`%`/`&` steht *nach* der Einrückung (Einrückung ist Syntax).
* **Zellen** (`make_cell`, `Cell`): angezeigter Text als Marker-Segmente,
  Inline-Tokens `%{…}` usw. über `answer_line_markers`.
* **Darstellung** (`render_cell`): Lösungstext ist im Arbeitsblatt unsichtbar,
  aber platzhaltend (`diagram-hidden`), in der Lösung farbig markiert.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from typing import Iterator

from .answer_line_markers import (
    MARKER_SHOW_MODE,
    _extract_leading_line_marker,
    _render_inline_markdown_fragment,
    _wrap_solution_fragment,
    parse_answer_line_visibility,
)
from .inline_markup.spans import blank_comment_only_lines

TAB_WIDTH = 4
INDENTED_LINE_MARKER_RE = re.compile(r"^\s*([§%&])(?=\s|$)")
"""Zeilenmarker *nach* der Einrückung -- gilt nur im Inhalt von Diagrammblöcken.
Gemeinsame Quelle für Editor-Highlighting (`blatt_ui_editor_highlight.py`); die
VSCode-Grammatik spiegelt dieselbe Regel (Guardrail 5, Marker-Konsistenz)."""


@dataclass(frozen=True)
class Cell:
    """Angezeigter Text eines Elements als Marker-Segmente (`text`, `show`)."""

    segments: tuple[dict, ...]

    @property
    def text(self) -> str:
        """Gesamttext aller Segmente unabhängig von der Sichtbarkeit."""
        return "".join(segment["text"] for segment in self.segments)


@dataclass(frozen=True)
class ParseIssue:
    """Strukturfehler mit Validator-Code und 1-basierter Zeile im Blockinhalt."""

    code: str
    severity: str
    line: int
    message: str


@dataclass(frozen=True)
class SourceLine:
    """Eine inhaltlich relevante Quellzeile eines Diagrammblocks.

    Attributes:
        number: 1-basierte Zeile im Blockinhalt (für Meldungen).
        width: Breite der Einrückung in Leerzeichen (Tab = `TAB_WIDTH`).
        show: Sichtbarkeit aus dem Zeilenmarker (`both`, `worksheet`, `solution`).
        text: Text ohne Einrückung und ohne Zeilenmarker.
    """

    number: int
    width: int
    show: str
    text: str


def _indent_width(raw_line: str) -> int:
    """Breite des führenden Leerraums, Tab = `TAB_WIDTH` Leerzeichen."""
    leading = raw_line[: len(raw_line) - len(raw_line.lstrip())]
    return len(leading.expandtabs(TAB_WIDTH))


def iter_source_lines(content) -> Iterator[SourceLine]:
    """Liefert die relevanten Zeilen eines Blockinhalts.

    Args:
        content: *Roher* Blockinhalt, nie durch `normalize_markdown` geschickt.

    Yields:
        `SourceLine` je Zeile, ohne Leerzeilen und reine Kommentarzeilen.
    """
    for number, raw in enumerate(blank_comment_only_lines(str(content or "")).splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        marker, after = _extract_leading_line_marker(stripped)
        yield SourceLine(number, _indent_width(raw), MARKER_SHOW_MODE.get(marker, "both"), after)


def make_cell(text: str, show: str = "both", prefix: str = "", suffix: str = "") -> Cell:
    """Baut eine Zelle; Inline-Tokens im Text werden per Marker-Logik zerlegt.

    Args:
        text: Anzeigetext, darf `%{…}`/`§{…}`/`&{…}` enthalten; `<-` wird `←`.
        show: Sichtbarkeit des Texts außerhalb von Inline-Tokens.
        prefix: Fester Text davor, mit derselben Sichtbarkeit wie die Zeile.
        suffix: Fester Text dahinter, mit derselben Sichtbarkeit wie die Zeile.
    """
    parsed = parse_answer_line_visibility(text, default_show=show) if text else {"segments": []}
    segments = [{"text": seg["text"].replace("<-", "←"), "show": seg["show"]} for seg in parsed["segments"]]
    if prefix:
        segments.insert(0, {"text": prefix, "show": show})
    if suffix:
        segments.append({"text": suffix, "show": show})
    return Cell(tuple(segments))


def plain_cell(text: str) -> Cell:
    """Zelle aus festem Text: `&`, `%` und `§` bleiben Zeichen, keine Marker (Gatter `&`, Terminale)."""
    return Cell(({"text": text, "show": "both"},))


def _merged_segments(segments) -> list[tuple[str, str]]:
    """Fasst benachbarte Segmente gleicher Sichtbarkeit zu `(show, text)` zusammen.

    So wird `% rückgabe x` (Präfix, Ausdruck, Suffix) *eine* Lücke statt drei
    einzelner Spans, und Markdown sieht zusammenhängenden Text.
    """
    merged: list[tuple[str, str]] = []
    for segment in segments:
        if merged and merged[-1][0] == segment["show"]:
            merged[-1] = (segment["show"], merged[-1][1] + segment["text"])
        else:
            merged.append((segment["show"], segment["text"]))
    return merged


def render_cell(cell: Cell, include_solutions: bool) -> tuple[str, bool]:
    """Rendert eine Zelle; liefert `(html, ist_lücke)`.

    Segmente nur fürs Arbeitsblatt (`§`) fehlen in der Lösung; Segmente nur
    für die Lösung (`%`) sind in der Lösung farbig markiert (wie in anderen
    Antwortblöcken) und im Arbeitsblatt unsichtbar, aber platzhaltend.
    """
    parts: list[str] = []
    has_gap = False
    for show, text in _merged_segments(cell.segments):
        # Vor Markdown escapen: Bedingungen wie `a<b` dürfen nie als HTML-Tag gelesen werden.
        fragment = _render_inline_markdown_fragment(escape(text, quote=False), inline_only=True)
        if not fragment:
            continue
        if include_solutions:
            if show == "worksheet":
                continue
            parts.append(_wrap_solution_fragment(fragment) if show == "solution" else fragment)
        elif show == "solution":
            has_gap = True
            parts.append(f"<span class='diagram-hidden'>{fragment}</span>")
        else:
            parts.append(fragment)
    return "".join(parts), has_gap
