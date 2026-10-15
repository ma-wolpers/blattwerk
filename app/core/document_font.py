"""Schriftprofil eines Dokuments: Frontmatter `font_profile` vor App-Einstellung.

Einzige Stelle, die entscheidet, welches Schriftprofil ein Dokument rendert. Renderer
(`render_html`, Lernhilfen) und Validator (`FM012`) nutzen dieselbe Auflösung:

* gültiger Dokumentwert -> dieser steuert Vorschau und Export,
* kein Dokumentwert -> der App-Standard (`default_font_profile` bzw. die Vorschau-
  Auswahl, die der Aufrufer übergibt),
* ungültiger Dokumentwert -> App-Standard plus Problemtext; der Validator meldet ihn
  als Warnung, sodass der Rückfall sichtbar ist und der Build trotzdem läuft.
"""

from __future__ import annotations

from ..styles.blatt_styles import FONT_PROFILE_ORDER, normalize_font_profile

FONT_PROFILE_KEY = "font_profile"


def document_font_profile_value(meta) -> str | None:
    """Rohwert von `font_profile` aus dem Frontmatter, getrimmt und klein; `None` wenn leer."""
    raw = (meta or {}).get(FONT_PROFILE_KEY)
    if raw is None:
        return None
    text = str(raw).strip().lower()
    return text or None


def resolve_document_font_profile(meta, app_default) -> tuple[str, str | None]:
    """Liefert `(profil, problem)` für ein Dokument.

    Args:
        meta: Frontmatter-Dict des Dokuments.
        app_default: Schriftprofil der App (Vorschau-Auswahl/Präferenz); wird selbst
            normalisiert, ein unbekannter Wert fällt auf das Standardprofil.

    Returns:
        Das zu rendernde Profil und ``None`` oder ein Problemtext für einen
        ungültigen Dokumentwert.

    Example:
        >>> resolve_document_font_profile({"font_profile": "Arial"}, "segoe")
        ('arial', None)
        >>> resolve_document_font_profile({}, "calibri")
        ('calibri', None)
    """
    fallback = normalize_font_profile(app_default)
    value = document_font_profile_value(meta)
    if value is None:
        return fallback, None
    if value in FONT_PROFILE_ORDER:
        return value, None
    problem = (
        f"Unbekanntes Schriftprofil `font_profile: {value}`; es gilt die App-Einstellung. "
        f"Erlaubt: {', '.join(FONT_PROFILE_ORDER)}."
    )
    return fallback, problem
