"""MathJax an einer Stelle: Version, Konfigurationsprofile, Einbinden und Druckvorbereitung.

Die HTML-Erzeuger binden MathJax immer über den CDN-Link ein (`mathjax_head`). So bleibt
eine exportierte HTML-Datei auf jedem Rechner lauffähig; ein lokaler Pfad würde dort ins
Leere zeigen. Den Unterschied macht allein der Druck: `prepare_html_for_print` entfernt
MathJax aus Seiten ohne Formel und stellt alle anderen auf das mitgelieferte Paket um.

Warum das wichtig ist (Messung im Development-Log, 2026-10-30): Das Laden vom CDN kostete
je Druck rund 5 s, auch ohne Formel, und ohne Internet blieben Formeln still roh.

Das Paket unter `assets/mathjax/` erzeugt `tools/vendor_mathjax.py` für `MATHJAX_VERSION`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MATHJAX_VERSION = "4.1.3"
"""Exakte Version für CDN-Link und mitgeliefertes Paket; Vendoring und Link bleiben gleich."""

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "mathjax"
_LOCAL_SCRIPT = ASSET_DIR / "mathjax" / "tex-svg.js"
_LOCAL_FONTS = ASSET_DIR / "@mathjax"

_CDN_SCRIPT_TAG = f'<script defer src="https://cdn.jsdelivr.net/npm/mathjax@{MATHJAX_VERSION}/tex-svg.js"></script>'

PROFILE_DOCUMENT = "document"
"""Arbeitsblatt, Klausur, Präsentation, Lernhilfen: `$$` freistehend, `\\boldsymbol` geladen."""

PROFILE_PLAIN = "plain"
"""Schlichtes Markdown und Erwartungshorizont: ohne Zusatzpakete."""

PROFILE_KURZENTWURF = "kurzentwurf"
"""Kurzentwurf: auch `$$` bleibt inline, weil die Formeln in Tabellenzellen stehen."""

_PROFILES = {
    PROFILE_DOCUMENT: """{
    loader: { load: ['[tex]/boldsymbol'] },
    tex: {
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true,
        packages: {'[+]': ['boldsymbol']},
    },
    svg: { fontCache: 'none' }
}""",
    PROFILE_PLAIN: """{
    tex: { inlineMath: [['$', '$']], displayMath: [['$$', '$$']], processEscapes: true },
    svg: { fontCache: 'none' }
}""",
    PROFILE_KURZENTWURF: """{
    loader: { load: ['[tex]/boldsymbol'] },
    tex: {
        inlineMath: [['$$', '$$'], ['$', '$']],
        displayMath: [],
        processEscapes: true,
        packages: {'[+]': ['boldsymbol']},
    },
    svg: { fontCache: 'none' }
}""",
}

_MATH_TOKEN_RE = re.compile(r"\$|\\begin\{|\\ref\{|\\eqref\{")
"""Alles, was MathJax im Text setzen könnte. Bewusst weit: Ein Fehlalarm (etwa `5 $`) kostet
nur Zeit, ein übersehener Treffer dagegen liefert rohe Formeln. Eine Prüfung der Quelle
würde Titel, Kopfzeile und Blockoptionen verpassen, deshalb zählt der fertige Body."""


def mathjax_head(profile: str) -> str:
    """Liefert den `<head>`-Schnipsel für ein Konfigurationsprofil.

    Args:
        profile: Eines der ``PROFILE_*``.

    Raises:
        KeyError: Unbekanntes Profil.

    Example:
        >>> "tex-svg.js" in mathjax_head(PROFILE_PLAIN)
        True
    """
    return f"<script>\nwindow.MathJax = {_PROFILES[profile]};\n</script>\n{_CDN_SCRIPT_TAG}"


def body_contains_math(html: str) -> bool:
    """Prüft den Body einer fertigen Seite auf mögliche Formeln.

    Example:
        >>> body_contains_math("<head>$</head><body>5 Euro</body>")
        False
        >>> body_contains_math("<head></head><body>$x$</body>")
        True
    """
    _head, separator, body = html.partition("</head>")
    return bool(_MATH_TOKEN_RE.search(body if separator else html))


def prepare_html_for_print(html: str) -> str:
    """Passt eine Seite für den Chromium-Druck an; nur `write_pdf_from_html` ruft das auf.

    - Ohne Formel im Body entfällt das MathJax-Skript ganz.
    - Sonst lädt der Browser das mitgelieferte Paket. Der Schriftpfad muss mit: MathJax
      holt Schriftteile (etwa für `\\mathbb`) sonst fest vom CDN und lässt die ganze Seite
      roh, wenn das scheitert.
    - Fehlt das Paket (unvollständiger Checkout), bleibt der CDN-Link als Rückfall.

    Args:
        html: Vollständige Seite aus einem der HTML-Erzeuger.

    Returns:
        Die druckfertige Seite; Seiten ohne MathJax-Tag bleiben unverändert.
    """
    if _CDN_SCRIPT_TAG not in html:
        return html
    if not body_contains_math(html):
        return html.replace(_CDN_SCRIPT_TAG, "")
    if not _LOCAL_SCRIPT.exists():
        return html
    paths = json.dumps({"fonts": _LOCAL_FONTS.as_uri()})
    local_tags = (
        f"<script>window.MathJax.loader = Object.assign(window.MathJax.loader || {{}}, {{paths: {paths}}});</script>\n"
        f'<script defer src="{_LOCAL_SCRIPT.as_uri()}"></script>'
    )
    return html.replace(_CDN_SCRIPT_TAG, local_tags)
