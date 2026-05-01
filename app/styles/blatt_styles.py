"""Styles und Druckprofile für Blattwerk.

Dieses Modul kapselt:
- Druckprofile (standard/strong)
- CSS-Variablenaufbau je Profil
- Laden der externen CSS-Basisdatei und Ergänzen von Overrides
- Farbaufbereitung für PDF-Laufelemente
"""

from __future__ import annotations

from pathlib import Path
import re

from .worksheet_design import build_design_css


PRINT_PROFILE_PRESETS = {
    "standard": {
        "text_color": "#111",
        "header_color": "#777",
        "task_hint_color": "#a0a0a0",
        "footer_color": "#888888",
        "running_title_color": "#515151",
        "field_border_color": "#000",
        "field_border_width": "1px",
        "material_border_width": "1px",
        "material_border_color": "#b8b8b8",
        "grid_color": "rgba(80, 80, 80, 0.45)",
        "grid_stroke": "1px",
        "grid_border_width": "1px",
        "grid_border_color": "#000",
        "dot_border_color": "#999",
        "dot_color": "#999",
        "dot_radius": "0.5px",
        "dot_step": "0.5cm",
    },
    "strong": {
        "text_color": "#000",
        "header_color": "#5a5a5a",
        "task_hint_color": "#666",
        "footer_color": "#888888",
        "running_title_color": "#515151",
        "field_border_color": "#000",
        "field_border_width": "1.6px",
        "material_border_width": "1.3px",
        "material_border_color": "#878787",
        "grid_color": "rgba(35, 35, 35, 0.72)",
        "grid_stroke": "1.35px",
        "grid_border_width": "1.6px",
        "grid_border_color": "#000",
        "dot_border_color": "#565656",
        "dot_color": "#4f4f4f",
        "dot_radius": "1.05px",
        "dot_step": "0.46cm",
    },
}


PRINT_PROFILE_ALIASES = {
    "default": "standard",
    "normal": "standard",
    "standard": "standard",
    "stark": "strong",
    "strong": "strong",
    "printer_weak": "strong",
    "max": "strong",
    "maximal": "strong",
}


FONT_PROFILE_PRESETS = {
    "segoe": {
        "label": "Segoe UI",
        "font_family": "'Segoe UI', 'Arial', sans-serif",
    },
    "calibri": {
        "label": "Calibri",
        "font_family": "Calibri, 'Segoe UI', Arial, sans-serif",
    },
    "arial": {
        "label": "Arial",
        "font_family": "Arial, 'Helvetica Neue', Helvetica, sans-serif",
    },
    "verdana": {
        "label": "Verdana",
        "font_family": "Verdana, 'Segoe UI', Arial, sans-serif",
    },
    "tahoma": {
        "label": "Tahoma",
        "font_family": "Tahoma, 'Segoe UI', Arial, sans-serif",
    },
}

FONT_PROFILE_ORDER = list(FONT_PROFILE_PRESETS.keys())
FONT_PROFILE_LABELS = {
    key: value["label"] for key, value in FONT_PROFILE_PRESETS.items()
}
DEFAULT_FONT_PROFILE = "segoe"


FONT_SIZE_PROFILE_PRESETS = {
    "small": {
        "label": "Klein",
        "font_size_base": "10pt",
        "box_buffer_inline": "0.15cm",
        "box_buffer_block": "0.10cm",
        "box_radius": "0.14em",
    },
    "normal": {
        "label": "Normal",
        "font_size_base": "11pt",
        "box_buffer_inline": "0.20cm",
        "box_buffer_block": "0.13cm",
        "box_radius": "0.18em",
    },
    "large": {
        "label": "Groß",
        "font_size_base": "12.5pt",
        "box_buffer_inline": "0.26cm",
        "box_buffer_block": "0.17cm",
        "box_radius": "0.24em",
    },
}

FONT_SIZE_PROFILE_ORDER = list(FONT_SIZE_PROFILE_PRESETS.keys())
FONT_SIZE_PROFILE_LABELS = {
    key: value["label"] for key, value in FONT_SIZE_PROFILE_PRESETS.items()
}
DEFAULT_FONT_SIZE_PROFILE = "normal"


PAGE_LAYOUTS = {
    "a4_portrait": {
        "page_size_css": "A4 portrait",
        "page_margin_top_css": "2.0cm",
        "page_margin_right_css": "1.5cm",
        "page_margin_bottom_css": "1.5cm",
        "page_margin_left_css": "1.5cm",
        "page_margin_right_hole_punch_css": "0.9cm",
        "page_margin_left_hole_punch_css": "2.3cm",
        "document_header_size": "0.78em",
        "solution_badge_size": "0.84em",
    },
    "a5_landscape": {
        "page_size_css": "A5 landscape",
        "page_margin_top_css": "1.1cm",
        "page_margin_right_css": "0.6cm",
        "page_margin_bottom_css": "0.6cm",
        "page_margin_left_css": "0.6cm",
        "page_margin_right_hole_punch_css": "0.4cm",
        "page_margin_left_hole_punch_css": "1.3cm",
        "document_header_size": "0.85em",
        "solution_badge_size": "0.9em",
    },
    "presentation_16_9": {
        "page_size_css": "33.867cm 19.05cm",
        "page_margin_top_css": "1.0cm",
        "page_margin_right_css": "1.0cm",
        "page_margin_bottom_css": "1.0cm",
        "page_margin_left_css": "1.0cm",
        "page_margin_right_hole_punch_css": "1.0cm",
        "page_margin_left_hole_punch_css": "1.0cm",
        "document_header_size": "0.78em",
        "solution_badge_size": "0.84em",
    },
    "presentation_16_10": {
        "page_size_css": "30.48cm 19.05cm",
        "page_margin_top_css": "1.0cm",
        "page_margin_right_css": "1.0cm",
        "page_margin_bottom_css": "1.0cm",
        "page_margin_left_css": "1.0cm",
        "page_margin_right_hole_punch_css": "1.0cm",
        "page_margin_left_hole_punch_css": "1.0cm",
        "document_header_size": "0.78em",
        "solution_badge_size": "0.84em",
    },
    "presentation_4_3": {
        "page_size_css": "25.4cm 19.05cm",
        "page_margin_top_css": "1.0cm",
        "page_margin_right_css": "1.0cm",
        "page_margin_bottom_css": "1.0cm",
        "page_margin_left_css": "1.0cm",
        "page_margin_right_hole_punch_css": "1.0cm",
        "page_margin_left_hole_punch_css": "1.0cm",
        "document_header_size": "0.78em",
        "solution_badge_size": "0.84em",
    },
}


_PAGE_DIMENSIONS_CM = {
    "a4": (21.0, 29.7),
    "a5": (14.8, 21.0),
}


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
    """Erzeugt CSS-Variablen für das gewählte Schriftprofil."""
    profile_key = normalize_font_profile(font_profile)
    profile = FONT_PROFILE_PRESETS[profile_key]
    return f"""
:root {{
    --font-family-base: {profile["font_family"]};
}}
"""


def build_font_size_profile_css(font_size_profile):
    """Erzeugt CSS-Variablen für Schriftgröße und Antwortbox-Puffer."""
    profile_key = normalize_font_size_profile(font_size_profile)
    profile = FONT_SIZE_PROFILE_PRESETS[profile_key]
    return f"""
:root {{
    --font-size-base: {profile["font_size_base"]};
    --box-buffer-inline: {profile["box_buffer_inline"]};
    --box-buffer-block: {profile["box_buffer_block"]};
    --box-radius: {profile["box_radius"]};
}}
"""


def build_page_layout_css(page_format, hole_punch_enabled=False, document_mode="worksheet"):
    """Erzeugt CSS für das gewählte Seitenlayout."""
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    if str(document_mode or "").strip().lower() == "presentation":
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


def resolve_printable_width_cm(page_format, hole_punch_enabled=False):
    """Resolve printable content width from page format and active margins."""
    layout = PAGE_LAYOUTS.get(page_format, PAGE_LAYOUTS["a4_portrait"])
    page_width_cm = _layout_page_width_cm(layout)

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

    margin_left_cm = _css_length_to_cm(margin_left_raw, 1.5)
    margin_right_cm = _css_length_to_cm(margin_right_raw, 1.5)
    return max(0.5, page_width_cm - margin_left_cm - margin_right_cm)


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
    document_mode="worksheet",
):
    """Erzeugt das finale Stylesheet aus Basis-CSS + dynamischen Overrides."""
    base_stylesheet = _load_stylesheet_template_text().strip()
    overrides = "\n\n".join(
        [
            build_page_layout_css(
                page_format,
                hole_punch_enabled=hole_punch_enabled,
                document_mode=document_mode,
            ).strip(),
            build_print_profile_css(print_profile).strip(),
            build_font_profile_css(font_profile).strip(),
            build_font_size_profile_css(font_size_profile).strip(),
            build_design_css(
                color_profile=color_profile, contrast_profile=print_profile
            ).strip(),
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
