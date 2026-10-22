"""Renderer für `:::struktogramm` (Alias `:::structogram`) -- HTML/CSS, kein SVG-Gesamtbild.

Gestalt nach den Ergänzenden Hinweisen zur GO Informatik (S. 5–6):
Methodenkopf fett über dem Diagramm, dünne Linien in Textfarbe, keine
Füllung; Verzweigung mit Dreieckskopf („wahr“ links, „falsch“ rechts),
Mehrfachauswahl mit Schräge und `sonst`-Gegenschräge, Schleifen mit
Balken links (kopfgesteuert: Kopfzeile oben; fußgesteuert: Fußzeile unten).

Warum HTML statt SVG (anders als `answer_special_mindmap.py`): Zelltexte
müssen umbrechen können (GO Beispiel 2), und SVG kennt keinen Textumbruch.
Die Struktur sind verschachtelte CSS-Grids; nur die Schrägen sind kleine
Inline-SVGs, gestreckt über genau *ihre* Grid-Spalte. Dadurch trifft die
Spitze des Dreiecks immer exakt die Spaltengrenze darunter, auch wenn ein
leerer Zweig eine feste schmale Breite hat statt eines Anteils.

Lücken-Struktogramm: Text, der nur in der Lösung sichtbar ist (`%`, `%{…}`),
wird im Arbeitsblatt mit `visibility:hidden` mitgerendert und hält so die
Höhe der Lösung; die Zelle bekommt zusätzlich die Klasse `stg-gap` mit einer
einheitlichen Mindesthöhe. Ergebnis: max(Mindesthöhe, Lösungshöhe).
"""

from __future__ import annotations

import re
from html import escape

from .answer_line_markers import _render_inline_markdown_fragment, _wrap_solution_fragment
from .struktogramm_parse import Branch, Loop, Statement, Switch, parse_struktogramm
from .struktogramm_signature import SignatureError, format_signature_html, parse_signature

_MIN_COLUMN_DEMAND = 6
"""Mindest-„Zeichenbedarf“ einer Spalte, damit kurze Zweige nicht kollabieren."""
_EMPTY_COLUMN = "4.6em"
"""Feste Breite leerer Zweige (Platz für „falsch“/„sonst“, vgl. GO Bsp. 1)."""
_SIDE_BIAS = 0.65
"""Ab diesem Breitenanteil rückt die Bedingung an die Dreiecksspitze heran."""
_WIDTH_RE = re.compile(r"^\d+(?:\.\d+)?(?:%|cm|mm|px|em|rem)$")


def _merged_segments(segments) -> list[tuple[str, str]]:
    """Fasst benachbarte Segmente gleicher Sichtbarkeit zu `(show, text)` zusammen.

    So wird `% rückgabe x` (Präfix, Ausdruck, Suffix) *eine* Lücke statt drei
    einzelner Spans, und Markdown sieht zusammenhängenden Text.
    """
    merged: list[tuple[str, str]] = []
    for segment in segments:
        if merged and merged[-1][0] == segment["show"]:
            merged[-1] = (segment["show"], merged[-1][1] + segment["text"])
        else:
            merged.append((segment["show"], segment["text"]))
    return merged


def _cell_html(cell, include_solutions: bool) -> tuple[str, bool]:
    """Rendert eine Zelle; liefert `(html, ist_lücke)`.

    Segmente nur fürs Arbeitsblatt (`§`) fehlen in der Lösung; Segmente nur
    für die Lösung (`%`) sind in der Lösung farbig markiert (wie in anderen
    Antwortblöcken) und im Arbeitsblatt unsichtbar, aber platzhaltend.
    """
    parts: list[str] = []
    has_gap = False
    for show, text in _merged_segments(cell.segments):
        # Vor Markdown escapen: Bedingungen wie `a<b` dürfen nie als HTML-Tag gelesen werden.
        fragment = _render_inline_markdown_fragment(escape(text, quote=False))
        if not fragment:
            continue
        if include_solutions:
            if show == "worksheet":
                continue
            parts.append(_wrap_solution_fragment(fragment) if show == "solution" else fragment)
        elif show == "solution":
            has_gap = True
            parts.append(f"<span class='stg-hidden'>{fragment}</span>")
        else:
            parts.append(fragment)
    return "".join(parts), has_gap


def _cell_div(cell, include_solutions: bool, extra_class: str = "") -> str:
    """Zelle als `div.stg-cell` (mit `stg-gap`, falls Lückentext darin)."""
    html, has_gap = _cell_html(cell, include_solutions)
    classes = " ".join(c for c in ("stg-cell", extra_class, "stg-gap" if has_gap else "") if c)
    return f"<div class='{classes}'>{html}</div>"


def _demand(elements: list) -> int:
    """Grober Breitenbedarf einer Folge in Zeichen (für Spaltenanteile)."""
    return max((_element_demand(element) for element in elements), default=0)


def _element_demand(element) -> int:
    """Breitenbedarf eines Elements; Spalten addieren sich, Schleifen + Balken."""
    if isinstance(element, Statement):
        return len(element.cell.text)
    if isinstance(element, Loop):
        return max(len(element.text.text), 3 + _demand(element.body))
    if isinstance(element, Branch):
        return max(len(element.condition.text) + 4, _column_demand(element.yes) + _column_demand(element.no))
    if isinstance(element, Switch):
        bodies = [case.body for case in element.cases] + ([element.default] if element.default is not None else [])
        return max(len(element.expression.text) + 4, sum(_column_demand(body) for body in bodies))
    return 0


def _column_demand(elements: list) -> int:
    """Bedarf einer Spalte, mindestens `_MIN_COLUMN_DEMAND`."""
    return max(_MIN_COLUMN_DEMAND, _demand(elements))


def _grid_template(bodies: list[list]) -> str:
    """`grid-template-columns` für Zweig-/Fallspalten: Anteil nach Bedarf, leer = schmal.

    Sind alle Spalten leer, teilen sie sich die Breite gleichmäßig.
    """
    if all(not body for body in bodies):
        return " ".join("minmax(0, 1fr)" for _ in bodies)
    return " ".join(_EMPTY_COLUMN if not body else f"minmax(0, {_column_demand(body)}fr)" for body in bodies)


def _diagonal(column: str, rising: bool) -> str:
    """Schräge über die Grid-Spalte(n) `column`: fallend (links oben → rechts unten) oder steigend."""
    points = "0,100 100,0" if rising else "0,0 100,100"
    return (
        f"<div class='stg-diag' style='grid-column:{column};'>"
        "<svg viewBox='0 0 100 100' preserveAspectRatio='none' aria-hidden='true'>"
        f"<polyline points='{points}' /></svg></div>"
    )


def _sequence(elements: list, include_solutions: bool) -> str:
    """Folge von Elementen; eine leere Folge wird eine leere Zelle."""
    inner = "".join(_element(element, include_solutions) for element in elements)
    return f"<div class='stg-seq'>{inner or _empty_cell()}</div>"


def _empty_cell() -> str:
    """Leere Zelle (z. B. fehlender `sonst`-Zweig)."""
    return "<div class='stg-cell stg-empty'></div>"


def _element(element, include_solutions: bool) -> str:
    """Dispatch auf den Renderer des Elementtyps."""
    if isinstance(element, Statement):
        return _cell_div(element.cell, include_solutions, "stg-stmt")
    if isinstance(element, Loop):
        return _loop(element, include_solutions)
    if isinstance(element, Branch):
        return _branch(element, include_solutions)
    return _switch(element, include_solutions)


def _loop(loop: Loop, include_solutions: bool) -> str:
    """Schleife: eingerückter Rumpf mit Balken links, Text oben oder unten."""
    text = _cell_div(loop.text, include_solutions, "stg-loop-text")
    body = f"<div class='stg-loop-body'>{_sequence(loop.body, include_solutions)}</div>"
    inner = text + body if loop.kind == "head" else body + text
    return f"<div class='stg-loop stg-loop-{loop.kind}'>{inner}</div>"


def _condition_place(yes: list, no: list) -> str:
    """Wo die Bedingung steht: nahe der Spitze, also im breiteren Teil an der Grenze."""
    if not no and yes:
        return "grid-column:1; justify-self:end;"
    if not yes and no:
        return "grid-column:2; justify-self:start;"
    share = _column_demand(yes) / (_column_demand(yes) + _column_demand(no))
    if share >= _SIDE_BIAS:
        return "grid-column:1; justify-self:end;"
    if share <= 1 - _SIDE_BIAS:
        return "grid-column:2; justify-self:start;"
    return "grid-column:1 / 3; justify-self:center;"


def _branch(branch: Branch, include_solutions: bool) -> str:
    """Verzweigung: Dreieckskopf über zwei Spalten, darunter wahr-/falsch-Zweig."""
    template = _grid_template([branch.yes, branch.no])
    condition, has_gap = _cell_html(branch.condition, include_solutions)
    gap_class = " stg-gap" if has_gap else ""
    head = (
        f"<div class='stg-head{gap_class}' style='grid-template-columns:{template};'>"
        f"{_diagonal('1', rising=False)}{_diagonal('2', rising=True)}"
        f"<div class='stg-head-text stg-cond' style='grid-row:1; {_condition_place(branch.yes, branch.no)}'>{condition}</div>"
        "<div class='stg-head-text stg-label' style='grid-row:2; grid-column:1; justify-self:start;'>wahr</div>"
        "<div class='stg-head-text stg-label' style='grid-row:2; grid-column:2; justify-self:end;'>falsch</div>"
        "</div>"
    )
    columns = _sequence(branch.yes, include_solutions) + _sequence(branch.no, include_solutions)
    return f"<div class='stg-branch'>{head}<div class='stg-cols' style='grid-template-columns:{template};'>{columns}</div></div>"


def _switch(switch: Switch, include_solutions: bool) -> str:
    """Mehrfachauswahl: Schräge über die Fälle, Gegenschräge über `sonst`."""
    bodies = [case.body for case in switch.cases] + ([switch.default] if switch.default is not None else [])
    template = _grid_template(bodies or [[]])
    count = max(1, len(switch.cases))
    expression, has_gap = _cell_html(switch.expression, include_solutions)
    parts = [_diagonal(f"1 / {count + 1}", rising=False)]
    if switch.default is not None:
        parts.append(_diagonal(str(count + 1), rising=True))
    parts.append(f"<div class='stg-head-text stg-cond' style='grid-row:1; grid-column:1 / {count + 1}; justify-self:end;'>{expression}</div>")
    for position, case in enumerate(switch.cases, start=1):
        value, case_gap = _cell_html(case.value, include_solutions)
        has_gap = has_gap or case_gap
        parts.append(f"<div class='stg-head-text stg-label' style='grid-row:2; grid-column:{position}; justify-self:center;'>{value}</div>")
    if switch.default is not None:
        parts.append(f"<div class='stg-head-text stg-label' style='grid-row:2; grid-column:{count + 1}; justify-self:end;'>sonst</div>")
    gap_class = " stg-gap" if has_gap else ""
    head = f"<div class='stg-head{gap_class}' style='grid-template-columns:{template};'>{''.join(parts)}</div>"
    columns = "".join(_sequence(body, include_solutions) for body in bodies) or _empty_cell()
    return f"<div class='stg-switch'>{head}<div class='stg-cols' style='grid-template-columns:{template};'>{columns}</div></div>"


def _signature_html(options) -> str:
    """Methodenkopf; eine ungültige Signatur erscheint roh (der Validator meldet sie)."""
    raw = str((options or {}).get("signature") or "").strip()
    if not raw:
        return ""
    try:
        return format_signature_html(parse_signature(raw))
    except SignatureError:
        return f"<div class='stg-sig'>{escape(raw)}</div>"


def render_struktogramm_block(options, content, include_solutions=False) -> str:
    """Rendert einen Struktogramm-Block als HTML.

    Args:
        options: Blockoptionen (`signature`, `width`; `align` wertet der
            Dispatcher über `_wrap_with_object_alignment` aus).
        content: *Roher* Blockinhalt -- nicht durch `normalize_markdown`
            schicken, das würde Leerzeilen vor `-`-Zeilen einfügen und die
            Einrückungsstruktur verfälschen.
        include_solutions: Lösungsfassung (Lückentext sichtbar, farbig).
    """
    elements, _issues = parse_struktogramm(content)
    if not elements:
        return ""
    width = str((options or {}).get("width") or "").strip()
    style = f" style='width:{width};'" if _WIDTH_RE.match(width) else ""
    body = "".join(_element(element, include_solutions) for element in elements)
    return f"<div class='stg-block'{style}>{_signature_html(options)}<div class='stg'><div class='stg-seq'>{body}</div></div></div>"


def estimate_struktogramm_weight(options, content) -> float:
    """Schätzt das Layoutgewicht (für automatische Spaltenbreiten).

    Ein Struktogramm wächst mit der Zahl der Elemente (Zeilen) und braucht
    wegen der Spaltenaufteilung eher Breite als Fließtext gleicher Länge.
    """
    lines = [line for line in str(content or "").splitlines() if line.strip()]
    if not lines:
        return 0.0
    longest = max(len(line.strip()) for line in lines)
    return 0.8 + 0.18 * len(lines) + longest / 55.0
