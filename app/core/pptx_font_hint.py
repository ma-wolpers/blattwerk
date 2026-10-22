"""Hinweis beim editierbaren PPTX-Export: mitgelieferte Schriften müssen installiert sein.

Die editierbare PPTX setzt den echten Schriftnamen je Textlauf (`run.font.name`), bettet
die Schriftdatei aber nicht ein. PowerPoint zeigt eine mitgelieferte Schrift (z. B.
Comic Neue) daher nur, wenn sie auf dem Rechner installiert ist, sonst eine
Ersatzschrift. Dieser Hinweis nennt die betroffenen Schriften samt dokumentiertem
Ersatz (`BundledFont.system_fallback`) -- es gibt bewusst kein Versprechen
automatischer Verfügbarkeit.
"""

from __future__ import annotations

from ..styles.bundled_fonts import BUNDLED_FONTS
from .blatt_validator_types import BuildDiagnostic

PPTX003_BUNDLED_FONTS_NOT_EMBEDDED = "PPTX003"


def used_font_names(results) -> set[str]:
    """Alle Schriftnamen der Textläufe aus den extrahierten Folien (`result.elements`)."""
    names: set[str] = set()
    for result in results or ():
        for element in getattr(result, "elements", None) or ():
            for run in getattr(element, "runs", None) or ():
                if getattr(run, "font_name", None):
                    names.add(run.font_name)
    return names


def bundled_font_hint(results) -> BuildDiagnostic | None:
    """`PPTX003`-Warnung, wenn mitgelieferte Schriften vorkommen; sonst ``None``."""
    used = {name.lower() for name in used_font_names(results)}
    fonts = [font for font in BUNDLED_FONTS if font.family.lower() in used]
    if not fonts:
        return None
    listing = ", ".join(f"{font.family} (sonst Ersatz: {font.system_fallback})" for font in fonts)
    return BuildDiagnostic(
        code=PPTX003_BUNDLED_FONTS_NOT_EMBEDDED,
        message=(
            f"Die PPTX nutzt mitgelieferte Schriften: {listing}. PowerPoint zeigt sie nur, wenn sie "
            "auf dem Rechner installiert sind; die Schriftdateien liegen in Blattwerks Ordner assets/fonts/."
        ),
        severity="warning",
    )
