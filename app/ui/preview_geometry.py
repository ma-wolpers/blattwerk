"""Geometrie- und Zoom-Helfer für die Blattwerk-Vorschau.

Dieses Modul ist absichtlich UI-neutral:
- keine Tk-Widgets als Pflicht
- reine Berechnungsfunktionen

Ziel: Vorschauverhalten (Zoom, Zentrierung, aktive Seite) getrennt
vom GUI-Eventcode wartbar machen.
"""

from __future__ import annotations


def clamp(value, lower, upper):
    """Begrenzt einen numerischen Wert auf [lower, upper]."""
    return max(lower, min(value, upper))


def get_preview_frame_size(canvas_width, canvas_height, padding_px, min_frame_px):
    """Berechnet die nutzbare Vorschaufläche mit Mindestgröße."""
    frame_width = max(min_frame_px, canvas_width - padding_px)
    frame_height = max(min_frame_px, canvas_height - padding_px)
    return frame_width, frame_height


def get_fit_scales(frame_width, frame_height, source_width, source_height):
    """Liefert Fit-Skalierungen für Seitenbreite und ganze Seite."""
    width_fit_scale = frame_width / source_width
    page_fit_scale = min(frame_width / source_width, frame_height / source_height)
    return width_fit_scale, page_fit_scale


def get_zoom_target_size(
    source_width, source_height, width_fit_scale, zoom_percent, scale_min, scale_max
):
    """Berechnet Zielgröße bei seitenbreitenbasiertem Zoom."""
    scale = width_fit_scale * (zoom_percent / 100.0)
    scale = clamp(scale, scale_min, scale_max)
    return max(1, int(source_width * scale)), max(1, int(source_height * scale))


def parse_scrollregion(scrollregion_text):
    """Parst Scrollregion robust als Float-Tupel."""
    raw = scrollregion_text or "0 0 0 0"
    try:
        x0, y0, x1, y1 = (float(part) for part in raw.split())
        return x0, y0, x1, y1
    except Exception:
        return 0.0, 0.0, 0.0, 0.0


def get_centered_view_fractions(page_box, canvas_width, canvas_height, scroll_bounds):
    """Berechnet x/y-View-Fraktionen, um eine Seite im Viewport zu zentrieren."""
    x0, y0, x1, y1 = page_box
    page_center_x = (x0 + x1) / 2
    page_center_y = (y0 + y1) / 2

    scroll_x0, scroll_y0, scroll_x1, scroll_y1 = scroll_bounds
    scroll_width = max(1.0, scroll_x1 - scroll_x0)
    scroll_height = max(1.0, scroll_y1 - scroll_y0)

    max_scroll_x = max(0.0, scroll_width - canvas_width)
    max_scroll_y = max(0.0, scroll_height - canvas_height)

    target_x = max(0.0, min(page_center_x - canvas_width / 2, max_scroll_x))
    target_y = max(0.0, min(page_center_y - canvas_height / 2, max_scroll_y))

    x_fraction = 0.0 if max_scroll_x <= 0 else target_x / scroll_width
    y_fraction = 0.0 if max_scroll_y <= 0 else target_y / scroll_height
    return x_fraction, y_fraction


def find_active_page_index(
    layout_mode, page_layout_boxes, viewport_center_x, viewport_center_y, current_index
):
    """Bestimmt die aktive Seite anhand des Viewport-Zentrums."""
    if not page_layout_boxes:
        return current_index

    best_index = current_index
    best_distance = float("inf")

    for index, (x0, y0, x1, y1) in enumerate(page_layout_boxes):
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2

        if layout_mode == "strip":
            distance = abs(center_x - viewport_center_x)
        else:
            distance = abs(center_y - viewport_center_y)

        if distance < best_distance:
            best_distance = distance
            best_index = index

    return best_index
