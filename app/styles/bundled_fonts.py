"""Mitgelieferte Schriften (OFL) fuer Arbeitsblaetter, Klausuren und Praesentationen.

Die Dateien liegen unter `assets/fonts/<ordner>/` jeweils mit ihrer Lizenz (`OFL.txt`).
Der Katalog beschreibt nur Schnitte, die tatsaechlich als Datei vorliegen; fehlt z. B.
ein Fettschnitt, wird keiner deklariert und der Browser erzeugt ihn synthetisch wie bei
jeder Systemschrift. Ein Test gleicht Katalog, Dateien und Lizenzen ab.

Einbindung: `font_face_css(keys)` erzeugt `@font-face`-Regeln mit `data:`-URIs, und zwar
nur fuer die uebergebenen (im Dokument benutzten) Familien und hoechstens einmal je
Familie. `data:` statt `file:`, damit dieselbe Regel im PDF-Druck (Chromium aus einer
temporaeren HTML-Datei), im HTML-Export (Datei wird weitergegeben) und im editierbaren
PPTX-Export (Playwright) gleich wirkt.

GRENZE(variable-font): Fredoka liegt nur als Variable Font vor (Achse `wght` 300-700).
Chromium bettet dessen Instanzen als Type3-Schriften ein: sichtbar und durchsuchbar,
aber ohne Familiennamen im PDF und in manchen Betrachtern weniger scharf.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"


@dataclass(frozen=True)
class FontFace:
    """Ein Schnitt einer Familie: Datei relativ zu `FONTS_DIR`, Stil und Gewicht.

    Genau eines von `weight` (statischer Schnitt) oder `weight_range` (Variable Font,
    nur Fredoka) ist gesetzt.
    """

    path: str
    style: str = "normal"
    weight: int | None = 400
    weight_range: tuple[int, int] | None = None

    def css_weight(self) -> str:
        """`font-weight`-Wert fuer `@font-face` (Einzelwert oder Bereich)."""
        if self.weight_range is not None:
            return f"{self.weight_range[0]} {self.weight_range[1]}"
        return str(self.weight)


@dataclass(frozen=True)
class BundledFont:
    """Eine mitgelieferte Familie.

    Attributes:
        key: Schluessel im Schriftprofil-Katalog (`FONT_PROFILE_PRESETS`) und in
            `font_profile`.
        family: Echter Familienname (fuer CSS und den PPTX-Export, damit ein auf dem
            Zielrechner installierter Font greift).
        system_fallback: Aehnliche, unter Windows vorinstallierte Schrift: CSS-Fallback,
            Darstellung im Tk-Schriftmenue und dokumentierter PPTX-Ersatz.
        generic: Generische CSS-Familie als letzter Fallback.
        folder: Ordner unter `FONTS_DIR`.
        faces: Die vorhandenen Schnitte.
    """

    key: str
    family: str
    system_fallback: str
    generic: str
    folder: str
    faces: tuple[FontFace, ...]

    @property
    def license_path(self) -> Path:
        """Pfad der mitgelieferten Lizenzdatei."""
        return FONTS_DIR / self.folder / "OFL.txt"

    def css_family(self) -> str:
        """CSS-`font-family`-Liste: eigener Font, System-Ersatz, generische Familie."""
        return f"'{self.family}', '{self.system_fallback}', {self.generic}"


def _static(folder: str, names: dict[tuple[int, str], str]) -> tuple[FontFace, ...]:
    """Baut statische Schnitte aus `{(gewicht, stil): dateiname}`."""
    return tuple(
        FontFace(path=f"{folder}/{file_name}", style=style, weight=weight)
        for (weight, style), file_name in names.items()
    )


BUNDLED_FONTS: tuple[BundledFont, ...] = (
    BundledFont(
        "comic_neue", "Comic Neue", "Comic Sans MS", "cursive", "comic-neue",
        _static("comic-neue", {
            (300, "normal"): "ComicNeue-Light.ttf",
            (300, "italic"): "ComicNeue-LightItalic.ttf",
            (400, "normal"): "ComicNeue-Regular.ttf",
            (400, "italic"): "ComicNeue-Italic.ttf",
            (700, "normal"): "ComicNeue-Bold.ttf",
            (700, "italic"): "ComicNeue-BoldItalic.ttf",
        }),
    ),
    BundledFont(
        "andika", "Andika", "Segoe UI", "sans-serif", "andika",
        _static("andika", {
            (400, "normal"): "Andika-Regular.ttf",
            (400, "italic"): "Andika-Italic.ttf",
            (700, "normal"): "Andika-Bold.ttf",
            (700, "italic"): "Andika-BoldItalic.ttf",
        }),
    ),
    BundledFont(
        "fredoka", "Fredoka", "Segoe UI", "sans-serif", "fredoka",
        (FontFace(path="fredoka/Fredoka-Variable.ttf", weight=None, weight_range=(300, 700)),),
    ),
    BundledFont(
        "patrick_hand", "Patrick Hand", "Segoe Print", "cursive", "patrick-hand",
        _static("patrick-hand", {(400, "normal"): "PatrickHand-Regular.ttf"}),
    ),
    BundledFont(
        "indie_flower", "Indie Flower", "Ink Free", "cursive", "indie-flower",
        _static("indie-flower", {(400, "normal"): "IndieFlower-Regular.ttf"}),
    ),
    BundledFont(
        "gloria_hallelujah", "Gloria Hallelujah", "Segoe Print", "cursive", "gloria-hallelujah",
        _static("gloria-hallelujah", {(400, "normal"): "GloriaHallelujah.ttf"}),
    ),
    BundledFont(
        "short_stack", "Short Stack", "Segoe Print", "cursive", "short-stack",
        _static("short-stack", {(400, "normal"): "ShortStack-Regular.ttf"}),
    ),
)

BUNDLED_FONTS_BY_KEY = {font.key: font for font in BUNDLED_FONTS}


def bundled_font_presets() -> dict[str, dict[str, str]]:
    """Eintraege fuer `FONT_PROFILE_PRESETS` (gleiches Schema wie die Systemschriften).

    `tk_family` ist der System-Ersatz, weil Tk die mitgelieferten Dateien nicht laden
    kann; das Schriftmenue zeigt den Namen also in einer aehnlichen Systemschrift.
    """
    return {
        font.key: {
            "label": f"{font.family} (mitgeliefert)",
            "css_family": font.css_family(),
            "tk_family": font.system_fallback,
        }
        for font in BUNDLED_FONTS
    }


def bundled_font_file(key: str, weight: int = 400, style: str = "normal") -> Path:
    """Absoluter Pfad der Schriftdatei eines mitgelieferten Schnitts.

    Fuer Stellen, die eine Schrift ausserhalb von CSS brauchen (z. B. das Stempeln der
    PDF-Laufelemente per PyMuPDF), damit der Dateiname nur in diesem Katalog steht.

    Args:
        key: Familienschluessel aus `BUNDLED_FONTS`, z. B. ``"andika"``.
        weight: Gewicht des statischen Schnitts.
        style: ``"normal"`` oder ``"italic"``.

    Raises:
        KeyError: Familie oder Schnitt ist nicht im Katalog.

    Example:
        >>> bundled_font_file("andika").name
        'Andika-Regular.ttf'
    """
    font = BUNDLED_FONTS_BY_KEY[key]
    for face in font.faces:
        if face.weight == weight and face.style == style:
            return FONTS_DIR / face.path
    raise KeyError(f"Schnitt {weight}/{style} fehlt fuer Schrift {key!r}")


@lru_cache(maxsize=None)
def _data_uri(relative_path: str) -> str:
    """Liest eine Schriftdatei einmal und liefert sie als `data:`-URI (gecacht)."""
    data = (FONTS_DIR / relative_path).read_bytes()
    return "data:font/ttf;base64," + base64.b64encode(data).decode("ascii")


def font_face_css(keys) -> str:
    """`@font-face`-Regeln fuer die uebergebenen Familien (unbekannte Schluessel ignoriert).

    Jede Familie erscheint hoechstens einmal, in Katalogreihenfolge, damit gleiche
    Eingaben byte-gleiches CSS ergeben (Vorschau-Cache).

    Args:
        keys: Iterable von Schriftprofil-Schluesseln, z. B. ``{"comic_neue"}``.

    Example:
        >>> font_face_css([]) == ""
        True
    """
    wanted = set(keys or ())
    rules = []
    for font in BUNDLED_FONTS:
        if font.key not in wanted:
            continue
        for face in font.faces:
            rules.append(
                "@font-face {\n"
                f"    font-family: '{font.family}';\n"
                f"    src: url('{_data_uri(face.path)}') format('truetype');\n"
                f"    font-style: {face.style};\n"
                f"    font-weight: {face.css_weight()};\n"
                "    font-display: block;\n"
                "}"
            )
    return "\n".join(rules)
