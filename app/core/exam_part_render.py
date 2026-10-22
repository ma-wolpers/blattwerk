"""Darstellung der Klausurteile am Hilfsmittel-Trenner `--hm` (Teil A/B).

Einzige Quelle der Teilbezeichnungen (`AID_PART_LABELS`) und der Regel,
welcher Teil auf einer neuen Seite beginnt (`part_starts_new_page`). Die
Semantik des Trenners (wo Teil A/B beginnt, Deckblatt) liegt in
`document_semantics.resolve_aid_split`/`annotate_aid_parts`; dieses Modul
übersetzt nur deren Annotationen in HTML.

Kopfzeile je Teil: Jeder Teil, der auf einer neuen Seite beginnt, bekommt
dieselbe Schülerkopfzeile wie der Dokumentanfang (`student_header`), damit
getrennt eingesammelte Teile (z. B. hilfsmittelfreier Teil A) Name und
Datum tragen. Ohne `show_student_header` ist die Kopfzeile leer, und es
ändert sich nichts.
"""

from __future__ import annotations

from .document_semantics import AID_SPLIT_BLOCK

AID_PART_LABELS = {"A": "Teil A – hilfsmittelfrei", "B": "Teil B – mit Hilfsmitteln"}

PART_HEADER_HTML_KEY = "_aid_header_html"
"""Block-Option mit dem fertigen Kopfzeilen-HTML; gesetzt nur von `attach_part_headers`."""

_PAGEBREAK_HTML = "<div class='ab-pagebreak' aria-hidden='true'></div>"


def part_starts_new_page(options) -> bool:
    """Ob der annotierte Teil auf einer neuen Seite beginnt.

    Teil B beginnt immer mit einem Umbruch; Teil A nur mit Deckblatt
    (`_aid_break`, gesetzt von `annotate_aid_parts`). Ohne Deckblatt steht
    Teil A am Dokumentanfang und teilt sich die Kopfzeile des Dokuments.
    """
    opts = options or {}
    return opts.get("_aid_part") == "B" or bool(opts.get("_aid_break"))


def attach_part_headers(blocks, header_html: str):
    """Hängt die Schülerkopfzeile an jeden Teil, der auf einer neuen Seite beginnt.

    Args:
        blocks: Blockliste nach `annotate_aid_parts` (nur dort tragen
            `aidsplit`-Blöcke `_aid_part`).
        header_html: Ergebnis von `student_header.render_student_header(meta)`;
            leer, wenn die Kopfzeile abgeschaltet ist.

    Returns:
        Die Blockliste; unverändert, wenn `header_html` leer ist oder es keinen
        gültigen Split gibt.
    """
    if not header_html:
        return blocks
    result = []
    for block_type, options, content in blocks:
        if block_type == AID_SPLIT_BLOCK and (options or {}).get("_aid_part") in AID_PART_LABELS and part_starts_new_page(options):
            options = {**options, PART_HEADER_HTML_KEY: header_html}
        result.append((block_type, options, content))
    return result


def render_aid_part(options) -> str:
    """Teilüberschrift am Hilfsmittel-Trenner (nur mit Annotation aus `resolve_aid_split`).

    Ohne Annotation (`.abw`, `.pbw` oder ungültiger Split) rendert `--hm` nichts.
    Ein Teil, der auf einer neuen Seite beginnt (`part_starts_new_page`), gibt
    in dieser Reihenfolge aus: Umbruch (vorhandenes Pagebreak-Element, damit
    Vorschau, HTML, PDF und PNG dieselbe Umbruchsemantik haben), ggf. die
    Schülerkopfzeile (`attach_part_headers`), Überschrift.
    """
    part = (options or {}).get("_aid_part")
    if part not in AID_PART_LABELS:
        return ""
    heading = f"<h2 class='aid-part'>{AID_PART_LABELS[part]}</h2>"
    if part_starts_new_page(options):
        return _PAGEBREAK_HTML + str(options.get(PART_HEADER_HTML_KEY) or "") + heading
    return heading
