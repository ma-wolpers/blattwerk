"""Silbentrennung für den Druck, nur in Wörtern, die nicht in ihre Spalte passen.

Warum überhaupt: Alle Seiten setzen ``<html lang>`` und der Kurzentwurf zusätzlich
``hyphens: auto``. Der Headless-Chromium des Drucks hat aber kein Trennwörterbuch (eigenes
Profil, ``--disable-component-update``), trennt also nie. Schmale Spalten brachen lange
Wörter deshalb hart und ohne Strich um ("Stellenwertta|fel") oder ließen sie überlaufen.

Warum nur dort: Weiche Trennstriche (U+00AD) landen bei Chromium in der Textebene des PDFs,
auch wo nicht getrennt wird. Überall gesetzt, fände die PDF-Suche "Zahlenstrahle" nicht mehr
und Kopieren lieferte unsichtbare Zeichen. Deshalb zwei Schritte:

1. `hyphenate_html` (Python, vor dem Druck) merkt jedes trennbare lange Wort vor:
   ``<span class="bw-hyph" data-bw-hyph="Stel·len·…">Stellenwerttafel</span>``. Der Text
   bleibt sauber, die Trennstellen stehen nur im Attribut. Ist etwas vorgemerkt, hängt es
   `_APPLY_SCRIPT` an.
2. `_APPLY_SCRIPT` (im Browser, nach Schriften und MathJax) setzt die Trennstellen nur in
   Wörter, die hart umbrochen werden (mehr als ein Zeilenrechteck) oder breiter sind als
   ihr Block. Die Entscheidung hängt nicht von der Position ab: Ein Wort bricht nur dann
   mitten durch, wenn es nicht einmal allein in eine Zeile passt.

Wie `mathjax_support.prepare_html_for_print` ist das eine Druckvorbereitung: nur
`write_pdf_from_html` ruft `hyphenate_html` auf. Damit gilt sie für jede Pipeline, und die
Vorschau zeigt dieselben Umbrüche wie das PDF. Exportiertes HTML bleibt unverändert.
Welcher Text überhaupt angefasst wird, entscheidet `document_text_pass.map_body_text`
(hier zusätzlich ohne Code); dazu bleiben Entitäten, Internet-/Mailadressen und Wörter
kürzer als `MIN_WORD_LENGTH` unverändert. Die Sprache kommt aus ``<html lang>``; ohne
Wörterbuch bleibt die Seite gleich. Schilder setzen ``hyphens: none`` und trennen nie.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from .document_text_pass import DEFAULT_SKIPPED_ELEMENTS, map_body_text
from .hyphenation_adapter import hyphenator_for

MIN_WORD_LENGTH = 6
"""Kürzere Wörter lohnen keine Trennung (mindestens 2 + 2 Buchstaben um die Fuge)."""

MARK_CLASS = "bw-hyph"
MARK_ATTRIBUTE = "data-bw-hyph"

_SKIPPED_ELEMENTS = (*DEFAULT_SKIPPED_ELEMENTS, "pre", "code", "kbd", "samp")
_ALREADY_MARKED = rf'<span class="{MARK_CLASS}"[^>]*>.*?</span>'
_LANG_RE = re.compile(r"<html\b[^>]*?\blang\s*=\s*[\"']([^\"']+)[\"']", re.I)
_BODY_END_RE = re.compile(r"</body\s*>", re.I)
_TEXT_RE = re.compile(
    r"(?P<entity>&#?\w+;)"
    r"|(?P<address>[^\s<]*(?:://|www\.|@)[^\s<]*)"
    rf"|(?P<word>[^\W\d_]{{{MIN_WORD_LENGTH},}})"
)

# Ein Durchgang bei `load` und je ein weiterer, sobald Schriften bzw. MathJax fertig sind.
# Nicht darauf warten: Im Druck stehen Schriften bei `load` oft noch auf "loading", und ein
# Versprechen, das vor Ablauf des Zeitbudgets (`pdf_printers`) nicht einlöst, darf die
# Trennung nicht verhindern. Jeder Durchgang fasst nur noch nicht getrennte Wörter an (das
# Attribut wird danach entfernt), spätere Durchgänge bessern also nur nach. Erst alle messen,
# dann alle ändern, damit der Browser nicht nach jedem Wort neu umbricht.
_APPLY_SCRIPT = f"""<script>
(function () {{
  function blockOf(el) {{
    var node = el.parentElement;
    while (node && /^(inline|contents)$/.test(getComputedStyle(node).display)) {{ node = node.parentElement; }}
    return node;
  }}
  function innerWidth(node) {{
    var style = getComputedStyle(node);
    return node.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  }}
  function tooWide(el) {{
    if (el.getClientRects().length > 1) {{ return true; }}
    var block = blockOf(el);
    return !!block && el.getBoundingClientRect().width > innerWidth(block) + 0.5;
  }}
  function pass() {{
    var words = Array.prototype.slice.call(document.querySelectorAll('span.{MARK_CLASS}[{MARK_ATTRIBUTE}]'));
    words.filter(tooWide).forEach(function (el) {{
      el.textContent = el.getAttribute('{MARK_ATTRIBUTE}');
      el.removeAttribute('{MARK_ATTRIBUTE}');
    }});
  }}
  window.addEventListener('load', function () {{
    pass();
    if (document.fonts) {{ document.fonts.ready.then(pass); }}
    var mathjax = window.MathJax && window.MathJax.startup && window.MathJax.startup.promise;
    if (mathjax) {{ mathjax.then(pass); }}
  }});
}})();
</script>"""


def _marker(hyphenate: Callable[[str], str]) -> Callable[[str], str]:
    """Liefert die Textfunktion für `map_body_text`, die trennbare Wörter vormerkt."""

    def replace(match: re.Match) -> str:
        """Merkt ein Wort mit mindestens einer Trennstelle vor; alles andere bleibt."""
        word = match.group("word")
        if word is None:
            return match.group(0)
        hyphenated = hyphenate(word)
        if hyphenated == word:
            return word
        return f'<span class="{MARK_CLASS}" {MARK_ATTRIBUTE}="{hyphenated}">{word}</span>'

    return lambda text: _TEXT_RE.sub(replace, text)


def hyphenate_html(html: str) -> str:
    """Merkt trennbare Wörter einer fertigen Seite vor und hängt das Trennskript an.

    Args:
        html: Vollständige Seite aus einem der HTML-Erzeuger.

    Returns:
        Die Seite mit vorgemerkten Wörtern und `_APPLY_SCRIPT` vor ``</body>``; ohne
        ``<html lang>``, ohne Wörterbuch oder ohne trennbares Wort unverändert. Mehrfacher
        Aufruf ändert nichts mehr (idempotent).

    Example:
        >>> page = '<html lang="xx"><body>Stellenwerttafel</body></html>'
        >>> hyphenate_html(page) == page
        True
    """
    language = _LANG_RE.search(html)
    hyphenate = hyphenator_for(language.group(1)) if language else None
    if hyphenate is None or _APPLY_SCRIPT in html:
        return html
    marked = map_body_text(html, _marker(hyphenate), skipped_elements=_SKIPPED_ELEMENTS, protected_pattern=_ALREADY_MARKED)
    if marked == html:
        return html
    body_end = list(_BODY_END_RE.finditer(marked))
    if not body_end:
        return marked + _APPLY_SCRIPT
    cut = body_end[-1].start()
    return marked[:cut] + _APPLY_SCRIPT + marked[cut:]
