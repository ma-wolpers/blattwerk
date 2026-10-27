"""Vorschau-Ansicht: Zoom-Anzeige, Einpassen (Seitenbreite/ganze Seite) und Seitenlayout.
"""

from __future__ import annotations

from PIL import Image
from .preview_geometry import clamp, get_fit_scales
from .ui_constants import (
    PREVIEW_ZOOM_MAX_PERCENT,
    PREVIEW_ZOOM_MIN_PERCENT,
    VIEW_FIT_WIDTH,
    VIEW_LAYOUT_SINGLE,
    VIEW_LAYOUT_STACK,
    VIEW_LAYOUT_STRIP,
    VIEW_MODE_LABELS,
)


class BlattwerkAppStyleViewMixin:
    """Steuert Einpassen, Zoom-Anzeige und Layout der Vorschau."""

    def _refresh_zoom_label(self):
            """Aktualisiert den Zoomtext (immer seitenbreitenbezogene Prozent)."""

            display_zoom_percent = self._get_display_zoom_percent()
            self.zoom_info_var.set(f"Zoom: {display_zoom_percent}%")

    def _get_fit_scales(self, image: Image.Image):
            """Berechnet Skalierung für Seitenbreite und ganze Seite -- bezogen auf die Referenzseite.

            Referenz ist die erste Vorschauseite (Arbeitsblattformat), nicht
            `image` selbst: Alle Seiten werden mit derselben Auflösung gerastert,
            ein gemeinsamer Faktor hält deshalb die echten Größenverhältnisse --
            eine angehängte A6-Lernhilfe erscheint kleiner als die A4-Seite
            (maßstabsgetreu). Bei gleich großen Seiten ist das Ergebnis dasselbe
            wie zuvor. Ohne Vorschauseiten gilt `image`.
            """

            reference = self.preview_images[0] if getattr(self, "preview_images", None) else image
            frame_width, frame_height = self._get_preview_frame_size()
            source_w, source_h = reference.size
            return get_fit_scales(frame_width, frame_height, source_w, source_h)

    def _get_display_zoom_percent(self):
            """Liefert Zoomanzeige immer relativ zur Seitenbreite."""

            return int(round(self.zoom_percent))

    def set_view_fit_mode(self, fit_mode):
            """Setzt Ansichts-Preset als seitenbreitenbezogenen Zoomwert."""

            if fit_mode not in VIEW_MODE_LABELS:
                return

            self.preview_fit_mode_var.set(fit_mode)

            if self.preview_images:
                page = self.preview_images[self.current_page_index]
                width_fit_scale, page_fit_scale = self._get_fit_scales(page)

                if fit_mode == VIEW_FIT_WIDTH:
                    target_zoom_percent = 100.0
                else:
                    ratio = (page_fit_scale / width_fit_scale) if width_fit_scale > 0 else 1.0
                    target_zoom_percent = 100.0 * ratio

                self.zoom_percent = clamp(target_zoom_percent, PREVIEW_ZOOM_MIN_PERCENT, PREVIEW_ZOOM_MAX_PERCENT)

            self._refresh_zoom_label()
            if self.preview_images:
                x_view_start = self.preview_canvas.xview()[0]
                y_view_start = self.preview_canvas.yview()[0]
                self._show_current_page(
                    reset_scroll=False,
                    x_view_start=x_view_start,
                    y_view_start=y_view_start,
                )
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()

    def set_preview_layout_mode(self, layout_mode):
            """Schaltet zwischen Einzelseite und Seitenband um."""

            if layout_mode not in {VIEW_LAYOUT_SINGLE, VIEW_LAYOUT_STRIP, VIEW_LAYOUT_STACK}:
                return

            self.preview_layout_mode_var.set(layout_mode)
            if self.preview_images:
                self._show_current_page(reset_scroll=True)
            if hasattr(self, "_persist_active_document_tab_state"):
                self._persist_active_document_tab_state()
