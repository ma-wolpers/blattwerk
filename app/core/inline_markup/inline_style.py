"""Effektiver Inline-Stil eines Textlaufs (`-<SPEC> … -<>`): Schrift, Größe, Farbe.

Eigener kleiner Datentyp, damit `runs.py` (Run-Modell) und `style_spans.py`
(Parser) ihn ohne Zirkelimport teilen. Ein `InlineStyle` setzt nur die
Eigenschaften, die im SPEC stehen; `inherit_from(outer)` ergänzt fehlende aus
dem umgebenden Bereich ("innerer Stil erbt pro Eigenschaft").
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape


@dataclass(frozen=True)
class InlineStyle:
    """Gesetzte Eigenschaften eines Stilbereichs (`None` = nicht gesetzt, erbt von außen).

    Attributes:
        font_css: CSS-`font-family`-Liste der Schrift.
        font_key: Schriftprofil-Schlüssel (für die Einbettung mitgelieferter Fonts
            und den PPTX-Export).
        font_family: Erster, echter Familienname (PPTX `run.font.name`).
        size_pt: Schriftgröße in Punkt.
        color: CSS-Farbe als `#rrggbb`.
    """

    font_css: str | None = None
    font_key: str | None = None
    font_family: str | None = None
    size_pt: float | None = None
    color: str | None = None

    def inherit_from(self, outer: "InlineStyle | None") -> "InlineStyle":
        """Ergänzt nicht gesetzte Eigenschaften aus `outer` (innerer Wert gewinnt).

        Example:
            >>> inner = InlineStyle(size_pt=20.0)
            >>> inner.inherit_from(InlineStyle(color="#ff0000")).color
            '#ff0000'
        """
        if outer is None:
            return self
        font_set = self.font_css is not None
        return replace(
            self,
            font_css=self.font_css if font_set else outer.font_css,
            font_key=self.font_key if font_set else outer.font_key,
            font_family=self.font_family if font_set else outer.font_family,
            size_pt=self.size_pt if self.size_pt is not None else outer.size_pt,
            color=self.color if self.color is not None else outer.color,
        )

    def css_declarations(self) -> str:
        """CSS für das `style`-Attribut, z. B. ``font-size: 12pt; color: #ff0000``."""
        parts = []
        if self.font_css:
            parts.append(f"font-family: {self.font_css}")
        if self.size_pt is not None:
            parts.append(f"font-size: {self.size_pt:g}pt")
        if self.color:
            parts.append(f"color: {self.color}")
        return "; ".join(parts)

    def wrap_html(self, inner_html: str) -> str:
        """Umhüllt bereits gerendertes HTML mit dem Stil-Span."""
        return f'<span class="bw-style" style="{escape(self.css_declarations(), quote=True)}">{inner_html}</span>'
