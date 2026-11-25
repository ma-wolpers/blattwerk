"""Kurzentwurf: Zelleninhalt (Text mit Absätzen, Listen, Leerzeilen) als HTML.

Einziger Renderpfad für den Text jeder Tabellenzelle (Vorschau und PDF
nutzen dasselbe HTML). Konvention wie im Arbeitsblatt:

- einfacher Zeilenumbruch = `<br>` im selben Absatz,
- `- `/`* `/`• `/`1.`/`a)` am Zeilenanfang = Listenpunkt,
- Leerzeile = neuer Absatz **mit sichtbarer Leerzeile** davor: der folgende
  Block trägt die Klasse `cell-gap` (Abstand einer Zeile, CSS in
  `render_html`). Ein Listenwechsel ohne Leerzeile setzt nur den kleinen
  Blockabstand.

Reine Kommentarzeilen (`%%...%%`) zählen gar nicht. Wie die Inline-Inhalte
einer Zeile dargestellt werden, lässt sich per `line_renderer` ersetzen --
z. B. setzt `activity_cell.render_utterance` Antizipationen in
Anführungszeichen.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from ..inline_markup import render_inline_markup
from ..inline_markup.spans import drop_comment_only_lines
from .cell_text import strip_hard_break

_ORDERED_DIGIT_RE = re.compile(r"^\d+[.)]\s+(.+)$")
_ORDERED_ALPHA_RE = re.compile(r"^([a-zA-Z])[.)]\s+(.+)$")

CELL_GAP_CLASS = "cell-gap"
"""CSS-Klasse für einen Block, vor dem in der Quelle eine Leerzeile stand."""


def render_inline_line(line: str) -> str:
    """Standard-Darstellung einer Zeile: harter Umbruch weg, Inline-Markup gerendert.

    Escaping (inkl. `&`/`<`/`>`) übernimmt das zentrale `inline_markup`-Paket
    pro Run; hier darf NICHT zusätzlich vorab escaped werden.
    """
    return render_inline_markup(strip_hard_break(line))


def render_cell_text(text: str, line_renderer: Callable[[str], str] | None = None) -> str:
    """Rendert einen Zellentext zu `<p>`/`<ul>`/`<ol>`-Blöcken.

    `line_renderer` bekommt jede Absatzzeile bzw. jeden Listenpunkt (ohne
    Aufzählungszeichen) und liefert dessen HTML; Standard ist
    `render_inline_line`. Leere Zeilen nach `strip_hard_break` entfallen.
    """
    render_line = line_renderer or render_inline_line
    normalized = drop_comment_only_lines(str(text or "").replace("\r\n", "\n").replace("\r", "\n"))

    blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    list_ordered_type: str | None = None  # None=unordered, '1'/'a'/'A'=ordered
    gap_before = False

    def append_block(tag: str, base_class: str, inner_html: str, extra_attrs: str = "") -> None:
        nonlocal gap_before
        classes = f"{base_class} {CELL_GAP_CLASS}" if gap_before else base_class
        blocks.append(f"<{tag}{extra_attrs} class=\"{classes}\">{inner_html}</{tag}>")
        gap_before = False

    def flush_paragraph() -> None:
        rendered = [render_line(line) for line in paragraph_lines if strip_hard_break(line)]
        if rendered:
            append_block("p", "cell-paragraph", "<br>".join(rendered))
        paragraph_lines.clear()

    def flush_list() -> None:
        items_html = "".join(f"<li>{render_line(item)}</li>" for item in list_items if strip_hard_break(item))
        if items_html:
            if list_ordered_type is None:
                append_block("ul", "cell-list", items_html)
            else:
                type_attr = f" type=\"{list_ordered_type}\"" if list_ordered_type != "1" else ""
                append_block("ol", "cell-list", items_html, type_attr)
        list_items.clear()

    for raw_line in normalized.split("\n"):
        stripped = raw_line.strip()

        extracted = extract_bullet_text(stripped)
        if extracted is not None:
            item_text, ordered_type = extracted
            flush_paragraph()
            if list_items and list_ordered_type != ordered_type:
                flush_list()
            list_ordered_type = ordered_type
            list_items.append(item_text)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            gap_before = bool(blocks)
            continue

        flush_list()
        paragraph_lines.append(stripped)

    flush_paragraph()
    flush_list()
    return "".join(blocks)


def extract_bullet_text(line: str) -> tuple[str, str | None] | None:
    """Returns (text, ordered_type) or None.

    ordered_type is None for bullet lists, '1' for digit-ordered,
    'a'/'A' for lower-/upper-alpha ordered lists.
    """
    if not line:
        return None

    for marker in ("- ", "* ", "• "):
        if line.startswith(marker):
            return line[len(marker):].strip(), None

    digit_match = _ORDERED_DIGIT_RE.match(line)
    if digit_match:
        return digit_match.group(1).strip(), "1"

    alpha_match = _ORDERED_ALPHA_RE.match(line)
    if alpha_match:
        ordered_type = "a" if alpha_match.group(1).islower() else "A"
        return alpha_match.group(2).strip(), ordered_type

    return None
