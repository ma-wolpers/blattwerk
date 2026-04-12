"""Optionen für die visuelle Blattgestaltung (Farbprofile inkl. S/W)."""

from __future__ import annotations

from dataclasses import dataclass


_COLOR_PROFILE_PRESETS = {
    "default": {
        "label": "Grau",
        "colors": {
            "primary_border": "#5A5A5A",
            "primary_bg": "#F4F4F4",
            "secondary_border": "#7A7A7A",
            "secondary_bg": "#ECECEC",
        },
    },
    "ocean": {
        "label": "Ocean",
        "colors": {
            "primary_border": "#2F7FAE",
            "primary_bg": "#E5F2FA",
            "secondary_border": "#2A9A8B",
            "secondary_bg": "#E3F7F3",
        },
    },
    "indigo": {
        "label": "Indigo",
        "colors": {
            "primary_border": "#4C5ED9",
            "primary_bg": "#EAF0FF",
            "secondary_border": "#A057B8",
            "secondary_bg": "#F7ECFB",
        },
    },
    "moss": {
        "label": "Moss",
        "colors": {
            "primary_border": "#3E8A68",
            "primary_bg": "#E7F3EC",
            "secondary_border": "#8E7B3F",
            "secondary_bg": "#F5F1E2",
        },
    },
    "terracotta": {
        "label": "Terracotta",
        "colors": {
            "primary_border": "#B45E47",
            "primary_bg": "#F9ECE8",
            "secondary_border": "#5F72B8",
            "secondary_bg": "#EAF0FB",
        },
    },
    "sunrise": {
        "label": "Sunrise",
        "colors": {
            "primary_border": "#B8842F",
            "primary_bg": "#FBF1DF",
            "secondary_border": "#C24D8F",
            "secondary_bg": "#FBE8F4",
        },
    },
    "lavender_graphite": {
        "label": "Lavender Graphite",
        "colors": {
            "primary_border": "#6E5BC7",
            "primary_bg": "#F1EEFF",
            "secondary_border": "#4F4A67",
            "secondary_bg": "#ECEAF6",
        },
    },
    "forest_moss": {
        "label": "Forest Moss",
        "colors": {
            "primary_border": "#3E7A5D",
            "primary_bg": "#EAF5EF",
            "secondary_border": "#567D45",
            "secondary_bg": "#ECF3E8",
        },
    },
    "obsidian_gold": {
        "label": "Obsidian Gold",
        "colors": {
            "primary_border": "#9E7C2F",
            "primary_bg": "#F8F1E1",
            "secondary_border": "#3C3741",
            "secondary_bg": "#DFDCE3",
        },
    },
    "bw": {
        "label": "S/W",
        "colors": {
            "primary_border": "#3E3E3E",
            "primary_bg": "#FFFFFF",
            "secondary_border": "#585858",
            "secondary_bg": "#F4F4F4",
        },
    },
}

COLOR_PROFILE_ORDER = list(_COLOR_PROFILE_PRESETS.keys())
COLOR_PROFILE_LABELS = {
    key: preset["label"] for key, preset in _COLOR_PROFILE_PRESETS.items()
}
DEFAULT_COLOR_PROFILE = "default"
CONTRAST_PROFILE_LABELS = {
    "standard": "Normal",
    "strong": "Hoch",
}
CONTRAST_PROFILE_ORDER = ["standard", "strong"]


_PROFILE_COLORS = {
    key: dict(preset["colors"]) for key, preset in _COLOR_PROFILE_PRESETS.items()
}


@dataclass(frozen=True)
class _SymbolStylePreset:
    """Bündelt Filter- und Konturstile für Aufgabensymbole."""

    symbol_filter: str
    text_stroke: str
    text_shadow: str


_SYMBOL_STYLE_PRESETS = {
    ("color", "standard"): _SymbolStylePreset(
        symbol_filter="brightness(0.94) contrast(1.12)",
        text_stroke="0 transparent",
        text_shadow="none",
    ),
    ("color", "strong"): _SymbolStylePreset(
        symbol_filter="brightness(0.84) contrast(1.4)",
        text_stroke="0 transparent",
        text_shadow="0.30px 0 0 #000000, -0.30px 0 0 #000000, 0 0.30px 0 #000000, 0 -0.30px 0 #000000",
    ),
    ("bw", "standard"): _SymbolStylePreset(
        symbol_filter="grayscale(1) brightness(0.75) contrast(5.1)",
        text_stroke="0.22px #000000",
        text_shadow="0.30px 0 0 #000000, -0.30px 0 0 #000000, 0 0.30px 0 #000000, 0 -0.30px 0 #000000",
    ),
    ("bw", "strong"): _SymbolStylePreset(
        symbol_filter="grayscale(1) brightness(0.75) contrast(8.4)",
        text_stroke="0.30px #000000",
        text_shadow="0.82px 0 0 #000000, -0.82px 0 0 #000000, 0 0.82px 0 #000000, 0 -0.82px 0 #000000",
    ),
}


def normalize_color_profile(value: str | None) -> str:
    """Normalisiert Profilnamen auf bekannte Farbprofile."""
    normalized = (value or "").strip().lower()
    if normalized in {"bw_theme", "bw"}:
        return "bw"
    if normalized in {"default", "standard"}:
        return "default"
    return normalized if normalized in _COLOR_PROFILE_PRESETS else DEFAULT_COLOR_PROFILE


def normalize_contrast_profile(value: str | None) -> str:
    """Normalisiert den Kontrastmodus auf `standard` oder `strong`."""
    return value if value in CONTRAST_PROFILE_LABELS else "standard"


def get_color_profile_preview(profile_key: str | None) -> dict:
    """Liefert Vorschau-/UI-Farben für ein Farbprofil."""
    profile = normalize_color_profile(profile_key)
    return _resolve_profile_colors(profile)


def _hex_to_rgb(hex_color: str):
    """Wandelt Hex-Farbwerte in RGB-Integer um."""
    color = (hex_color or "").strip().lstrip("#")
    if len(color) != 6:
        return (127, 127, 127)

    try:
        return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))
    except ValueError:
        return (127, 127, 127)


def _rgb_to_hex(red: int, green: int, blue: int):
    """Wandelt RGB-Integer in einen Hex-Farbwert um."""
    return f"#{red:02X}{green:02X}{blue:02X}"


def _mix_hex(base_hex: str, target_hex: str, ratio: float):
    """Mischt zwei Hex-Farben linear mit Verhältnis `ratio`."""
    ratio = max(0.0, min(1.0, ratio))
    base_r, base_g, base_b = _hex_to_rgb(base_hex)
    target_r, target_g, target_b = _hex_to_rgb(target_hex)
    out_r = round(base_r * (1.0 - ratio) + target_r * ratio)
    out_g = round(base_g * (1.0 - ratio) + target_g * ratio)
    out_b = round(base_b * (1.0 - ratio) + target_b * ratio)
    return _rgb_to_hex(out_r, out_g, out_b)


def _resolve_profile_colors(color_profile: str):
    """Löst finale Profilfarben auf (inkl. subtil grünlicher Lösungsnuance)."""

    profile_colors = dict(_PROFILE_COLORS[color_profile])
    primary_border = profile_colors["primary_border"]
    primary_bg = profile_colors["primary_bg"]
    secondary_border = profile_colors["secondary_border"]
    secondary_bg = profile_colors["secondary_bg"]

    if color_profile not in {"default", "bw"}:
        solution_border = _mix_hex(primary_border, "#4B9A6E", 0.36)
        solution_bg = _mix_hex(primary_bg, "#E7F7EC", 0.40)
    else:
        solution_border = _mix_hex(primary_border, "#4B4B4B", 0.20)
        solution_bg = _mix_hex(primary_bg, "#FFFFFF", 0.08)

    return {
        "info_border": primary_border,
        "info_bg": primary_bg,
        "secondary_border": secondary_border,
        "secondary_bg": secondary_bg,
        "solution_border": solution_border,
        "solution_bg": solution_bg,
    }


def _resolve_symbol_style(color_profile: str, contrast_profile: str):
    """Liefert Filter + Kontur für Aufgabensymbole aus zentralen Presets."""

    if color_profile == "bw":
        mode_key = "bw"
    else:
        mode_key = "color"

    return _SYMBOL_STYLE_PRESETS[(mode_key, contrast_profile)]


def build_design_css(
    color_profile: str = DEFAULT_COLOR_PROFILE,
    contrast_profile: str = "standard",
):
    """Erzeugt CSS-Overrides für Arbeitsblatt-Gestaltung."""

    color_profile = normalize_color_profile(color_profile)
    contrast_profile = normalize_contrast_profile(contrast_profile)
    profile_colors = _resolve_profile_colors(color_profile)

    accent_main = profile_colors["info_border"]
    accent_secondary = profile_colors["secondary_border"]
    accent_secondary_soft = profile_colors["secondary_bg"]
    accent_soft = _mix_hex(profile_colors["info_bg"], "#FFFFFF", 0.22)
    accent_strong = _mix_hex(accent_main, "#1E1E1E", 0.28)
    meta_color = _mix_hex(accent_main, "#6A6A6A", 0.56)
    line_color = _mix_hex(accent_main, "#6E6E6E", 0.52)
    material_border = _mix_hex(accent_secondary, "#7A7A7A", 0.28)
    material_bg = _mix_hex(accent_secondary_soft, "#FFFFFF", 0.10)
    heading_underline = _mix_hex(accent_main, "#A0A0A0", 0.30)
    task_chip_bg = _mix_hex(profile_colors["info_bg"], accent_secondary, 0.12)
    solution_accent_strong = _mix_hex(
        profile_colors["solution_border"], "#205840", 0.25
    )
    solution_accent_soft = _mix_hex(profile_colors["solution_bg"], "#FFFFFF", 0.15)

    warning_border = "#B35B5B" if color_profile not in {"default", "bw"} else "#5A5A5A"
    note_border = _mix_hex(profile_colors["info_border"], "#666666", 0.35)
    bw_mode = color_profile == "bw"
    symbol_style = _resolve_symbol_style(color_profile, contrast_profile)

    if bw_mode:
        if contrast_profile == "strong":
            image_filter = "grayscale(1) brightness(0.76) contrast(2.35)"
        else:
            image_filter = "grayscale(1) contrast(1.35)"
    else:
        if contrast_profile == "strong":
            image_filter = "brightness(0.76) contrast(1.85) saturate(0.92)"
        else:
            image_filter = "none"

    bw_overrides = ""
    if bw_mode:
        bw_overrides = """
h1 {
    border-bottom: 1px solid #5A5A5A;
}

.material,
.info,
.solution,
.solution-version {
    background: #FFFFFF;
}

.task-header-left,
.task-points {
    background: transparent;
    padding: 0;
    border-radius: 0;
}
"""

    return f"""
:root {{
    --theme-accent-main: {accent_main};
    --theme-accent-secondary: {accent_secondary};
    --theme-accent-secondary-soft: {accent_secondary_soft};
    --theme-accent-soft: {accent_soft};
    --theme-accent-strong: {accent_strong};
    --theme-meta-color: {meta_color};
    --theme-line-color: {line_color};
    --theme-material-border: {material_border};
    --theme-material-bg: {material_bg};
    --theme-heading-underline: {heading_underline};
    --theme-task-chip-bg: {task_chip_bg};
    --solution-accent-strong: {solution_accent_strong};
    --solution-accent-soft: {solution_accent_soft};
    --info-border-color: {profile_colors["info_border"]};
    --info-bg-color: {profile_colors["info_bg"]};
    --info-warning-border-color: {warning_border};
    --info-note-border-color: {note_border};
    --solution-border-color: {profile_colors["solution_border"]};
    --solution-bg-color: {profile_colors["solution_bg"]};
}}

.info {{
    border-left-color: var(--info-border-color);
    background: var(--info-bg-color);
}}

.info.warning {{
    border-left-color: var(--info-warning-border-color);
}}

.info.note {{
    border-left-color: var(--info-note-border-color);
}}

.document-header,
.header-meta {{
    color: var(--theme-meta-color);
}}

h1 {{
    color: #111111;
    border-bottom: 2px solid #111111;
    padding-bottom: 0.12cm;
}}

.student-line {{
    border-bottom-color: var(--theme-line-color);
}}

.material {{
    border-color: var(--theme-material-border);
    background: var(--theme-material-bg);
}}

.material h3 {{
    color: var(--theme-accent-secondary);
}}

.task-header-left,
.task-points {{
    color: #111111;
    background: transparent;
    padding: 0;
    border-radius: 0;
}}

.task-work-hint {{
    color: var(--theme-meta-color);
}}

.task-work-symbol {{
    filter: {symbol_style.symbol_filter};
    -webkit-text-stroke: {symbol_style.text_stroke};
    text-shadow: {symbol_style.text_shadow};
}}

img {{
    filter: {image_filter};
}}

.solution-version,
.solution-version-inline {{
    border-color: var(--solution-accent-strong);
    color: var(--solution-accent-strong);
    background: var(--solution-accent-soft);
}}

.solution {{
    border-color: var(--solution-border-color);
    background: var(--solution-bg-color);
}}

.solution-label {{
    color: var(--solution-accent-strong);
}}

{bw_overrides}
"""
