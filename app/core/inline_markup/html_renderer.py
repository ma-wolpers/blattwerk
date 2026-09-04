"""Wandelt `list[Run]` in einen HTML-String um. Kennt keine Marker-Syntax, nur Run -> Tag.

Jeder `Run` wird unabhängig von seinen Nachbarn zu einer eigenen,
verschachtelten Tag-Kette gerendert (kein Zusammenfassen benachbarter Runs
mit gemeinsamen Flaggen zu einem gemeinsamen äußeren Tag) -- das erzeugt
gelegentlich zwei aufeinanderfolgende `<strong>`-Tags statt eines
durchgehenden, ist aber visuell in jedem Browser/PDF-Renderer identisch zur
"minimalen" Variante und hält diese Funktion bewusst einfach (kein
Nachbarschafts-Zusammenführungs-Algorithmus für einen rein kosmetischen
HTML-Unterschied).

Mathe-Runs werden HTML-escaped als rohe Original-Quelle ausgegeben (inkl.
`$`-Begrenzer -- MathJax verarbeitet sie client-seitig unverändert; dasselbe
Escaping-Verhalten wie `math_span_protection.restore_math_spans`, hier ohne
dessen Platzhalter-Suchschritt, da `run.text` bereits die aufgelöste,
platzhalterfreie Formelquelle ist). Code-Runs werden HTML-escaped in
`<code>` verpackt.
"""

from __future__ import annotations

from html import escape

from .escaping import resolve_escape_placeholders
from .runs import Run

_TAG_ORDER = (
    ("highlight", "mark", None),
    ("spoiler", "span", 'class="bw-spoiler"'),
    ("strike", "del", None),
    ("bold", "strong", None),
    ("italic", "em", None),
    ("underline", "u", None),
    ("subscript", "sub", None),
    ("superscript", "sup", None),
)
"""Feste äußere-zu-innere Verschachtelungsreihenfolge für kombinierte Flaggen.

Eine feste Reihenfolge (statt z. B. Einfügereihenfolge der Flaggen) macht
das Ergebnis für dieselbe Flag-Kombination immer identisch, unabhängig
davon, in welcher Reihenfolge die Marker-Durchläufe in `emphasis.py` sie
gesetzt haben.
"""


def _render_text_run(run: Run) -> str:
    html = escape(resolve_escape_placeholders(run.text))
    # `_TAG_ORDER` lists tags outer-to-inner, so wrapping must happen in
    # REVERSE (innermost/last entry wraps the raw text first, each earlier
    # entry then wraps around that) for the list's documented order to
    # actually end up outer-to-inner in the resulting HTML.
    for flag_name, tag, attrs in reversed(_TAG_ORDER):
        if getattr(run, flag_name):
            attr_suffix = f" {attrs}" if attrs else ""
            html = f"<{tag}{attr_suffix}>{html}</{tag}>"
    return html


def render_run(run: Run) -> str:
    """Rendert einen einzelnen `Run` zu HTML."""
    if run.kind == "math":
        return escape(run.text)
    if run.kind == "code":
        if run.is_block:
            return f"<pre><code>{escape(run.text)}</code></pre>"
        return f"<code>{escape(run.text)}</code>"
    return _render_text_run(run)


def render_inline_markup_html(runs: list[Run]) -> str:
    """Rendert eine vollständige `list[Run]` zu einem HTML-String."""
    return "".join(render_run(run) for run in runs)
