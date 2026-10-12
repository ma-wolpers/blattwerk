"""GUI-Mixin der Vorschau: setzt die Teil-Mixins fuer Toolbar, Dokumentdateien, Rendern und Ansicht zusammen.

Der Klassenname `BlattwerkAppPreviewMixin` und dieser Importpfad bleiben stabil;
die Methoden leben nach Verantwortung getrennt in `blatt_ui_preview_*.py`.
"""

from __future__ import annotations


from .blatt_ui_preview_toolbar import BlattwerkAppPreviewToolbarMixin
from .blatt_ui_preview_files import BlattwerkAppPreviewFilesMixin
from .blatt_ui_preview_render import BlattwerkAppPreviewRenderMixin
from .blatt_ui_preview_view import BlattwerkAppPreviewViewMixin


class BlattwerkAppPreviewMixin(
    BlattwerkAppPreviewToolbarMixin,
    BlattwerkAppPreviewFilesMixin,
    BlattwerkAppPreviewRenderMixin,
    BlattwerkAppPreviewViewMixin,
):
    """Rendert, skaliert und navigiert die Arbeitsblatt-Vorschau."""
