"""Löst nach dem Marker-Parsing verbliebene Mathe-/Code-/Worterklärungs-Platzhalter zu eigenen Runs auf.

Läuft als letzter Schritt in `emphasis.py::parse_emphasis`, nachdem alle
Marker-Durchläufe abgeschlossen sind: bis dahin waren die Platzhalter-
Zeichen für jeden Durchlauf einfach unauffällige, unformatierte Zeichen
innerhalb eines `kind="text"`-Runs (keiner der Marker-Regexe reagiert auf
sie -- eigene, disjunkte Private-Use-Bereiche für Mathe
(`math_span_protection.py`), Code (`spans.py`) und Worterklärung
(`word_notes.py`)).
"""

from __future__ import annotations

from ..math_span_protection import find_math_placeholder
from .runs import Run, style_flags
from .spans import find_code_placeholder
from .word_notes import find_word_note_placeholder


def _literal_note_text(text: str, math_spans: list[str], code_spans: list) -> str:
    """Löst Mathe-/Code-Platzhalter in Begriff/Erklärung zu wörtlichem Quelltext auf.

    In einer Worterklärung wird kein Markup interpretiert: eine Formel oder
    ein Code-Span darin erscheint als der Text, den der Autor geschrieben hat
    (`$x$`, `` `code` ``), nicht als gerenderte Formel/Code.
    """
    result: list[str] = []
    pos = 0
    while pos < len(text):
        math_match = find_math_placeholder(text, pos)
        code_match = find_code_placeholder(text, pos)
        candidates = [m for m in (math_match, code_match) if m is not None]
        if not candidates:
            result.append(text[pos:])
            break
        next_match = min(candidates, key=lambda m: m.start())
        result.append(text[pos : next_match.start()])
        index = int(next_match.group(1))
        if next_match is math_match and index < len(math_spans):
            result.append(math_spans[index])
        elif next_match is code_match and index < len(code_spans):
            result.append(f"`{code_spans[index].text}`")
        else:
            result.append(next_match.group(0))
        pos = next_match.end()
    return "".join(result)


def expand_placeholders(
    runs: list[Run], math_spans: list[str], code_spans: list, word_note_spans: list
) -> list[Run]:
    """Ersetzt verbleibende Platzhalter-Tokens durch eigene Runs.

    Mathe -> `kind="math"`, Code -> `kind="code"`, Worterklärung ->
    `kind="text"` mit `annotation`. Verschachteltes Fett um Inline-Code/Mathe
    wird dadurch bewusst NICHT unterstützt (siehe `runs.py`-Docstring):
    Stil-Flags eines umgebenden Runs gehen für den ausgelösten Code-/Mathe-Run
    verloren. Der Begriff einer Worterklärung behält dagegen die Flags des
    umgebenden Runs (ein Begriff in `**fett**` bleibt fett).
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
            note_match = find_word_note_placeholder(text, pos)
            candidates = [m for m in (math_match, code_match, note_match) if m is not None]
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
            elif next_match is note_match and index < len(word_note_spans):
                note = word_note_spans[index]
                expanded.append(
                    Run(
                        kind="text",
                        text=_literal_note_text(note.term, math_spans, code_spans),
                        annotation=_literal_note_text(note.explanation, math_spans, code_spans),
                        **flags,
                    )
                )
            else:
                # Index out of range should not happen in practice; keep the
                # placeholder text literally rather than crash or drop data.
                expanded.append(Run(kind="text", text=next_match.group(0), **flags))
            pos = next_match.end()

    return expanded
