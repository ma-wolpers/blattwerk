"""Markiert jedes Emoji im fertigen HTML mit einer Klasse (`EMOJI_GLYPH_CLASS`).

Einziger Weg, auf dem Emojis eine Darstellung bekommen: Die Renderer bleiben
emoji-blind, `mark_emoji_glyphs` läuft einmal über das fertige Dokument
(`render_html`, `render_help_cards_html`), und genau eine CSS-Regel in
`app/styles/worksheet_design.py` gestaltet die Klasse je Farbprofil (im S/W-Profil
die Outline-Darstellung). So sehen Emojis im Fließtext, in Überschriften, Tabellen,
Selfcheck-Skalen und die Aufgabensymbole gleich aus.

Welche Teile der Seite Text sind (nicht vor `<body>`, keine Tags, Kommentare,
`<script>`/`<style>`/`<svg>`/`<textarea>`/`<title>`-Inhalte, keine Formeln), entscheidet
der gemeinsame Durchlauf `document_text_pass.map_body_text`; hier steht nur, was mit
einem Stück Text passiert. Bereits markierte Emojis schützt `_ALREADY_MARKED`
(Idempotenz).
"""

from __future__ import annotations

import re
import unicodedata

from .emoji_data import (
    BMP_EMOJI_PRESENTATION_RANGES,
    CLUSTER_EXTENDERS,
    EMOJI_PRESENTATION_SELECTOR,
    REGIONAL_INDICATOR_RANGE,
    SMP_PICTOGRAPHIC_RANGE,
    TEXT_PRESENTATION_SELECTOR,
    ZERO_WIDTH_JOINER,
)
from .document_text_pass import map_body_text
from ..styles.worksheet_design import EMOJI_GLYPH_CLASS

_OPEN_TAG = f'<span class="{EMOJI_GLYPH_CLASS}">'
_CLOSE_TAG = "</span>"

_CANDIDATE_RE = re.compile("[⌚-⭕️\U0001F000-\U0001FAFF]")
"""Schneller Vorfilter: Ohne eines dieser Zeichen enthält ein Text kein Emoji."""

_ALREADY_MARKED = re.escape(_OPEN_TAG) + r".*?" + re.escape(_CLOSE_TAG)
"""Schon markierte Emojis bleiben unverändert (Idempotenz)."""


def _in_range(code_point: int, bounds: tuple[int, int]) -> bool:
    """Ob `code_point` im geschlossenen Intervall `bounds` liegt."""
    return bounds[0] <= code_point <= bounds[1]


def _has_emoji_presentation(char: str) -> bool:
    """Ob `char` ohne Variation Selector als buntes Emoji erscheint (Tabellen in `emoji_data`)."""
    code_point = ord(char)
    if _in_range(code_point, SMP_PICTOGRAPHIC_RANGE):
        return True
    return any(_in_range(code_point, bounds) for bounds in BMP_EMOJI_PRESENTATION_RANGES)


def is_emoji_cluster_start(text: str, index: int) -> bool:
    """Ob an `text[index]` ein Emoji-Cluster beginnt.

    Ein Cluster beginnt mit einem Zeichen, das von sich aus bunt erscheint
    (`Emoji_Presentation`), oder mit einem beliebigen Zeichen, auf das U+FE0F folgt
    (↔️, ⚖️, ✍️). Folgt U+FE0E (Textdarstellung), ist es kein Emoji.

    Example:
        >>> is_emoji_cluster_start("✅", 0), is_emoji_cluster_start("☐", 0)
        (True, False)
        >>> is_emoji_cluster_start("↔️", 0)
        True
    """
    following = text[index + 1] if index + 1 < len(text) else ""
    if following == TEXT_PRESENTATION_SELECTOR:
        return False
    return following == EMOJI_PRESENTATION_SELECTOR or _has_emoji_presentation(text[index])


def _cluster_end(text: str, index: int) -> int:
    """Index direkt hinter dem Emoji-Cluster, das bei `index` beginnt.

    Nimmt Erweiterungen (`CLUSTER_EXTENDERS`: U+FE0F, Hauttöne, Keycap, Tags), das
    Zeichen nach jedem ZWJ und den zweiten Regionalindikator einer Flagge mit.
    """
    end = index + 1
    if _in_range(ord(text[index]), REGIONAL_INDICATOR_RANGE) and end < len(text):
        if _in_range(ord(text[end]), REGIONAL_INDICATOR_RANGE):
            end += 1
    while end < len(text):
        char = text[end]
        if char == ZERO_WIDTH_JOINER and end + 1 < len(text):
            end += 2
        elif unicodedata.category(char) in CLUSTER_EXTENDERS:
            end += 1
        else:
            break
    return end


def _mark_plain_text(text: str) -> str:
    """Umschließt jedes Emoji-Cluster in reinem Text (ohne Formeln) mit dem Klassen-Span."""
    if not _CANDIDATE_RE.search(text):
        return text
    parts: list[str] = []
    index = 0
    plain_start = 0
    while index < len(text):
        if is_emoji_cluster_start(text, index):
            end = _cluster_end(text, index)
            parts.append(text[plain_start:index])
            parts.append(f"{_OPEN_TAG}{text[index:end]}{_CLOSE_TAG}")
            index = plain_start = end
        else:
            index += 1
    parts.append(text[plain_start:])
    return "".join(parts)


def mark_emoji_glyphs(html: str) -> str:
    """Umschließt jedes Emoji im Body von `html` mit `<span class="emoji-glyph">`.

    Bei einem vollständigen Dokument wird nur der Teil ab `<body>` bearbeitet, bei
    einem Fragment ohne `<body>` alles. Mehrfacher Aufruf ändert nichts mehr
    (idempotent).

    Args:
        html: Vollständiges HTML-Dokument oder HTML-Fragment.

    Returns:
        Das HTML mit markierten Emojis; ohne Emoji-Kandidaten unverändert.

    Example:
        >>> mark_emoji_glyphs("<p title='💡'>Tipp 💡 und ☐</p>")
        '<p title=\\'💡\\'>Tipp <span class="emoji-glyph">💡</span> und ☐</p>'
        >>> mark_emoji_glyphs("$x$ 🍎")
        '$x$ <span class="emoji-glyph">🍎</span>'
    """
    if not html or not _CANDIDATE_RE.search(html):
        return html
    return map_body_text(html, _mark_plain_text, protected_pattern=_ALREADY_MARKED)
