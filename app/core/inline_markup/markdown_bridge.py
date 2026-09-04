"""Dünner python-markdown-Preprocessor-Adapter für den zentralen Inline-Markup-Parser.

Läuft als registrierter `Preprocessor` -- derselben Kategorie, in der
`math_span_protection.py`s Schutzschritt konzeptionell sitzt -- auf dem
gesamten rohen Dokumenttext, BEVOR python-markdown irgendetwas davon
geparst hat. Ruft `parse_inline_markup()` auf (exakt dieselbe Funktion, die
auch Kurzentwurf direkt aufruft) und ersetzt NUR die dabei erkannten
Marker-Vorkommen -- gerendert über `html_renderer.py`, per `md.htmlStash`
als Platzhalter eingefügt. Unformatierter Text (`Run.is_plain`) bleibt
Zeichen für Zeichen unverändert im Rohtext stehen, damit python-markdowns
eigene, unveränderte Zuständigkeit für Links, Autolinks, rohes Inline-HTML,
Entities, `nl2br`-Zeilenumbrüche und Blockstruktur (Tabellen/Listen/
Absätze) erhalten bleibt -- wir berühren diese Zeichenbereiche nie.

Priorität 10: registriert NACH python-markdowns eingebautem
`html_block`-Preprocessor (Priorität 20 in markdown 3.10.x, höhere Zahl
läuft zuerst), damit vom Autor eingebettetes rohes HTML bereits als eigener
Stash-Platzhalter geschützt ist, bevor unser Scan beginnt -- wir laufen so
nie unbeabsichtigt in ein rohes HTML-Element hinein. Dieses Verhalten ist
identisch zu dem, das `math_span_protection.py`s bestehender
Schutzschritt schon heute für `$...$` hat (der als eigener String-Schritt
VOR `md.convert()` läuft, also zwangsläufig auch vor `html_block`) -- keine
neue Klasse von Risiko, nur konsequent auf die neuen Marker ausgeweitet.

Math-Doppelschutz-Hinweis: `parse_inline_markup()` schützt intern auch
`$...$`-Spans (Schritt 2 der Auswertungsreihenfolge, siehe `syntax.py`).
Für `blatt_kern_shared_parsing.py`/`answer_special_shared.py` ist zu diesem
Zeitpunkt (innerhalb von `md.convert()`) bereits die ÄUSSERE, unveränderte
`math_span_protection.protect_math_spans()`-Schicht dieser beiden Module
gelaufen (vor dem `md.convert()`-Aufruf) -- der Text enthält an dieser
Stelle also gar kein literales `$` mehr, wodurch der interne Mathe-Schutz
hier zu einem harmlosen No-Op wird (nichts zu schützen gefunden). Bewusst
NICHT optimiert/übersprungen, um die 14 bestehenden Aufrufer von
`convert_markdown_with_math` nicht anzufassen -- der Preisunterschied ist
ein zusätzlicher, folgenloser Regex-Scan, keine Verhaltensänderung.
"""

from __future__ import annotations

from markdown.preprocessors import Preprocessor

from . import parse_inline_markup
from .escaping import restore_escape_backslashes
from .html_renderer import render_run

BRIDGE_PREPROCESSOR_NAME = "blattwerk_inline_markup"
BRIDGE_PREPROCESSOR_PRIORITY = 10


class InlineMarkupPreprocessor(Preprocessor):
    """Ersetzt zentral erkannte Inline-Marker-Vorkommen durch gestashtes HTML, lässt alles andere roh stehen."""

    def run(self, lines: list[str]) -> list[str]:
        text = "\n".join(lines)
        if not text:
            return lines

        runs, _diagnostics = parse_inline_markup(text)
        pieces: list[str] = []
        for run in runs:
            if run.is_plain:
                # Escapes bleiben in Backslash-Form (nicht aufgelöst!) --
                # python-markdowns eigene, weiterhin aktive
                # Escape-Behandlung muss diesen Text noch sehen, siehe
                # `restore_escape_backslashes`-Docstring.
                pieces.append(restore_escape_backslashes(run.text))
                continue
            html = render_run(run)
            placeholder = self.md.htmlStash.store(html)
            if run.kind == "code" and run.is_block:
                # Block-level HTML (`<pre><code>`) must sit on its own line
                # with blank-line boundaries, or python-markdown's block
                # parser wraps the placeholder inside a `<p>` (invalid
                # nesting) instead of recognizing it as a standalone block
                # -- mirrors how python-markdown's own `html_block`
                # preprocessor stashes raw HTML blocks.
                pieces.append(f"\n\n{placeholder}\n\n")
            else:
                pieces.append(placeholder)

        return "".join(pieces).split("\n")


def register_inline_markup_bridge(md) -> None:
    """Registriert den Inline-Markup-Preprocessor in einer `markdown.Markdown()`-Instanz.

    Aufgerufen von `blatt_kern_shared_parsing.py`s und
    `answer_special_shared.py`s `_new_markdown_converter()`-Fabriken direkt
    nach dem Erzeugen der Instanz.
    """
    md.preprocessors.register(
        InlineMarkupPreprocessor(md), BRIDGE_PREPROCESSOR_NAME, BRIDGE_PREPROCESSOR_PRIORITY
    )
