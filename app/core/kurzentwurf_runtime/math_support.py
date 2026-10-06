"""Kurzentwurf: LaTeX-Formeln über MathJax -- alles wird inline gesetzt.

Arbeitsblatt/Präsentation laden MathJax direkt in ihrem HTML-Kopf
(`blatt_kern_layout_render.py`, `blatt_kern_layout_presentation.py`); der
Kurzentwurf nutzt dieselbe MathJax-Version und Grundkonfiguration, kennt
aber **keine** freistehenden Formeln: in einer schmalen Tabellenzelle ist
eine eigene, zentrierte Formelzeile nicht sinnvoll. `$$...$$` wird deshalb
genauso wie `$...$` als Inline-Formel gesetzt (beide Paare stehen in
`inlineMath`; MathJax sortiert Begrenzer nach Länge, `$$` gewinnt also vor
`$`), `displayMath` bleibt leer.

Die Formel-Quelle selbst überlebt das Inline-Markup unverändert
(`inline_markup` schützt `$...$`/`$$...$$`-Spans vor `*`/`_`-Interpretation);
MathJax setzt sie clientseitig beim Rendern im Headless-Browser.
"""

from __future__ import annotations

import re

from .model import Diagnostic
from .region import KURZENTWURF_DOCUMENT_REGION_ID

MATHJAX_INLINE_HEAD_HTML = """<script>
    window.MathJax = {
        loader: { load: ['[tex]/boldsymbol'] },
        tex: {
            inlineMath: [['$$', '$$'], ['$', '$']],
            displayMath: [],
            processEscapes: true,
            packages: {'[+]': ['boldsymbol']},
        },
        svg: { fontCache: 'none' }
    };
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js" onerror="document.body.classList.add('mathjax-load-failed')"></script>"""
"""HTML-Schnipsel für den `<head>` des Kurzentwurfs (MathJax, `$$...$$` und `$...$` inline)."""

_DOUBLE_DOLLAR_MATH_RE = re.compile(r"\$\$(.+?)\$\$")
_INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?![\s$])([^$\n]+?)(?<!\s)\$(?![\d$])")
"""Inline-Formel wie in `math_span_protection._MATH_SPAN_PATTERN` (Pandoc-
Heuristik gegen Währungstext wie `$5 und $10`), aber zeilenweise; `$$`-Spans
erkennt `_DOUBLE_DOLLAR_MATH_RE` separat."""


def _line_contains_math(line: str) -> bool:
    """Prüft, ob eine Quellzeile mindestens eine `$$...$$`- oder `$...$`-Formel enthält."""
    if _DOUBLE_DOLLAR_MATH_RE.search(line):
        return True
    return bool(_INLINE_MATH_RE.search(line))


def collect_math_diagnostics(source: str) -> list[Diagnostic]:
    """Liefert die Formel-Hinweise `KZF160`/`KZF161` für einen Kurzentwurf-Quelltext.

    - `KZF160` (warning, höchstens einmal pro Dokument, an der ersten
      Fundstelle): der Kurzentwurf enthält Formeln (`$...$` oder
      `$$...$$`); MathJax wird von einem CDN geladen, bei Vorschau/Export
      ist daher eine Internetverbindung nötig -- analog `MJ001` bei
      Arbeitsblättern.
    - `KZF161` (warning, pro `$$...$$`-Formel): rein informativ -- die
      Formel wird korrekt gesetzt, aber im Fließtext statt (wie im
      Arbeitsblatt gewohnt) als eigene, zentrierte Formelzeile. Ankert am
      Formeltext statt an der Zeilennummer, damit eine abgehakte Warnung
      beim Einfügen von Zeilen davor abgehakt bleibt.

    Frontmatter-Zeilen werden mitgeprüft; dort kommen Formeln praktisch
    nicht vor, eine Sonderbehandlung wäre unnötige Komplexität.
    """
    diagnostics: list[Diagnostic] = []
    first_math_line: int | None = None
    for line_number, line in enumerate(source.splitlines(), start=1):
        for match in _DOUBLE_DOLLAR_MATH_RE.finditer(line):
            diagnostics.append(
                Diagnostic(
                    code="KZF161",
                    severity="warning",
                    message=(
                        "$$...$$ wird im Kurzentwurf im Fliesstext gesetzt (wie $...$), "
                        "nicht als eigene, zentrierte Formelzeile."
                    ),
                    line=line_number,
                    region_id=KURZENTWURF_DOCUMENT_REGION_ID,
                    anchor=match.group(0),
                )
            )
        if first_math_line is None and _line_contains_math(line):
            first_math_line = line_number

    if first_math_line is not None:
        diagnostics.append(
            Diagnostic(
                code="KZF160",
                severity="warning",
                message=(
                    "Enthaelt Formel-Syntax ($...$). Die Darstellung laedt MathJax von einem CDN "
                    "und benoetigt daher beim PDF-Export/der Vorschau eine Internetverbindung; "
                    "ohne Internet bleibt die rohe Formel-Quelle als Text sichtbar."
                ),
                line=first_math_line,
                region_id=KURZENTWURF_DOCUMENT_REGION_ID,
                anchor="",
            )
        )
    return diagnostics
