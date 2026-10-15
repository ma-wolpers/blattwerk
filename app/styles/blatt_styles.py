"""Styles und Druckprofile für Blattwerk.

Dieses Modul kapselt:
- Druckprofile (standard/strong)
- CSS-Variablenaufbau je Profil
- Laden der externen CSS-Basisdatei und Ergänzen von Overrides
- Farbaufbereitung für PDF-Laufelemente

Die Kataloge (Profile, `PAGE_LAYOUTS`) liegen in `blatt_styles_data.py` und werden
hier re-exportiert.
"""

from __future__ import annotations

from pathlib import Path
import re

from .page_geometry import build_gutter_css
from .worksheet_design import build_design_css
from .bundled_fonts import font_face_css
from .blatt_styles_data import (
    PRINT_PROFILE_PRESETS,
    PRINT_PROFILE_ALIASES,
    FONT_PROFILE_PRESETS,
    FONT_PROFILE_ORDER,
    FONT_PROFILE_LABELS,
    DEFAULT_FONT_PROFILE,
    FONT_SIZE_PROFILE_PRESETS,
    FONT_SIZE_PROFILE_ORDER,
    FONT_SIZE_PROFILE_LABELS,
    DEFAULT_FONT_SIZE_PROFILE,
    PAGE_LAYOUTS,
    WORKSHEET_PAGE_FORMATS,
    WORKSHEET_PAGE_FORMAT_LABELS,
    DEFAULT_WORKSHEET_PAGE_FORMAT,
    PRESENTATION_PAGE_FORMATS,
    DEFAULT_PRESENTATION_PAGE_FORMAT,
    _PAGE_DIMENSIONS_CM,
)


STYLESHEET_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "worksheet.css"
)


_cached_stylesheet_template = None


def invalidate_stylesheet_template_cache():
    """Verwirft die zwischengespeicherte CSS-Basisvorlage."""
    global _cached_stylesheet_template
    _cached_stylesheet_template = None


def _normalize_keyword(value, default=""):
    """Normalisiert optionale Schlüsselwörter für Lookups."""
    return (value or default).strip().lower()


def normalize_font_profile(value):
    """Normalisiert die Schriftauswahl auf bekannte Profile."""
    normalized = _normalize_keyword(value, default=DEFAULT_FONT_PROFILE)
    return normalized if normalized in FONT_PROFILE_PRESETS else DEFAULT_FONT_PROFILE


def normalize_font_size_profile(value):
    """Normalisiert die Schriftgröße auf bekannte Presets."""
    normalized = _normalize_keyword(value, default=DEFAULT_FONT_SIZE_PROFILE)
    return (
        normalized
        if normalized in FONT_SIZE_PROFILE_PRESETS
        else DEFAULT_FONT_SIZE_PROFILE
    )


def resolve_print_profile(profile_name):
    """Liefert ein bekanntes Druckprofil (standard/strong)."""
    normalized = _normalize_keyword(profile_name, default="standard")
    canonical_name = PRINT_PROFILE_ALIASES.get(normalized, "standard")
    return dict(PRINT_PROFILE_PRESETS[canonical_name])


def build_print_profile_css(profile_name):
    """Erzeugt CSS-Variablen für druckbezogene Kontrast-/Stärkeanpassungen."""
    profile = resolve_print_profile(profile_name)
    return f"""
:root {{
    --text-color: {profile["text_color"]};
    --header-color: {profile["header_color"]};
    --task-hint-color: {profile["task_hint_color"]};
    --footer-color: {profile["footer_color"]};
    --running-title-color: {profile["running_title_color"]};
    --field-border-color: {profile["field_border_color"]};
    --field-border-width: {profile["field_border_width"]};
    --material-border-width: {profile["material_border_width"]};
    --material-border-color: {profile["material_border_color"]};
    --grid-line-color: {profile["grid_color"]};
    --grid-line-stroke: {profile["grid_stroke"]};
    --grid-border-width: {profile["grid_border_width"]};
    --grid-border-color: {profile["grid_border_color"]};
    --dot-border-color: {profile["dot_border_color"]};
    --dot-color: {profile["dot_color"]};
    --dot-radius: {profile["dot_radius"]};
    --dot-spacing: {profile["dot_step"]};
}}
"""


def build_font_profile_css(font_profile):
    """Erzeugt CSS-Variablen für das gewählte Schriftprofil.

    Ist das Profil eine mitgelieferte Schrift (`bundled_fonts.py`), werden deren
    `@font-face`-Regeln mit eingebettet -- nur für dieses eine Profil, damit nicht
    alle Schriftdateien in jedem Dokument landen.
    """
    profile_key = normalize_font_profile(font_profile)
    profile = FONT_PROFILE_PRESETS[profile_key]
    font_faces = font_face_css([profile_key])
    return f"""
{font_faces}
:root {{
    --font-family-base: {profile["css_family"]};
}}
"""


def build_font_size_profile_css(font_size_profile, slide_layout=False):
    """Erzeugt CSS-Variablen für Schriftgröße und Antwortbox-Puffer."""
    profile_key = normalize_font_size_profile(font_size_profile)
    profile = FONT_SIZE_PROFILE_PRESETS[profile_key]
    is_presentation = bool(slide_layout)
    font_size_base = (
        profile.get("presentation_font_size_base", profile["font_size_base"])
        if is_presentation
        else profile["font_size_base"]
    )
    return f"""
:root {{
    --font-size-base: {font_size_base};
    --box-buffer-inline: {profile["box_buffer_inline"]};
    --box-buffer-block: {profile["box_buffer_block"]};
    --box-radius: {profile["box_radius"]};
}}
"""


def build_page_layout_css(page_format, hole_punch_enabled=False, slide_layout=False):
    """Erzeugt CSS für das gewählte Seitenlayout."""
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    if slide_layout:
        margin_css = "0"
    else:
        if hole_punch_enabled:
            margin_right = layout.get(
                "page_margin_right_hole_punch_css", layout["page_margin_right_css"]
            )
            margin_left = layout.get(
                "page_margin_left_hole_punch_css", layout["page_margin_left_css"]
            )
        else:
            margin_right = layout["page_margin_right_css"]
            margin_left = layout["page_margin_left_css"]
        margin_css = (
            f"{layout['page_margin_top_css']} {margin_right} "
            f"{layout['page_margin_bottom_css']} {margin_left}"
        )

    return f"""
@page {{
    size: {layout["page_size_css"]};
    margin: {margin_css};
}}

:root {{
    --document-header-size: {layout["document_header_size"]};
    --solution-badge-size: {layout["solution_badge_size"]};
}}
"""


def _css_length_to_cm(raw_value, default_cm):
    """Convert a simple CSS length (`cm|mm|px|pt`) to centimeters."""
    text = str(raw_value or "").strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(cm|mm|px|pt)", text)
    if not match:
        return default_cm

    value = float(match.group(1))
    unit = match.group(2)
    if unit == "cm":
        return value
    if unit == "mm":
        return value / 10.0
    if unit == "px":
        return value * (2.54 / 96.0)
    if unit == "pt":
        return value * (2.54 / 72.0)
    return default_cm


def _layout_page_width_cm(layout):
    """Resolve physical page width in centimeters from a layout preset."""
    size_text = str((layout or {}).get("page_size_css", "A4 portrait") or "").strip().lower()

    custom_size_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)cm\s+(\d+(?:\.\d+)?)cm",
        size_text,
    )
    if custom_size_match:
        width = float(custom_size_match.group(1))
        return width

    parts = [part for part in size_text.split() if part]
    paper_key = parts[0] if parts else "a4"
    paper_dimensions = _PAGE_DIMENSIONS_CM.get(paper_key, _PAGE_DIMENSIONS_CM["a4"])

    if "landscape" in parts:
        return max(paper_dimensions)
    return min(paper_dimensions)


def resolve_page_side_margins_cm(page_format, hole_punch_enabled=False):
    """Liefert `(links_cm, rechts_cm)` der aktiven `@page`-Seitenränder."""
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])

    if hole_punch_enabled:
        margin_left_raw = layout.get(
            "page_margin_left_hole_punch_css", layout["page_margin_left_css"]
        )
        margin_right_raw = layout.get(
            "page_margin_right_hole_punch_css", layout["page_margin_right_css"]
        )
    else:
        margin_left_raw = layout["page_margin_left_css"]
        margin_right_raw = layout["page_margin_right_css"]

    return _css_length_to_cm(margin_left_raw, 1.5), _css_length_to_cm(margin_right_raw, 1.5)


def resolve_printable_width_cm(page_format, hole_punch_enabled=False):
    """Resolve printable content width from page format and active margins."""
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    page_width_cm = _layout_page_width_cm(layout)
    margin_left_cm, margin_right_cm = resolve_page_side_margins_cm(page_format, hole_punch_enabled)
    return max(0.5, page_width_cm - margin_left_cm - margin_right_cm)


def _layout_page_height_cm(layout):
    """Resolve physical page height in centimeters from a layout preset.

    Mirrors `_layout_page_width_cm` exactly, but picks the *other* paper
    dimension: landscape's height is the shorter side, portrait's height
    is the longer side (the reverse of width's landscape/portrait pick).
    """
    size_text = str((layout or {}).get("page_size_css", "A4 portrait") or "").strip().lower()

    custom_size_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)cm\s+(\d+(?:\.\d+)?)cm",
        size_text,
    )
    if custom_size_match:
        return float(custom_size_match.group(2))

    parts = [part for part in size_text.split() if part]
    paper_key = parts[0] if parts else "a4"
    paper_dimensions = _PAGE_DIMENSIONS_CM.get(paper_key, _PAGE_DIMENSIONS_CM["a4"])

    if "landscape" in parts:
        return min(paper_dimensions)
    return max(paper_dimensions)


def resolve_printable_height_cm(page_format, hole_punch_enabled=False):
    """Resolve printable content height from page format and active margins.

    `hole_punch_enabled` is accepted for signature symmetry with
    `resolve_printable_width_cm` but has no effect here: `PAGE_LAYOUTS`
    only defines hole-punch margin overrides for the left/right (binding)
    margins, never for top/bottom -- this mirrors that intentionally,
    it isn't an oversight.
    """
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    page_height_cm = _layout_page_height_cm(layout)

    margin_top_cm = _css_length_to_cm(layout["page_margin_top_css"], 1.5)
    margin_bottom_cm = _css_length_to_cm(layout["page_margin_bottom_css"], 1.5)
    return max(0.5, page_height_cm - margin_top_cm - margin_bottom_cm)


def _load_stylesheet_template_text():
    """Lädt die CSS-Vorlage einmalig von der Datei."""
    global _cached_stylesheet_template
    if _cached_stylesheet_template is not None:
        return _cached_stylesheet_template

    if not STYLESHEET_TEMPLATE_PATH.exists():
        raise RuntimeError(f"CSS-Vorlage fehlt: {STYLESHEET_TEMPLATE_PATH}")

    _cached_stylesheet_template = STYLESHEET_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _cached_stylesheet_template


def build_stylesheet(
    page_format,
    print_profile,
    hole_punch_enabled=False,
    color_profile="indigo",
    font_profile=DEFAULT_FONT_PROFILE,
    font_size_profile=DEFAULT_FONT_SIZE_PROFILE,
    slide_layout=False,
    reserve_gutters=False,
    has_word_notes=False,
):
    """Erzeugt das finale Stylesheet aus Basis-CSS + dynamischen Overrides.

    `reserve_gutters` reserviert die Randspalten (siehe `page_geometry.py`);
    nur das Arbeitsblatt setzt es. `has_word_notes` ergänzt die rechte Spalte
    für Worterklärungen.
    """
    base_stylesheet = _load_stylesheet_template_text().strip()
    overrides = "\n\n".join(
        [
            build_page_layout_css(
                page_format,
                hole_punch_enabled=hole_punch_enabled,
                slide_layout=slide_layout,
            ).strip(),
            build_print_profile_css(print_profile).strip(),
            build_font_profile_css(font_profile).strip(),
            build_font_size_profile_css(font_size_profile, slide_layout=slide_layout).strip(),
            build_design_css(
                color_profile=color_profile, contrast_profile=print_profile
            ).strip(),
            build_gutter_css(reserve_gutters, has_word_notes).strip(),
        ]
    )
    return f"{base_stylesheet}\n\n{overrides}\n"


def _hex_to_rgb_tuple(hex_color):
    """Wandelt Hex-Farben in normierte RGB-Tupel (0..1) um."""
    color = (hex_color or "").strip().lstrip("#")
    if len(color) != 6:
        return (0.5, 0.5, 0.5)
    try:
        red = int(color[0:2], 16) / 255
        green = int(color[2:4], 16) / 255
        blue = int(color[4:6], 16) / 255
        return (red, green, blue)
    except ValueError:
        return (0.5, 0.5, 0.5)


def resolve_pdf_running_colors(print_profile):
    """Liefert Farben für PDF-Laufelemente je Druckprofil."""
    profile = resolve_print_profile(print_profile)
    return {
        "footer_color": _hex_to_rgb_tuple(profile.get("footer_color")),
        "running_title_color": _hex_to_rgb_tuple(profile.get("running_title_color")),
    }
