"""Löst nach dem Marker-Parsing verbliebene Mathe-/Code-Platzhalter zu eigenen Runs auf.

Läuft als letzter Schritt in `emphasis.py::parse_emphasis`, nachdem alle
Marker-Durchläufe abgeschlossen sind: bis dahin waren die Platzhalter-
Zeichen für jeden Durchlauf einfach unauffällige, unformatierte Zeichen
innerhalb eines `kind="text"`-Runs (keiner der Marker-Regexe reagiert auf
sie -- eigene, disjunkte Private-Use-Bereiche für Mathe
(`math_span_protection.py`) und Code (`spans.py`)).
"""

from __future__ import annotations

from ..math_span_protection import find_math_placeholder
from .runs import Run, style_flags
from .spans import find_code_placeholder


def expand_placeholders(runs: list[Run], math_spans: list[str], code_spans: list) -> list[Run]:
    """Ersetzt verbleibende Mathe-/Code-Platzhalter-Tokens durch eigene `kind="math"`/`kind="code"`-Runs.

    Verschachteltes Fett um Inline-Code/Mathe wird dadurch bewusst NICHT
    unterstützt (siehe `runs.py`-Docstring): Stil-Flags eines umgebenden
    Runs gehen für den ausgelösten Code-/Mathe-Run verloren.
    """
    expanded: list[Run] = []
    for run in runs:
        if run.kind != "text" or not run.text:
            expanded.append(run)
            continue

        text = run.text
        flags = style_flags(run)
        pos = 0
        while pos < len(text):
            math_match = find_math_placeholder(text, pos)
            code_match = find_code_placeholder(text, pos)
            candidates = [m for m in (math_match, code_match) if m is not None]
            if not candidates:
                expanded.append(Run(kind="text", text=text[pos:], **flags))
                break

            next_match = min(candidates, key=lambda m: m.start())
            if next_match.start() > pos:
                expanded.append(Run(kind="text", text=text[pos : next_match.start()], **flags))

            index = int(next_match.group(1))
            if next_match is math_match and index < len(math_spans):
                expanded.append(Run(kind="math", text=math_spans[index]))
            elif next_match is code_match and index < len(code_spans):
                span = code_spans[index]
                expanded.append(Run(kind="code", text=span.text, is_block=span.is_block))
            else:
                # Index out of range should not happen in practice; keep the
                # placeholder text literally rather than crash or drop data.
                expanded.append(Run(kind="text", text=next_match.group(0), **flags))
            pos = next_match.end()

    return expanded
