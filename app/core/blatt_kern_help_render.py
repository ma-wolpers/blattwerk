"""Help-card extraction and HTML rendering."""

from __future__ import annotations
from .document_font import resolve_document_font_profile

from html import escape

from ..styles.blatt_styles import build_stylesheet
from .blatt_kern_shared import (
    HELP_BLOCK_TYPES,
    _new_markdown_converter,
    _help_labels_for_tag,
    _normalize_help_tag,
    _resolve_help_level,
    convert_markdown_with_math,
    is_hole_punch_layout_enabled,
    should_render_block,
)

HELP_CARD_WIDTH_CM = 10.5
"""Äußere CSS-Box-Breite einer Lernhilfenkarte in Zentimetern, inklusive
`padding`/`border` (nicht zusätzlich zu ihnen). Entspricht bewusst der
DIN-A6-Breite (`PAGE_LAYOUTS["a6_portrait"]` in `app/styles/blatt_styles.py`),
damit Einzelkarten-Export und Zweispalten-Mehrkarten-PDF (zwei Karten pro
DIN-A4-Breite nebeneinander) dieselbe physische Kartenbreite verwenden.
`.help-card` trägt bewusst keinen horizontalen Margin -- Abstände zwischen
Karten im Zweispalten-Layout werden ausschließlich über den Spalten-Container
gesteuert (siehe `.help-cards-columns`), nicht über Card-Margin."""

HELP_CARD_LAYOUT_SHEET = "sheet"
"""Kartenlayout „Sammelseite“: Karten fließen in A6-Breite (bei mindestens zwei
Karten zweispaltig) über die Seiten des gewählten Formats."""

HELP_CARD_LAYOUT_SINGLE = "single"
"""Kartenlayout „Einzelseiten“: jede Karte beginnt auf einer neuen Seite und
füllt randlos die volle Seitenbreite; am Kartenanfang steht ein unsichtbarer
Marker (`help_card_marker`), über den `help_card_pages` die Seitenspanne
jeder Karte im gedruckten PDF wiederfindet."""

HELP_CARD_LAYOUTS = (HELP_CARD_LAYOUT_SHEET, HELP_CARD_LAYOUT_SINGLE)

HELP_CARD_MARKER_PREFIX = "BWHC-"
"""Präfix des unsichtbaren Seitenmarkers im Einzelseiten-Layout; vier Ziffern
Kartennummer folgen (`BWHC-0001`). Wird nach dem Druck aus dem PDF entfernt."""


def help_card_marker(index):
    """Markertext der Karte mit der 1-basierten Dokumentnummer `index`.

    Beispiel: ``help_card_marker(3) == "BWHC-0003"``. Einzige Stelle, die das
    Markerformat festlegt -- Renderer und PDF-Auswertung nutzen beide diese
    Funktion.
    """
    return f"{HELP_CARD_MARKER_PREFIX}{int(index):04d}"


def collect_help_blocks(blocks, include_solutions=False, document_type="worksheet"):
    """Extrahiert sichtbare Hilfeblöcke inkl. Metadaten in Dokumentreihenfolge."""

    collected = []
    for block_type, options, content in blocks:
        if block_type not in HELP_BLOCK_TYPES:
            continue
        if not should_render_block(
            block_type,
            options,
            include_solutions,
            document_type=document_type,
        ):
            continue

        collected.append(
            {
                "block_type": block_type,
                "options": dict(options),
                "content": (content or "").strip(),
                "level": _resolve_help_level(options),
            }
        )

    return collected


def collect_labeled_help_blocks(
    meta,
    blocks,
    include_solutions=False,
    document_type="worksheet",
):
    """Extract visible help blocks and attach deterministic visible labels."""

    help_blocks = collect_help_blocks(
        blocks,
        include_solutions=include_solutions,
        document_type=document_type,
    )
    if not help_blocks:
        return []

    return _annotate_help_block_labels(help_blocks, (meta or {}).get("tag"))


def _annotate_help_block_labels(help_blocks, help_tag):
    """Assigns deterministic visible labels to help cards based on global/local tags."""

    normalized_help_tag = _normalize_help_tag(help_tag)
    auto_tag_entries = [block for block in help_blocks if not _normalize_help_tag(block["options"].get("tag"))]
    auto_labels = _help_labels_for_tag(len(auto_tag_entries), normalized_help_tag)
    auto_label_index = 0

    annotated_blocks = []
    for block in help_blocks:
        block_options = block["options"]
        local_tag = _normalize_help_tag(block_options.get("tag"))
        if local_tag:
            help_label = local_tag
        else:
            help_label = (
                auto_labels[auto_label_index]
                if auto_label_index < len(auto_labels)
                else None
            )
            auto_label_index += 1

        annotated_block = dict(block)
        annotated_block["label"] = help_label
        annotated_blocks.append(annotated_block)

    return annotated_blocks


def _wrap_cards_for_layout(cards_html, page_format, layout=HELP_CARD_LAYOUT_SHEET):
    """Wraps rendered cards in the container that carries the layout's CSS rules.

    Sammelseite: Multicol-Container für das Zweispalten-Layout, nur bei
    mindestens zwei Karten und einem physischen Seitenformat, das breiter ist
    als eine einzelne DIN-A6-Karte (`page_format` ungleich `"a6_portrait"`).
    `column-width: {HELP_CARD_WIDTH_CM}cm` sorgt dafür, dass der Browser die
    linke Spalte zuerst vollständig füllt, bevor die rechte beginnt
    (Standard-CSS-Fragmentierungsverhalten für paginierte Medien), ohne dass
    serverseitig Karten vorab auf Spalten verteilt werden müssten (Kartenhöhen
    sind variabel und erst durch den Renderer bekannt).

    Einzelseiten: immer der Container `.help-cards-single`, an dem die
    Seitenumbruch- und Vollbreite-Regeln aus `_help_cards_css` hängen.
    """
    joined = "".join(cards_html)
    if layout == HELP_CARD_LAYOUT_SINGLE:
        return f'<div class="help-cards-single">{joined}</div>'
    if len(cards_html) <= 1 or page_format == "a6_portrait":
        return joined
    return f'<div class="help-cards-columns">{joined}</div>'


def _render_help_card_section(index, block, layout):
    """Rendert eine einzelne Lernhilfenkarte als `<section class="help-card">`.

    Args:
        index: 1-basierte Kartennummer in Dokumentreihenfolge (über *alle*
            sichtbaren Karten, auch wenn nur eine Teilmenge gerendert wird);
            landet in `data-help-index` und im Einzelseiten-Marker.
        block: gelabelter Hilfeblock aus `collect_labeled_help_blocks`.
        layout: `HELP_CARD_LAYOUT_SHEET` oder `HELP_CARD_LAYOUT_SINGLE`; nur das
            Einzelseiten-Layout setzt den unsichtbaren Seitenmarker.
    """
    block_content = block["content"]
    level = block["level"]

    markdown_converter = _new_markdown_converter()
    body_html = (
        convert_markdown_with_math(markdown_converter, block_content)
        if block_content
        else ""
    )

    title_text = (block["options"].get("title") or "Hilfe").strip() or "Hilfe"
    label_text = (block.get("label") or "").strip()
    header_title = f"{label_text} - {title_text}" if label_text else title_text
    level_badge = (
        f"<span class='help-card-level'>Stufe {level}</span>"
        if level is not None
        else ""
    )
    marker_html = (
        f'<span class="help-card-marker">{help_card_marker(index)}</span>'
        if layout == HELP_CARD_LAYOUT_SINGLE
        else ""
    )

    return f"""
<section class="help-card" data-help-index="{index}">
{marker_html}<header class="help-card-header">
<h2>{escape(header_title)}</h2>
{level_badge}
</header>
<div class="help-card-body">{body_html}</div>
</section>
""".strip()


def _help_cards_css():
    """Karten-CSS für beide Layouts (Sammelseite und Einzelseiten).

    Das Einzelseiten-Layout (`.help-cards-single`) setzt die Karte randlos auf
    volle Seitenbreite -- auf DIN A6 ist das genau `HELP_CARD_WIDTH_CM`, auf
    A5/A4 entsprechend breiter -- und erzwingt vor jeder weiteren Karte einen
    Seitenumbruch. `break-inside: auto` ist dort Absicht: eine zu lange Karte
    soll sichtbar über die Seite laufen, damit `help_card_pages` sie erkennt
    und ins nächstgrößere Format verschiebt. Der Marker sitzt absolut im
    oberen Kartenpolster, damit er beim späteren Entfernen keinen Nachbartext
    berührt.
    """
    return f"""
body {{
    margin: 0;
}}

@page {{
    margin: 0;
}}

.help-cards-columns {{
    column-width: {HELP_CARD_WIDTH_CM}cm;
    column-fill: auto;
    column-gap: 0;
}}

.help-card {{
    box-sizing: border-box;
    width: {HELP_CARD_WIDTH_CM}cm;
    border: var(--material-border-width) solid var(--material-border-color);
    border-radius: 10px;
    padding: 0.65cm 0.7cm;
    margin: 0 0 0.45cm 0;
    break-inside: avoid;
    page-break-inside: avoid;
    -webkit-column-break-inside: avoid;
}}
""" + """
.help-card:last-child {
    margin-bottom: 0;
}

.help-cards-single .help-card {
    position: relative;
    width: 100%;
    margin: 0;
    break-before: page;
    break-inside: auto;
    page-break-inside: auto;
}

.help-cards-single .help-card:first-child {
    break-before: auto;
}

.help-card-marker {
    position: absolute;
    top: 1px;
    left: 1px;
    font-size: 2px;
    line-height: 2px;
    color: #fff;
}

.help-card-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.6em;
    margin: 0 0 0.4em 0;
}

.help-card-header h2 {
    margin: 0;
    font-size: 1.18em;
}

.help-card-level {
    color: var(--task-hint-color);
    border: 1px solid var(--material-border-color);
    border-radius: 999px;
    padding: 0.04em 0.55em;
    font-size: 0.9em;
    white-space: nowrap;
}

.help-card-body > *:first-child {
    margin-top: 0;
}

.help-card-body > *:last-child {
    margin-bottom: 0;
}
""".strip()


def render_help_cards_html(
    meta,
    blocks,
    include_solutions=False,
    page_format="a4_portrait",
    print_profile="standard",
    color_profile="indigo",
    font_profile="segoe",
    font_size_profile="normal",
    layout=HELP_CARD_LAYOUT_SHEET,
    card_indices=None,
):
    """Rendert ausschließlich Hilfeblöcke als kartenseitige HTML-Ausgabe.

    `font_profile` ist der App-Standard; ein gültiges `font_profile` im Frontmatter
    hat Vorrang (`resolve_document_font_profile`).

    Args:
        layout: `HELP_CARD_LAYOUT_SHEET` (Standard, fließende Sammelseite) oder
            `HELP_CARD_LAYOUT_SINGLE` (je Karte eine Seite, siehe `_help_cards_css`).
        card_indices: optional die 1-basierten Kartennummern, die gerendert
            werden sollen (`None` = alle). Labels und Nummern werden trotzdem
            über *alle* sichtbaren Karten vergeben, damit eine Teilmenge (z. B.
            die Karten, die erst auf DIN A5 passen) dieselben Labels trägt wie
            im vollständigen Satz.

    Returns:
        Vollständiges HTML-Dokument oder `""`, wenn keine (ausgewählte) Karte
        sichtbar ist.
    """
    if layout not in HELP_CARD_LAYOUTS:
        raise ValueError(f"Unbekanntes Lernhilfen-Layout: {layout!r}")
    font_profile, _ = resolve_document_font_profile(meta, font_profile)

    help_blocks = collect_labeled_help_blocks(
        meta,
        blocks,
        include_solutions=include_solutions,
        document_type="worksheet",
    )
    selected = [
        (index, block)
        for index, block in enumerate(help_blocks, start=1)
        if card_indices is None or index in card_indices
    ]
    if not selected:
        return ""

    stylesheet = build_stylesheet(
        page_format,
        print_profile,
        hole_punch_enabled=is_hole_punch_layout_enabled(meta),
        color_profile=color_profile,
        font_profile=font_profile,
        font_size_profile=font_size_profile,
    )
    cards_html = [_render_help_card_section(index, block, layout) for index, block in selected]

    title_value = escape((meta or {}).get("Titel", "Hilfekarten"))
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{title_value} – Hilfekarten</title>
<script>
window.MathJax = {{
    tex: {{
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true,
    }},
    svg: {{
        fontCache: 'none'
    }}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" onerror="document.body.classList.add('mathjax-load-failed')"></script>
<style>
{stylesheet}

{_help_cards_css()}
</style>
</head>
<body>
{_wrap_cards_for_layout(cards_html, page_format, layout)}
</body>
</html>
"""
