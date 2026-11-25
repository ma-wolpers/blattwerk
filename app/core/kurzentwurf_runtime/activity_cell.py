"""Kurzentwurf: Spalte Lernaktivitäten (`s<`-Einträge und `ant<`-Antizipationen) als HTML.

Die Einträge kommen geordnet aus `KurzentwurfSegment.activities`; jede
Antizipation erscheint deshalb direkt unter dem `s<`, hinter dem sie im
Quelltext steht.

Antizipationen schreibt man **ohne** Anführungszeichen -- jede Zeile eines
`ant<`-Blocks ist eine Äußerung, Blattwerk setzt „…“ selbst. Eine Klammer
am Zeilenende (z. B. `(Fehlvorstellung)`) ist eine Anmerkung: sie steht
hinter dem schließenden Anführungszeichen und erscheint grau
(`ant-note`). Trotzdem gesetzte Anführungszeichen werden ignoriert und
vom Parser mit `KZF155` gemeldet; beide nutzen `split_utterance`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..inline_markup import render_inline_markup
from ..inline_markup.spans import drop_comment_only_lines
from .cell_html import extract_bullet_text, render_cell_text
from .cell_text import label_entries, strip_hard_break
from .model import ACTIVITY_KIND_ANTICIPATION, ActivityEntry

OPEN_QUOTE = "„"
CLOSE_QUOTE = "“"
ANT_NOTE_CLASS = "ant-note"

_DOUBLE_QUOTES = "„“”\"»«"
"""Doppelte Anführungszeichen: vorn bzw. hinten jeweils einzeln entfernt."""
_SINGLE_QUOTES = "‚‘’'"
"""Einfache Anführungszeichen: nur als Paar entfernt (ein Apostroph wie in `Moritz'` bleibt)."""
_TRAILING_NOTE_RE = re.compile(r"^(?P<text>.*\S)\s*(?P<note>\([^()]*\))$")


@dataclass(frozen=True)
class Utterance:
    """Eine antizipierte Äußerung: Wortlaut ohne Anführungszeichen, Anmerkung, Fundmeldung."""

    text: str
    note: str
    had_quotes: bool


def split_utterance(item: str) -> Utterance:
    """Zerlegt eine `ant<`-Zeile (ohne Aufzählungszeichen) in Wortlaut und Anmerkung.

    Erst wird eine abschließende Klammer als Anmerkung abgetrennt (nur wenn
    davor Text steht), dann werden Anführungszeichen am Rand des Wortlauts
    entfernt. `had_quotes` meldet, ob welche dastanden.
    """
    text = strip_hard_break(item).strip()
    note = ""
    match = _TRAILING_NOTE_RE.match(text)
    if match:
        text, note = match.group("text").strip(), match.group("note")
    unquoted = _strip_quotes(text)
    return Utterance(text=unquoted, note=note, had_quotes=unquoted != text)


def _strip_quotes(text: str) -> str:
    """Entfernt Anführungszeichen am Anfang/Ende (siehe `_DOUBLE_QUOTES`/`_SINGLE_QUOTES`)."""
    if len(text) >= 2 and text[0] in _SINGLE_QUOTES and text[-1] in _SINGLE_QUOTES:
        return text[1:-1].strip()
    if text[:1] in _DOUBLE_QUOTES:
        text = text[1:]
    if text[-1:] in _DOUBLE_QUOTES:
        text = text[:-1]
    return text.strip()


def line_has_quotes(line: str) -> bool:
    """Prüft eine `ant<`-Quellzeile (ggf. mit `- `) auf Anführungszeichen (`KZF155`)."""
    stripped = str(line or "").strip()
    extracted = extract_bullet_text(stripped)
    item = extracted[0] if extracted is not None else stripped
    return bool(item) and split_utterance(item).had_quotes


def render_utterance(item: str) -> str:
    """HTML einer Äußerung: „Wortlaut“ plus graue Anmerkung."""
    utterance = split_utterance(item)
    parts: list[str] = []
    if utterance.text:
        parts.append(f"{OPEN_QUOTE}{render_inline_markup(utterance.text)}{CLOSE_QUOTE}")
    if utterance.note:
        parts.append(f"<span class=\"{ANT_NOTE_CLASS}\">{render_inline_markup(utterance.note)}</span>")
    return " ".join(parts)


def activity_cell_html(entries: tuple[ActivityEntry, ...], *, s_marker_label: str, ant_marker_label: str) -> str:
    """Rendert die Lernaktivitäten-Zelle in Quellreihenfolge.

    Direkt aufeinanderfolgende `s<`-Einträge bilden einen Absatz und
    bekommen je Zeile das Label (`label_entries`); jede Antizipation
    unterbricht ihn mit ihrem Block (`_anticipation_html`).
    Kommentarzeilen fallen vorher weg, damit daraus kein leerer Eintrag wird.
    """
    parts: list[str] = []
    student_texts: list[str] = []

    def flush_student_texts() -> None:
        if student_texts:
            parts.append(render_cell_text(label_entries("\n".join(student_texts), s_marker_label)))
            student_texts.clear()

    for entry in entries:
        text = drop_comment_only_lines(str(entry.text or "")).strip()
        if not text:
            continue
        if entry.kind == ACTIVITY_KIND_ANTICIPATION:
            flush_student_texts()
            parts.append(_anticipation_html(text, ant_marker_label))
        else:
            student_texts.append(text)
    flush_student_texts()
    return "".join(parts)


def _anticipation_html(text: str, marker_label: str) -> str:
    """Ein `ant<`-Block: eine Äußerung steht hinter dem Label, mehrere darunter."""
    label = str(marker_label or "").strip()
    label_html = render_inline_markup(f"**{label}**") if label else ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) == 1:
        extracted = extract_bullet_text(lines[0])
        utterance_html = render_utterance(extracted[0] if extracted is not None else lines[0])
        content = f"{label_html} {utterance_html}" if label_html else utterance_html
        return f"<p class=\"cell-paragraph\">{content}</p>"
    label_paragraph = f"<p class=\"cell-paragraph\">{label_html}</p>" if label_html else ""
    return label_paragraph + render_cell_text(text, line_renderer=render_utterance)
