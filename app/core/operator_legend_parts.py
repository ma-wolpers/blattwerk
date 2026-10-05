"""Operatorenliste je Teil und Messmarken für die Platzierung am Seitenende.

Fachliche Regel (Produktentscheidung):

* Ohne gültigen Hilfsmittel-Trenner gibt es eine Liste aus allen verwendeten
  Operatoren am Dokumentende.
* Mit gültigem Split (ein oder zwei `--hm`, siehe `resolve_aid_split`) gibt es je
  Teil eine eigene Liste: Liste A (Teil A inklusive Deckblatt) am Ende von Teil A,
  Liste B am Dokumentende.
* Ein Teil ohne Operatoren bekommt keine Liste (und keinen Wrapper).
* In der Lösungsfassung gibt es keine Liste.

Renderrepräsentation von „Ende Teil A“: Liste A wird als ``PART_END_HTML_KEY`` an
den A/B-Trenner gehängt; `_render_aid_part` gibt sie **vor** dem Seitenumbruch
aus. Der Key bedeutet ausschließlich „Inhalt, der ans Ende des vorangehenden
Teils gehört“ und wird nur von diesem Modul gesetzt (Guard-Test).

Jede gerenderte Liste steckt in einem Wrapper mit eindeutiger ID und zwei
unsichtbaren Messmarken (Link-Elemente), über die `operator_legend_placement`
die Liste im fertigen PDF findet und ans Seitenende schiebt.
"""

from __future__ import annotations

from .document_semantics import resolve_aid_split
from .operator_legend import collect_used_operators, render_operator_legend_html

PART_END_HTML_KEY = "_part_end_html"
LEGEND_PROBE_URI_PREFIX = "https://blattwerk.invalid/legend/"
LEGEND_ELEMENT_ID_PREFIX = "operator-legend-"


def legend_probe_uri(legend_index: int, edge: str) -> str:
    """URI der Messmarke ``edge`` (``"top"``/``"bottom"``) der Liste ``legend_index``."""
    return f"{LEGEND_PROBE_URI_PREFIX}{legend_index}/{edge}"


def wrap_legend_html(table_html: str, legend_index: int) -> str:
    """Hüllt eine gerenderte Legendentabelle in Wrapper plus Messmarken.

    Die Messmarken sind 1 px hohe, unsichtbare Block-Links (für Screenreader und
    Tastatur ausgeblendet). Der Wrapper trägt die ID, über die die Platzierung
    ein ``padding-top`` setzt -- der bestehende ``margin-top`` der Tabelle bleibt
    unberührt (Padding kollabiert nicht mit dem Abstand davor).
    """
    probe = "<a class='operator-legend-probe' href='{uri}' aria-hidden='true' tabindex='-1'></a>"
    return (
        f"<div class='operator-legend-block' id='{LEGEND_ELEMENT_ID_PREFIX}{legend_index}'>"
        f"{probe.format(uri=legend_probe_uri(legend_index, 'top'))}"
        f"{table_html}"
        f"{probe.format(uri=legend_probe_uri(legend_index, 'bottom'))}"
        "</div>"
    )


def _legend_for(blocks, meta, legend_index: int) -> str:
    matched, _diagnostics = collect_used_operators(blocks, meta)
    if not matched:
        return ""
    return wrap_legend_html(render_operator_legend_html(matched), legend_index)


def build_part_legends(blocks, meta, document_type, *, include_solutions: bool):
    """Verteilt die Operatorenlisten auf die Teile.

    Args:
        blocks: Blockliste **vor** `annotate_aid_parts` (Indizes wie in
            `resolve_aid_split`).
        meta: Frontmatter (Fach/Stufe für die Operatorenliste).
        document_type: Dokumenttyp (Split nur in Klausuren).
        include_solutions: In der Lösungsfassung gibt es keine Liste.

    Returns:
        ``(blocks, end_html)``: Blockliste, bei Split mit ``PART_END_HTML_KEY``
        am A/B-Trenner, und das HTML der Liste am Dokumentende ("" ohne Liste).
    """
    if include_solutions:
        return blocks, ""
    split = resolve_aid_split(blocks, document_type)
    if split is None:
        return blocks, _legend_for(blocks, meta, 0)

    legend_a = _legend_for(blocks[: split.index], meta, 0)
    legend_b = _legend_for(blocks[split.index :], meta, 1 if legend_a else 0)
    if not legend_a:
        return blocks, legend_b
    annotated = list(blocks)
    block_type, options, content = annotated[split.index]
    annotated[split.index] = (block_type, {**options, PART_END_HTML_KEY: legend_a}, content)
    return annotated, legend_b
