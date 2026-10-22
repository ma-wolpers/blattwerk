"""Darstellung der Klausurteile an ihren Trennern (`--hm`, später Wahlteile).

Die Semantik (wo welcher Teil beginnt, Deckblatt) liegt allein in
`exam_parts.resolve_exam_parts`; dieses Modul überträgt das Layout in
Block-Annotationen (`annotate_exam_parts`) und diese in HTML.

Regel „neue Seite“: `ExamPart.page_break` (Teil beginnt an einem Trenner und
ist der erste Teil oder folgt auf einen Teil mit Aufgaben). Ohne Deckblatt
steht Teil A am Dokumentanfang (synthetischer Block, kein Umbruch) und teilt
sich die Kopfzeile des Dokuments; der Pflichtteil hat keine Überschrift und
damit auch keinen synthetischen Block.

Wahlteile: Der erste Wahlteil eines Bereichs trägt den Hinweis „Bearbeite k
der n Wahlteile.“, jeder Wahlteil unter seiner Überschrift ein Ankreuzfeld.

Kopfzeile je Teil: Jeder Teil, der auf einer neuen Seite beginnt, bekommt
dieselbe Schülerkopfzeile wie der Dokumentanfang (`student_header`), damit
getrennt eingesammelte Teile (z. B. hilfsmittelfreier Teil A) Name und
Datum tragen. Ohne `show_student_header` ist die Kopfzeile leer, und es
ändert sich nichts.
"""

from __future__ import annotations

from html import escape

from .exam_parts import AID_PART_LABELS, AID_SPLIT_BLOCK, resolve_exam_parts  # noqa: F401 (AID_PART_LABELS: Re-Export)
from .exam_parts_invariants import PART_KIND_CHOICE

PART_ID_KEY = "_exam_part"
"""Block-Option: `part_id` des Teils, der an diesem (Pseudo-)Block beginnt."""
PART_HEADING_KEY = "_exam_part_heading"
"""Block-Option: Überschrift des Teils (`ExamPart.heading`)."""
PART_BREAK_KEY = "_exam_part_break"
"""Block-Option: Teil beginnt auf einer neuen Seite."""
PART_CHOICE_NOTE_KEY = "_exam_part_choice_note"
"""Block-Option: Hinweistext des Wahlbereichs (nur am ersten Wahlteil)."""
PART_CHOICE_CHECK_KEY = "_exam_part_choice_check"
"""Block-Option: Wahlteil bekommt ein Ankreuzfeld."""
CHOICE_CHECK_TEXT = "Diesen Wahlteil bearbeite ich."
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
    groups = {group.group_id: group for group in layout.groups}
    for part in layout.parts:
        marks = {PART_ID_KEY: part.part_id, PART_HEADING_KEY: part.heading, PART_BREAK_KEY: part.page_break}
        if part.kind == PART_KIND_CHOICE:
            group = groups[part.group_id]
            marks[PART_CHOICE_CHECK_KEY] = True
            if group.part_ids[0] == part.part_id:
                marks[PART_CHOICE_NOTE_KEY] = f"Bearbeite {group.k} der {len(group.part_ids)} Wahlteile."
        if part.marker_block is None:
            if part.heading:
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
    html = ""
    if opts.get(PART_CHOICE_NOTE_KEY):
        html += f"<p class='exam-choice-note'>{escape(str(opts[PART_CHOICE_NOTE_KEY]))}</p>"
    html += f"<h2 class='aid-part'>{escape(str(opts.get(PART_HEADING_KEY) or ''))}</h2>"
    if opts.get(PART_CHOICE_CHECK_KEY):
        html += f"<p class='exam-choice-check'><span class='exam-choice-box' aria-hidden='true'>☐</span> {CHOICE_CHECK_TEXT}</p>"
    if part_starts_new_page(opts):
        return _PAGEBREAK_HTML + str(opts.get(PART_HEADER_HTML_KEY) or "") + html
    return html
