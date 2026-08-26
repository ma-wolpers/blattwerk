"""Schuetzt `$...$`/`$$...$$`-Formel-Spans vor dem Markdown-Rendern.

Geteilte Grundlage fuer beide `_new_markdown_converter()`-Fabriken
(`blatt_kern_shared_parsing.py`, `answer_special_shared.py`) -- diese
beiden Fabriken selbst bleiben bewusst dupliziert (siehe ihre eigenen
Modul-Docstrings), aber die Mathe-Schutz-Logik hier ist unabhaengig davon,
welche der beiden Fabriken den `md`-Konverter erzeugt hat, und wird daher
nur einmal gepflegt. Jedes der beiden Module bietet einen duennen
`convert_markdown_with_math(md, text)`-Wrapper an, der `_convert` unten mit
seiner eigenen `normalize_markdown`-Funktion aufruft.

MathJax laeuft clientseitig auf dem fertigen HTML und erwartet die
unveraenderte LaTeX-Quelle (`\\frac{a}{b}`, `x_i`, `\\{...\\}`) -- ohne
Schutz wuerde `python-markdown` Backslashes vor Interpunktion entfernen und
`*`/`_` als Betonungs-Syntax interpretieren, was die Formel beschaedigt.
"""

from __future__ import annotations

import re
from html import escape

_MATH_SPAN_PATTERN = re.compile(
    r"\$\$(.+?)\$\$"  # Display-Mathe -- ein starkes, eindeutiges Signal, keine Waehrungs-Verwechslungsgefahr.
    r"|\$(?!\s)(.+?)(?<!\s)\$(?!\d)",  # Inline-Mathe, Pandoc-Heuristik gegen "$5 ... $10"-Waehrungstext.
    re.DOTALL,
)
"""Erkennt `$...$`/`$$...$$`-Formel-Spans.

Die Inline-Variante verlangt zusaetzlich (a) keinen Leerraum direkt hinter
dem oeffnenden bzw. vor dem schliessenden `$` und (b) keine Ziffer direkt
nach dem schliessenden `$` -- die von Pandocs `tex_math_dollars` uebernommene
Standard-Heuristik, um Waehrungstext wie `"Preis: $5 und $10"` nicht als
Formel misszuverstehen. Wichtiger Nebeneffekt bei echtem Formeltext direkt
neben einem unpaarigen `$`-Zeichen (z. B. `"Preis: $5 und $x$"`): Pythons
`re`-Backtracking verwirft automatisch jeden Kandidaten, dessen vermeintlich
schliessendes `$` von Leerraum umgeben ist, und findet danach die naechste
gueltige Startposition -- ohne eigene Nachverarbeitung noetig (siehe
`tests/test_math_span_protection.py`)."""

_MATH_PLACEHOLDER_START = ""
_MATH_PLACEHOLDER_END = ""
"""Unicode-Private-Use-Zeichen als Platzhalter-Klammer, siehe `protect_math_spans`.

Bewusst **kein** ASCII-Token wie `@@MATH0@@`: ein Private-Use-Zeichen kommt in
echtem Autor:innen-Text praktisch nie vor, und keiner der von
`MARKDOWN_EXTENSIONS` genutzten Inline-Prozessoren (Emphasis, Code-Spans,
Links) reagiert auf diese Zeichen -- der Platzhalter durchlaeuft
`md.convert()` also garantiert unveraendert."""

_MATH_PLACEHOLDER_PATTERN = re.compile(
    f"{_MATH_PLACEHOLDER_START}(\\d+){_MATH_PLACEHOLDER_END}"
)


def protect_math_spans(text):
    """Ersetzt jeden `$...$`/`$$...$$`-Formel-Span in `text` durch einen Platzhalter.

    Liefert `(geschuetzter_text, spans)`, wobei `spans[i]` der rohe,
    unveraenderte Formel-Span (inkl. `$`-Begrenzer) ist, den Platzhalter `i`
    ersetzt. `spans` wird an `restore_math_spans` weitergereicht, um nach dem
    Markdown-Rendern die Original-Quelle (nur HTML-escaped) wiederherzustellen.
    """
    if not text:
        return text, []

    spans = []

    def _replace(match):
        index = len(spans)
        spans.append(match.group(0))
        return f"{_MATH_PLACEHOLDER_START}{index}{_MATH_PLACEHOLDER_END}"

    return _MATH_SPAN_PATTERN.sub(_replace, text), spans


def _restore_math_spans(text, spans, escape_fn):
    """Gemeinsame Platzhalter-Rueckersetzung fuer `restore_math_spans`/`restore_math_spans_as_text`.

    Nutzt ein exaktes Platzhalter-Pattern (kein blindes Teilstring-Replace)
    -- ein zufaellig aehnlich aussehender String im Text kann daher nie
    faelschlich ersetzt werden. Ein Index ausserhalb von `spans` (sollte bei
    korrekter Verwendung nie vorkommen) laesst den Platzhalter unveraendert,
    statt einen Fehler zu werfen -- defensiv, kein Kompilierabbruch wegen
    einer reinen Rendering-Hilfsfunktion.
    """
    if not spans:
        return text

    def _restore(match):
        index = int(match.group(1))
        if index >= len(spans):
            return match.group(0)
        return escape_fn(spans[index])

    return _MATH_PLACEHOLDER_PATTERN.sub(_restore, text)


def restore_math_spans(html, spans):
    """Setzt die von `protect_math_spans` platzierten Platzhalter durch die Original-Formel-Quelle zurueck.

    HTML-escaped die wiederhergestellte Formel-Quelle -- fuer Aufrufer, die
    direkt fertiges HTML produzieren (z. B. `convert_markdown_with_math`).
    """
    return _restore_math_spans(html, spans, escape)


def restore_math_spans_as_text(text, spans):
    """Wie `restore_math_spans`, aber ohne HTML-Escaping.

    Fuer Aufrufer, deren Ergebnis noch **kein** finales HTML ist, sondern
    selbst spaeter noch durch `convert_markdown_with_math` laeuft (z. B.
    `answer_line_markers.py::parse_answer_line_visibility`, das der
    Marker-Sichtbarkeits-Schicht vorgelagert ist) -- HTML-Escaping an dieser
    Stelle wuerde doppelt escapen (`$a < b$` wuerde als `$a &lt; b$` in die
    Formel eingebettet, statt erst beim finalen HTML-Rendering escaped zu
    werden).
    """
    return _restore_math_spans(text, spans, lambda value: value)


def convert_markdown_with_math(md, text, normalize_fn):
    """Rendert `text` per `md.convert(normalize_fn(...))`, mit Mathe-Schutz.

    `normalize_fn` ist die aufrufereigene `normalize_markdown`-Funktion
    (`blatt_kern_shared_parsing.py`/`answer_special_shared.py` haben je eine
    eigene, nicht konsolidierte Instanz) -- schuetzt Formel-Spans vor dem
    Konvertieren und stellt sie danach wieder her, sodass MathJax auf der
    Client-Seite die unveraenderte LaTeX-Quelle vorfindet.
    """
    protected_text, spans = protect_math_spans(text or "")
    html = md.convert(normalize_fn(protected_text))
    return restore_math_spans(html, spans)
