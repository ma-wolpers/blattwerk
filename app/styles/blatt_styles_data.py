"""Kataloge fuer Blattwerk-Styles: Druckprofile, Schrift- und Groessenprofile, Seitenlayouts.

Reine Daten. Die CSS-Erzeugung und alle Aufloesungsfunktionen leben in `blatt_styles.py`,
das diese Namen re-exportiert (bestehende Importe bleiben gueltig).
"""

# line-limit: data-only
from __future__ import annotations


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
    # "label": shown in the font picker (Teil 4).
    # "css_family": full CSS fallback stack, used for export CSS generation only.
    # "tk_family": one real font name, used for the on-screen live preview
    #   (Teil 4) -- Tk silently falls back to a default font if not installed.
    "segoe": {
        "label": "Segoe UI",
        "css_family": "'Segoe UI', 'Arial', sans-serif",
        "tk_family": "Segoe UI",
    },
    "calibri": {
        "label": "Calibri",
        "css_family": "Calibri, 'Segoe UI', Arial, sans-serif",
        "tk_family": "Calibri",
    },
    "arial": {
        "label": "Arial",
        "css_family": "Arial, 'Helvetica Neue', Helvetica, sans-serif",
        "tk_family": "Arial",
    },
    "verdana": {
        "label": "Verdana",
        "css_family": "Verdana, 'Segoe UI', Arial, sans-serif",
        "tk_family": "Verdana",
    },
    "tahoma": {
        "label": "Tahoma",
        "css_family": "Tahoma, 'Segoe UI', Arial, sans-serif",
        "tk_family": "Tahoma",
    },
    "times_new_roman": {
        "label": "Times New Roman",
        "css_family": "'Times New Roman', Times, serif",
        "tk_family": "Times New Roman",
    },
    "georgia": {
        "label": "Georgia",
        "css_family": "Georgia, 'Times New Roman', serif",
        "tk_family": "Georgia",
    },
    "cambria": {
        "label": "Cambria",
        "css_family": "Cambria, Georgia, serif",
        "tk_family": "Cambria",
    },
    "garamond": {
        "label": "Garamond",
        "css_family": "Garamond, 'Times New Roman', serif",
        "tk_family": "Garamond",
    },
    "book_antiqua": {
        "label": "Book Antiqua",
        "css_family": "'Book Antiqua', 'Palatino Linotype', serif",
        "tk_family": "Book Antiqua",
    },
    "constantia": {
        "label": "Constantia",
        "css_family": "Constantia, Georgia, serif",
        "tk_family": "Constantia",
    },
    "century_gothic": {
        "label": "Century Gothic",
        "css_family": "'Century Gothic', 'Segoe UI', sans-serif",
        "tk_family": "Century Gothic",
    },
    "trebuchet_ms": {
        "label": "Trebuchet MS",
        "css_family": "'Trebuchet MS', 'Segoe UI', sans-serif",
        "tk_family": "Trebuchet MS",
    },
    "comic_sans_ms": {
        "label": "Comic Sans MS",
        "css_family": "'Comic Sans MS', 'Comic Sans', sans-serif",
        "tk_family": "Comic Sans MS",
    },
    "bahnschrift": {
        "label": "Bahnschrift",
        "css_family": "Bahnschrift, 'Segoe UI', sans-serif",
        "tk_family": "Bahnschrift",
    },
    "corbel": {
        "label": "Corbel",
        "css_family": "Corbel, 'Segoe UI', sans-serif",
        "tk_family": "Corbel",
    },
    "candara": {
        "label": "Candara",
        "css_family": "Candara, 'Segoe UI', sans-serif",
        "tk_family": "Candara",
    },
    "franklin_gothic_medium": {
        "label": "Franklin Gothic Medium",
        "css_family": "'Franklin Gothic Medium', 'Arial Narrow', Arial, sans-serif",
        "tk_family": "Franklin Gothic Medium",
    },
    "lucida_sans": {
        "label": "Lucida Sans",
        "css_family": "'Lucida Sans', 'Lucida Sans Unicode', Verdana, sans-serif",
        "tk_family": "Lucida Sans",
    },
    "rockwell": {
        "label": "Rockwell",
        "css_family": "Rockwell, Georgia, serif",
        "tk_family": "Rockwell",
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
        "presentation_font_size_base": "12pt",
        "box_buffer_inline": "0.15cm",
        "box_buffer_block": "0.10cm",
        "box_radius": "0.14em",
    },
    "normal": {
        "label": "Normal",
        "font_size_base": "11pt",
        "presentation_font_size_base": "16pt",
        "box_buffer_inline": "0.20cm",
        "box_buffer_block": "0.13cm",
        "box_radius": "0.18em",
    },
    "large": {
        "label": "Groß",
        "font_size_base": "12.5pt",
        "presentation_font_size_base": "20pt",
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
    "a6_portrait": {
        "page_size_css": "10.5cm 14.8cm",
        "page_margin_top_css": "0.5cm",
        "page_margin_right_css": "0.4cm",
        "page_margin_bottom_css": "0.4cm",
        "page_margin_left_css": "0.4cm",
        "page_margin_right_hole_punch_css": "0.4cm",
        "page_margin_left_hole_punch_css": "0.4cm",
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
