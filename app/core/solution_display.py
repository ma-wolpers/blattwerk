"""Darstellung von `:::solution`-Inhalt aus der gemeinsamen Klassifikation.

Die oberste nummerierte Liste baut dieses Modul selbst aus
`solution_structure.classify_solution` -- derselben Zerlegung, die
`solution_items` für Bewertung und Erwartungshorizont nutzt. Dadurch sind
die gerenderten Listenpunkte per Konstruktion genau die bewerteten Punkte.

Alles andere bleibt bei der unveränderten Markdown-Pipeline
(`normalize_markdown` + `convert_markdown_with_math` mit frischem Konverter):
Text-Segmente als Ganzes, jeder Punkt als eigener Inhalt (Kopf + ausgerückte
Fortsetzung). Wie bei Markdown behalten Punkte lockerer Gruppen (Leerzeilen
zwischen den Punkten) ihre Absätze; in dichten Gruppen wird der erste Absatz
ausgepackt.
"""

from __future__ import annotations

import re

from .blatt_kern_shared import _new_markdown_converter, convert_markdown_with_math, normalize_markdown
from .solution_structure import SolutionEntry, classify_solution

_LIST_INDENT = 4
"""Markdown-Einrückung des Listeninhalts; so viele führende Leerzeichen verliert eine Fortsetzungszeile."""

_LEADING_PARAGRAPH_RE = re.compile(r"^<p>(.*?)</p>", re.DOTALL)


def render_solution_html(content: str) -> str:
    """Rendert den Inhalt eines Lösungsblocks (ohne die `Lösung`-Beschriftung)."""
    parts = []
    for segment in classify_solution(content).segments:
        if segment.is_items:
            items = "\n".join(f"<li>{_render_entry(entry, segment.loose)}</li>" for entry in segment.entries)
            parts.append(f"<ol>\n{items}\n</ol>")
        elif "".join(segment.text).strip():
            parts.append(_convert("\n".join(segment.text)))
    return "\n".join(parts)


def display_head(visible_head: str) -> str:
    """Anzeigeform der Kopfzeile eines Punkts (derzeit unverändert)."""
    return visible_head


def _render_entry(entry: SolutionEntry, loose: bool) -> str:
    """Inhalt eines Listenpunkts: Kopf plus Fortsetzung, um die Listeneinrückung ausgerückt."""
    head, *rest = entry.visible_lines()
    body = "\n".join([display_head(head), *(_outdent(line) for line in rest)]).rstrip()
    html = _convert(body)
    if not loose:
        html = _LEADING_PARAGRAPH_RE.sub(r"\1", html, count=1)
    return html


def _outdent(line: str) -> str:
    """Entfernt bis zu `_LIST_INDENT` führende Leerzeichen oder einen Tab (Markdown-Listeninhalt)."""
    if line.startswith("\t"):
        return line[1:]
    stripped = len(line) - len(line.lstrip(" "))
    return line[min(stripped, _LIST_INDENT):]


def _convert(text: str) -> str:
    """Markdown-Pipeline wie bei allen anderen Blöcken, mit frischem Konverter je Stück."""
    return convert_markdown_with_math(_new_markdown_converter(), normalize_markdown(text))
