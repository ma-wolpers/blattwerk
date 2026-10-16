"""Darstellung der Klausurteile am Hilfsmittel-Trenner `--hm` (Teil A/B).

Einzige Quelle der Teilbezeichnungen (`AID_PART_LABELS`). Die Semantik
des Trenners (wo Teil A/B beginnt, Deckblatt) liegt in
`document_semantics.resolve_aid_split`/`annotate_aid_parts`; dieses Modul
übersetzt nur deren Annotationen in HTML.
"""

from __future__ import annotations


AID_PART_LABELS = {"A": "Teil A – hilfsmittelfrei", "B": "Teil B – mit Hilfsmitteln"}


def render_aid_part(options) -> str:
    """Teilüberschrift am Hilfsmittel-Trenner (nur mit Annotation aus `resolve_aid_split`).

    Ohne Annotation (`.abw`, `.pbw` oder ungültiger Split) rendert `--hm` nichts.
    Teil B -- und mit Deckblatt auch Teil A (`_aid_break`) -- beginnt mit dem
    vorhandenen Pagebreak-Element, damit Vorschau, HTML, PDF und PNG dieselbe
    Umbruchsemantik haben.
    """
    part = (options or {}).get("_aid_part")
    if part not in AID_PART_LABELS:
        return ""
    heading = f"<h2 class='aid-part'>{AID_PART_LABELS[part]}</h2>"
    if part == "B" or (options or {}).get("_aid_break"):
        return "<div class='ab-pagebreak' aria-hidden='true'></div>" + heading
    return heading
