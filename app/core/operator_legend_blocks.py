"""Operatorentabelle als expliziter Block `:::operators:::` plus Messmarken fürs Seitenende.

Produktentscheidung: Es gibt keine automatisch angehängte Operatorentabelle
mehr. Eine Tabelle entsteht nur dort, wo ein `operators`-Block steht; fehlt
sie für verwendete `!!Operatoren!!`, warnt der Validator
(`blatt_validator_operator_legend`, OPR004–OPR008).

Bereich eines Blocks (`scope=`):

* ``previous`` (Standard): alle Blöcke nach dem vorigen `operators`-Block (bzw.
  ab Dokumentanfang) bis zu diesem Block.
* ``all``: das ganze Dokument, auch Blöcke nach der Tabelle.
* ``part``: der Hilfsmittel-Teil (`--hm`, siehe `resolve_aid_split`), in dem der
  Block steht -- Deckblatt und Teil A gelten als ein Teil. Ohne gültigen Split
  ist das das ganze Dokument.

Bereiche dürfen sich überschneiden (Warnung OPR008). Eine Operator-Fundstelle
gilt als abgedeckt, sobald **mindestens ein** Block sie abdeckt -- es gibt keine
„letzter Block gewinnt“-Semantik. Die Tabelle listet die im Bereich gefundenen
Operatoren in der Reihenfolge des ersten Auftretens ohne Duplikate
(`operator_legend.collect_used_operators`).

Sichtbarkeit: Der Block ist standardmäßig nur in der Arbeitsblattfassung
sichtbar (blocktypspezifischer Standard in `should_render_block`), wie die
frühere automatische Tabelle; `mode=solution` zeigt ihn nur in der Lösung.

Jede gerenderte Tabelle steckt in einem Wrapper mit dokumentweit eindeutiger ID
und zwei unsichtbaren Messmarken (Link-Elemente), über die
`operator_legend_placement` die Tabelle im fertigen PDF findet: Steht sie unter
anderem Inhalt, rutscht sie ans Seitenende; steht sie als Erstes auf einer
Seite, bleibt sie oben.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from .document_semantics import resolve_aid_split
from .document_type_registry import shows_operator_legend
from .inline_markup import parse_inline_markup
from .operator_legend import collect_used_operators, render_operator_legend_html

OPERATORS_BLOCK_TYPE = "operators"
OPERATOR_LEGEND_HTML_KEY = "_operator_legend_html"
SCOPE_PREVIOUS = "previous"
SCOPE_ALL = "all"
SCOPE_PART = "part"
KNOWN_SCOPES = (SCOPE_PREVIOUS, SCOPE_ALL, SCOPE_PART)

LEGEND_PROBE_URI_PREFIX = "https://blattwerk.invalid/legend/"
LEGEND_ELEMENT_ID_PREFIX = "operator-legend-"


@dataclass(frozen=True)
class OperatorBlockCoverage:
    """Bereich eines `operators`-Blocks: welche Blockindizes er abdeckt."""

    block_index: int
    scope: str
    covered: tuple[int, ...]


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


SECTION_BREAK_MARKER = "<!--BLATTWERK_SECTION_BREAK-->"


def as_own_section(table_html: str) -> str:
    """Lässt mit der gerenderten Tabelle einen neuen Druckabschnitt beginnen (`split_sections`).

    Abschnitte (`.ab-section`) werden nicht umbrochen. Stünde die Tabelle im
    Abschnitt der Aufgabe davor, würde die Aufgabe mit auf die nächste Seite
    wandern, sobald beide zusammen nicht mehr passen. Mit dem Trenner davor
    wandert nur die Tabelle, und `operator_legend_placement` schiebt sie ans
    Seitenende oder lässt sie oben stehen.

    Bewusst **kein** Trenner danach: Folgt ein Umbruch (`--hm`, `--!`), muss er
    im selben Abschnitt wie die Tabelle bleiben. Begänne er einen eigenen
    Abschnitt, würde dieser nach dem Verschieben der Tabelle ans Seitenende als
    Ganzes auf die nächste Seite rutschen und dort erneut umbrechen -- eine
    Leerseite, die Pass 2 der Platzierung (zu Recht) verwirft. Gilt nur auf
    oberster Ebene, nie innerhalb von `:::columns` (der Aufrufer prüft das).
    """
    return f"{SECTION_BREAK_MARKER}{table_html}"


def resolve_scope(options: dict | None) -> str:
    """Normalisierter `scope=`-Wert; Unbekanntes fällt auf ``previous`` zurück (OP002 meldet es)."""
    raw = str((options or {}).get("scope") or "").strip().lower()
    return raw if raw in KNOWN_SCOPES else SCOPE_PREVIOUS


def operator_block_coverages(blocks, document_type: str) -> list[OperatorBlockCoverage]:
    """Berechnet für jeden `operators`-Block seinen Bereich (Blockindizes, ohne andere Tabellen).

    Args:
        blocks: Blockliste **vor** `annotate_aid_parts` (Indizes wie in
            `resolve_aid_split`).
        document_type: Dokumenttyp (Teile nur in Klausuren mit gültigem Split).
    """
    split = resolve_aid_split(blocks, document_type)
    every_index = tuple(range(len(blocks)))
    coverages = []
    previous_start = 0
    for index, (block_type, options, _content) in enumerate(blocks):
        if block_type != OPERATORS_BLOCK_TYPE:
            continue
        scope = resolve_scope(options)
        if scope == SCOPE_ALL:
            covered = every_index
        elif scope == SCOPE_PART and split is not None:
            covered = tuple(range(0, split.index)) if index < split.index else tuple(range(split.index, len(blocks)))
        elif scope == SCOPE_PART:
            covered = every_index
        else:
            covered = tuple(range(previous_start, index))
        previous_start = index + 1
        coverages.append(OperatorBlockCoverage(index, scope, _without_tables(blocks, covered)))
    return coverages


def _without_tables(blocks, indices) -> tuple[int, ...]:
    """Entfernt `operators`-Blöcke selbst aus einem Bereich (ihr Inhalt zählt nie)."""
    return tuple(index for index in indices if blocks[index][0] != OPERATORS_BLOCK_TYPE)


def operator_marker_indices(blocks) -> list[int]:
    """Indizes aller Blöcke mit mindestens einem `!!...!!`-Operator-Marker (ohne Tabellen-Blöcke)."""
    result = []
    for index, (block_type, _options, content) in enumerate(blocks):
        if block_type == OPERATORS_BLOCK_TYPE or not content:
            continue
        runs, _issues = parse_inline_markup(content)
        if any(run.operator for run in runs):
            result.append(index)
    return result


def matched_operators_for(blocks, indices, meta):
    """Erkannte Operatoren der Blöcke ``indices`` (erstes Auftreten, ohne Duplikate)."""
    matched, _diagnostics = collect_used_operators([blocks[index] for index in indices], meta)
    return matched


def _legend_html(options: dict, matched) -> str:
    """Tabelle samt optionalem Titel (Titel innerhalb des Wrappers, wandert mit)."""
    title = str((options or {}).get("title") or "").strip()
    title_html = f"<div class='operator-legend-title'>{escape(title)}</div>" if title else ""
    return title_html + render_operator_legend_html(matched)


def annotate_operator_blocks(blocks, meta, document_type: str):
    """Hängt an jeden `operators`-Block das fertige Tabellen-HTML (`OPERATOR_LEGEND_HTML_KEY`).

    Nur für Typen mit Capability `operator_legend` (Arbeitsblatt, Klausur);
    sonst bleiben die Blöcke unverändert und rendern nichts (OPR007). Blöcke
    ohne Operatoren im Bereich bekommen leeres HTML und keinen Wrapper
    (Fehler OPR006). Der Index der Messmarken zählt nur gerenderte Tabellen
    und ist dadurch dokumentweit eindeutig. Muss **vor** `annotate_aid_parts`
    laufen (der synthetische Teil-A-Block verschiebt sonst die Indizes).
    """
    if not document_type or not shows_operator_legend(document_type):
        return blocks
    coverages = {coverage.block_index: coverage for coverage in operator_block_coverages(blocks, document_type)}
    if not coverages:
        return blocks
    result = []
    legend_index = 0
    for index, (block_type, options, content) in enumerate(blocks):
        coverage = coverages.get(index)
        if coverage is not None:
            matched = matched_operators_for(blocks, coverage.covered, meta)
            html = ""
            if matched:
                html = wrap_legend_html(_legend_html(options, matched), legend_index)
                legend_index += 1
            options = {**options, OPERATOR_LEGEND_HTML_KEY: html}
        result.append((block_type, options, content))
    return result
