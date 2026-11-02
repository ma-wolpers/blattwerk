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
- Ueberschriften lassen sich um Ebenen nach unten schieben (``heading_offset``), damit
  ``#`` im Inhalt nicht wie der Dokumenttitel (``<h1>``) aussieht. Ein Treeprocessor
  benennt die Elemente um; Raw-HTML (``<h1>`` von Hand) liegt im HTML-Stash und bleibt,
  wie geschrieben.
"""

from __future__ import annotations

import markdown
from markdown.treeprocessors import Treeprocessor

from .inline_markup.markdown_bridge import register_inline_markup_bridge

_LIST_BLOCK_PROCESSORS = ("olist", "ulist")
MAX_HEADING_LEVEL = 6
_HEADING_LEVELS = {f"h{level}": level for level in range(1, MAX_HEADING_LEVEL + 1)}


class _HeadingOffsetProcessor(Treeprocessor):
    """Schiebt jede Markdown-Ueberschrift um ``offset`` Ebenen nach unten (hoechstens h6).

    GRENZE: ``#####`` und ``######`` landen bei Versatz 1 beide auf ``<h6>``; HTML kennt
    keine tiefere Ebene.
    """

    def __init__(self, md: markdown.Markdown, offset: int) -> None:
        """Merkt sich den Versatz fuer alle Laeufe dieses Konverters."""
        super().__init__(md)
        self.offset = offset

    def run(self, root) -> None:
        """Benennt ``h1``..``h6`` im Elementbaum um (in place, kein neuer Baum)."""
        for element in root.iter():
            level = _HEADING_LEVELS.get(element.tag)
            if level is not None:
                element.tag = f"h{min(level + self.offset, MAX_HEADING_LEVEL)}"


def new_markdown(extensions=(), *, inline_markup=True, lists=True, heading_offset=0) -> markdown.Markdown:
    """Frischer Konverter fuer einen Renderlauf.

    Args:
        extensions: python-markdown-Erweiterungen, z. B. ``("tables", "nl2br")``.
        inline_markup: Blattwerk-Inline-Marker (fett, Hervorhebung, ...) per
            `register_inline_markup_bridge` einbinden.
        lists: ``False`` = Listenmarker bleiben woertlicher Text (Tabellenzellen).
        heading_offset: Um so viele Ebenen werden Ueberschriften tiefer gesetzt
            (``1``: ``#`` -> ``<h2>``); ``0`` laesst sie unveraendert. Welcher Wert
            gilt, entscheidet der Aufrufer sichtbar (z. B.
            `document_type_registry.content_heading_offset`).

    Example:
        >>> new_markdown(inline_markup=False).convert("2025. Jahr")
        '<ol start="2025">\\n<li>Jahr</li>\\n</ol>'
        >>> new_markdown(inline_markup=False, heading_offset=1).convert("# Teil")
        '<h2>Teil</h2>'
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
    if heading_offset:
        md.treeprocessors.register(_HeadingOffsetProcessor(md, heading_offset), "blattwerk_heading_offset", 5)
    return md
