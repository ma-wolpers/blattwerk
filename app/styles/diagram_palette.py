"""Datenfarben der Diagrammblöcke: mehrere klar unterscheidbare, helle Farbtöne.

Für Blöcke, in denen Farben Dinge auseinanderhalten, etwa die Sektoren eines Kreisdiagramms.
Die Palette ist aus der Hauptfarbe des Farbprofils abgeleitet und passt deshalb zu ihm. Alle
Töne bleiben hell genug für schwarzen Text und Lücken. Im Schwarz-Weiß-Profil ist sie eine
reine Grauabstufung.
"""

from __future__ import annotations

import colorsys

DATA_COLOR_COUNT = 8
_HUE_STEPS = (0, 135, 270, 45, 180, 315, 90, 225)
"""Drehung um den Farbkreis in Grad: Nachbarn in der Reihe liegen weit auseinander."""
_NEUTRAL_BASE_HUE = 210.0
"""Ausgangston, wenn die Hauptfarbe selbst keinen Farbton hat (Profil „Grau“)."""
_MIN_SATURATION = 0.1
_LIGHTNESS = 0.8
_SATURATION = 0.62
_GRAY_STEPS = (0.72, 0.9, 0.8, 0.95, 0.66, 0.85, 0.76, 0.92)
"""Grauwerte im Schwarz-Weiß-Profil, abwechselnd, damit Nachbarn sich unterscheiden."""


def _hex(red: float, green: float, blue: float) -> str:
    """Farbanteile von 0 bis 1 als `#RRGGBB`."""
    return f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"


def data_palette(accent_hex: str, black_white: bool) -> list[str]:
    """Liefert `DATA_COLOR_COUNT` Füllfarben.

    Args:
        accent_hex: Hauptfarbe des Farbprofils als `#RRGGBB`.
        black_white: Schwarz-Weiß-Profil, dann nur Grauwerte.
    """
    if black_white:
        return [_hex(level, level, level) for level in _GRAY_STEPS]
    channels = [int(accent_hex[i: i + 2], 16) / 255 for i in (1, 3, 5)]
    hue, _lightness, saturation = colorsys.rgb_to_hls(*channels)
    base = hue * 360 if saturation >= _MIN_SATURATION else _NEUTRAL_BASE_HUE
    return [
        _hex(*colorsys.hls_to_rgb(((base + step) % 360) / 360, _LIGHTNESS, _SATURATION))
        for step in _HUE_STEPS
    ]


def data_palette_css(accent_hex: str, black_white: bool) -> str:
    """CSS-Variablen `--diagram-data-1` bis `-8` für den `:root`-Block des Designs."""
    colors = data_palette(accent_hex, black_white)
    return "\n".join(f"    --diagram-data-{index}: {color};" for index, color in enumerate(colors, start=1))
