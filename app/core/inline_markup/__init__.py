"""Öffentliche Fassade des zentralen Inline-Markup-Pakets.

`parse_inline_markup(text)` ist die EINE autoritative Funktion, die
Rohtext in eine semantische `list[Run]` überführt -- Kurzentwurf
(`kurzentwurf_runtime/render_html.py`) ruft sie direkt auf,
`markdown_bridge.py` (Arbeitsblatt-/Antwortfeld-Pipelines) ruft exakt
dieselbe Funktion über einen dünnen Preprocessor-Adapter auf. Kein anderer
Code-Pfad im Projekt darf Stern, Unterstrich, Gleichheits-, Tilde-,
Zirkumflex-, Backtick-, Pipe- oder Prozent-Marker eigenständig
interpretieren.
"""

from __future__ import annotations

from .emphasis import parse_emphasis
from .html_renderer import render_inline_markup_html
from .runs import ParseDiagnostic, Run
from .spans import protect_all
from .syntax import MARKER_SPECS, EscalationLevel, MarkerSpec, marker_spec_by_key, marker_spec_by_name

__all__ = [
    "MARKER_SPECS",
    "EscalationLevel",
    "MarkerSpec",
    "ParseDiagnostic",
    "Run",
    "marker_spec_by_key",
    "marker_spec_by_name",
    "parse_inline_markup",
    "render_inline_markup",
]


def parse_inline_markup(text: str) -> tuple[list[Run], list[ParseDiagnostic]]:
    """Parst `text` gemäß der autoritativen Auswertungsreihenfolge (siehe `syntax.py`).

    Liefert `(runs, diagnostics)`. `runs` deckt den *gesamten* Eingabetext
    ab (auch unformatierter Text wird als `Run(kind="text")` ohne Flags
    zurückgegeben) -- Aufrufer können die Liste daher direkt zu Ausgabe
    zusammensetzen, ohne Lücken selbst auffüllen zu müssen.
    """
    if not text:
        return [], []

    protected_text, math_spans, code_spans, word_note_spans, diagnostics = protect_all(text)
    runs = parse_emphasis(protected_text, math_spans, code_spans, word_note_spans)
    return runs, diagnostics


def render_inline_markup(text: str) -> str:
    """Bequemlichkeits-Wrapper: parst `text` und rendert direkt zu HTML.

    Für Konsumenten, die kein Interesse an der Zwischenrepräsentation haben
    (aktuell: Kurzentwurf) -- intern nur `parse_inline_markup` +
    `render_inline_markup_html`, keine eigene Logik.
    """
    runs, _diagnostics = parse_inline_markup(text)
    return render_inline_markup_html(runs)
