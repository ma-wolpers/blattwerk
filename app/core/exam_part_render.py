"""Darstellung der Klausurteile an ihren Trennern (`--hm`, später Wahlteile).

Die Semantik (wo welcher Teil beginnt, Deckblatt) liegt allein in
`exam_parts.resolve_exam_parts`; dieses Modul überträgt das Layout in
Block-Annotationen (`annotate_exam_parts`) und diese in HTML.

Regel „neue Seite“: Ein Teil beginnt genau dann auf einer neuen Seite, wenn
er an einem Trenner beginnt (`ExamPart.marker_block`). Ohne Deckblatt steht
Teil A am Dokumentanfang (synthetischer Block, kein Umbruch) und teilt sich
die Kopfzeile des Dokuments.

Kopfzeile je Teil: Jeder Teil, der auf einer neuen Seite beginnt, bekommt
dieselbe Schülerkopfzeile wie der Dokumentanfang (`student_header`), damit
getrennt eingesammelte Teile (z. B. hilfsmittelfreier Teil A) Name und
Datum tragen. Ohne `show_student_header` ist die Kopfzeile leer, und es
ändert sich nichts.
"""

from __future__ import annotations

from html import escape

from .exam_parts import AID_PART_LABELS, AID_SPLIT_BLOCK, resolve_exam_parts  # noqa: F401 (AID_PART_LABELS: Re-Export)

PART_ID_KEY = "_exam_part"
"""Block-Option: `part_id` des Teils, der an diesem (Pseudo-)Block beginnt."""
PART_HEADING_KEY = "_exam_part_heading"
"""Block-Option: Überschrift des Teils (`ExamPart.heading`)."""
PART_BREAK_KEY = "_exam_part_break"
"""Block-Option: Teil beginnt auf einer neuen Seite."""
PART_HEADER_HTML_KEY = "_exam_part_header_html"
"""Block-Option mit dem fertigen Kopfzeilen-HTML; gesetzt nur von `attach_part_headers`."""

_PAGEBREAK_HTML = "<div class='ab-pagebreak' aria-hidden='true'></div>"


def annotate_exam_parts(blocks, document_type: str | None):
    """Markiert für das Rendern den Beginn jedes Teils.

    Ein Teil mit Trenner bekommt die Marken an diesem Block; der erste Teil
    ohne Trenner (Teil A ohne Deckblatt) einen synthetischen Block am
    Dokumentanfang -- danach sind die Blockindizes um eins verschoben, daher
    laufen indexbasierte Annotationen vorher. Ohne gültiges Layout bleibt die
    Blockliste unverändert (dann rendert ein Trenner nichts).
    """
    layout = resolve_exam_parts(blocks, document_type).layout
    if layout is None:
        return blocks
    annotated = list(blocks)
    prefix = []
    for part in layout.parts:
        marks = {PART_ID_KEY: part.part_id, PART_HEADING_KEY: part.heading, PART_BREAK_KEY: part.marker_block is not None}
        if part.marker_block is None:
            prefix.append((AID_SPLIT_BLOCK, marks, ""))
            continue
        block_type, options, content = annotated[part.marker_block]
        annotated[part.marker_block] = (block_type, {**options, **marks}, content)
    return prefix + annotated


def part_starts_new_page(options) -> bool:
    """Ob der an diesem Block beginnende Teil auf einer neuen Seite beginnt."""
    return bool((options or {}).get(PART_BREAK_KEY))


def attach_part_headers(blocks, header_html: str):
    """Hängt die Schülerkopfzeile an jeden Teil, der auf einer neuen Seite beginnt.

    Args:
        blocks: Blockliste nach `annotate_exam_parts`.
        header_html: Ergebnis von `student_header.render_student_header(meta)`;
            leer, wenn die Kopfzeile abgeschaltet ist.

    Returns:
        Die Blockliste; unverändert, wenn `header_html` leer ist oder es keine
        gültigen Teile gibt.
    """
    if not header_html:
        return blocks
    result = []
    for block_type, options, content in blocks:
        if PART_ID_KEY in (options or {}) and part_starts_new_page(options):
            options = {**options, PART_HEADER_HTML_KEY: header_html}
        result.append((block_type, options, content))
    return result


def render_exam_part(options) -> str:
    """Teilüberschrift am Trenner (nur mit Annotation aus `annotate_exam_parts`).

    Ohne Annotation (`.abw`, `.pbw` oder ungültige Struktur) rendert der
    Trenner nichts. Ein Teil auf neuer Seite gibt in dieser Reihenfolge aus:
    Umbruch (vorhandenes Pagebreak-Element, damit Vorschau, HTML, PDF und PNG
    dieselbe Umbruchsemantik haben), ggf. die Schülerkopfzeile, Überschrift.
    """
    opts = options or {}
    if PART_ID_KEY not in opts:
        return ""
    heading = f"<h2 class='aid-part'>{escape(str(opts.get(PART_HEADING_KEY) or ''))}</h2>"
    if part_starts_new_page(opts):
        return _PAGEBREAK_HTML + str(opts.get(PART_HEADER_HTML_KEY) or "") + heading
    return heading
