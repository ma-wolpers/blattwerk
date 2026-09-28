"""Kurzentwurf: LaTeX-Formeln (`$...$`) über MathJax -- nur Inline-Formeln.

Arbeitsblatt/Präsentation laden MathJax direkt in ihrem HTML-Kopf
(`blatt_kern_layout_render.py`, `blatt_kern_layout_presentation.py`); der
Kurzentwurf nutzt dieselbe MathJax-Version und Grundkonfiguration, aber
**ohne** freistehende Formeln (`$$...$$`): in einer schmalen Tabellenzelle
ist eine eigene Formelzeile nicht sinnvoll. `$$...$$` wird deshalb nicht
korrekt gesetzt (MathJax deutet die `$$` als leere Inline-Formeln) und
vom Validator mit `KZF161` gemeldet.

Die `$...$`-Quelle selbst überlebt das Inline-Markup unverändert
(`inline_markup` schützt Formel-Spans vor `*`/`_`-Interpretation);
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
            inlineMath: [['$', '$']],
            displayMath: [],
            processEscapes: true,
            packages: {'[+]': ['boldsymbol']},
        },
        svg: { fontCache: 'none' }
    };
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js" onerror="document.body.classList.add('mathjax-load-failed')"></script>"""
"""HTML-Schnipsel für den `<head>` des Kurzentwurfs (MathJax, nur `$...$`)."""

_DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$")
_INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?![\s$])([^$\n]+?)(?<!\s)\$(?![\d$])")
"""Inline-Formel wie in `math_span_protection._MATH_SPAN_PATTERN` (Pandoc-
Heuristik gegen Währungstext wie `$5 und $10`), aber zeilenweise und ohne
`$$`-Spans, die `_DISPLAY_MATH_RE` gesondert meldet."""


def collect_math_diagnostics(source: str) -> list[Diagnostic]:
    """Liefert die Formel-Hinweise `KZF160`/`KZF161` für einen Kurzentwurf-Quelltext.

    - `KZF160` (warning, höchstens einmal pro Dokument, an der ersten
      Fundstelle): der Kurzentwurf enthält `$...$`-Formeln; MathJax wird
      von einem CDN geladen, beim Export ist daher eine Internetverbindung
      nötig -- analog `MJ001` bei Arbeitsblättern.
    - `KZF161` (warning, pro betroffener Zeile): `$$...$$` wird im
      Kurzentwurf nicht unterstützt, nur `$...$`.

    Frontmatter-Zeilen werden mitgeprüft; dort kommen Formeln praktisch
    nicht vor, eine Sonderbehandlung wäre unnötige Komplexität.
    """
    diagnostics: list[Diagnostic] = []
    first_inline_line: int | None = None
    for line_number, line in enumerate(source.splitlines(), start=1):
        display_match = _DISPLAY_MATH_RE.search(line)
        if display_match:
            diagnostics.append(
                Diagnostic(
                    code="KZF161",
                    severity="warning",
                    message=(
                        "Freistehende Formeln ($$...$$) werden im Kurzentwurf nicht unterstuetzt "
                        "und nicht korrekt dargestellt. Bitte Inline-Formeln ($...$) verwenden."
                    ),
                    line=line_number,
                    region_id=KURZENTWURF_DOCUMENT_REGION_ID,
                    # Formeltext statt Zeilennummer: bleibt beim Einfügen von Zeilen davor stabil.
                    anchor=display_match.group(0),
                )
            )
        if first_inline_line is None and _INLINE_MATH_RE.search(_DISPLAY_MATH_RE.sub("", line)):
            first_inline_line = line_number

    if first_inline_line is not None:
        diagnostics.append(
            Diagnostic(
                code="KZF160",
                severity="warning",
                message=(
                    "Enthaelt Formel-Syntax ($...$). Die Darstellung laedt MathJax von einem CDN "
                    "und benoetigt daher beim PDF-Export/der Vorschau eine Internetverbindung; "
                    "ohne Internet bleibt die rohe Formel-Quelle als Text sichtbar."
                ),
                line=first_inline_line,
                region_id=KURZENTWURF_DOCUMENT_REGION_ID,
                anchor="",
            )
        )
    return diagnostics
