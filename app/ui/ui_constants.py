"""Zentrale UI-Konstanten für die Blattwerk-Vorschau.

Dieses Modul bündelt anpassbare Werte für:
- Zoom-/Skalierungsgrenzen
- Ansichtsmodi (Fit + Layout)
- Seitenabstände in Mehrseitenansichten

Änderungen hier wirken direkt auf `blatt_ui.py`.
"""

PREVIEW_CANVAS_PADDING_PX = 16
PREVIEW_MIN_FRAME_PX = 220
PREVIEW_ZOOM_MIN_PERCENT = 10
PREVIEW_ZOOM_MAX_PERCENT = 240
PREVIEW_SCALE_MIN = 0.05
PREVIEW_SCALE_MAX = 3.0

VIEW_FIT_WIDTH = "fit_width"
VIEW_FIT_PAGE = "fit_page"

VIEW_MODE_LABELS = {
    VIEW_FIT_WIDTH: "Seitenbreite",
    VIEW_FIT_PAGE: "Ganze Seite",
}

VIEW_LAYOUT_SINGLE = "single"
VIEW_LAYOUT_STRIP = "strip"
VIEW_LAYOUT_STACK = "stack"

EDITOR_VIEW_PREVIEW_ONLY = "preview_only"
EDITOR_VIEW_BOTH = "both"
EDITOR_VIEW_EDITOR_ONLY = "editor_only"

EDITOR_VIEW_MODE_LABELS = {
    EDITOR_VIEW_PREVIEW_ONLY: "Nur Vorschau",
    EDITOR_VIEW_BOTH: "Beides",
    EDITOR_VIEW_EDITOR_ONLY: "Nur Schreibbereich",
}

PREVIEW_PAGE_GAP_PX = 28
PREVIEW_PAGE_MARGIN_PX = 20

CUSTOM_FIT_MODE = "__custom__"
