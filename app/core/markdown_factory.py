"""Einzige Stelle, die python-markdown-Konverter baut und dessen Interna kennt.

Alle Renderer (Blockinhalte, Antwortfelder, Tabellenzellen, Markdown-Export,
Erwartungshorizont, Hilfe-Doku) holen ihren Konverter hier. Verifiziert gegen
python-markdown 3.10:

- Geordnete Listen beginnen sonst immer bei 1 (``OListProcessor.LAZY_OL = True``):
  "2025. Jahr" wurde "1. Jahr", "3. a" wurde "1. a". Ein Konstruktor-Argument dafuer
  gibt es nicht (``Markdown(lazy_ol=False)`` wird still ignoriert); gesetzt wird das
  Attribut am Prozessor der Instanz, dann erzeugt python-markdown ``<ol start="2025">``.
- Listen lassen sich fuer reinen Inline-Inhalt (Tabellenzellen) abschalten, indem die
  Blockprozessoren ``olist``/``ulist`` abgemeldet werden.
"""

from __future__ import annotations

import markdown

from .inline_markup.markdown_bridge import register_inline_markup_bridge

_LIST_BLOCK_PROCESSORS = ("olist", "ulist")


def new_markdown(extensions=(), *, inline_markup=True, lists=True) -> markdown.Markdown:
    """Frischer Konverter fuer einen Renderlauf.

    Args:
        extensions: python-markdown-Erweiterungen, z. B. ``("tables", "nl2br")``.
        inline_markup: Blattwerk-Inline-Marker (fett, Hervorhebung, ...) per
            `register_inline_markup_bridge` einbinden.
        lists: ``False`` = Listenmarker bleiben woertlicher Text (Tabellenzellen).

    Example:
        >>> new_markdown(inline_markup=False).convert("2025. Jahr")
        '<ol start="2025">\\n<li>Jahr</li>\\n</ol>'
    """
    md = markdown.Markdown(extensions=list(extensions))
    if inline_markup:
        register_inline_markup_bridge(md)
    processors = md.parser.blockprocessors
    if not lists:
        for name in _LIST_BLOCK_PROCESSORS:
            processors.deregister(name, strict=False)
    elif "olist" in processors:
        processors["olist"].LAZY_OL = False
    return md
