"""GUI-Mixin fuer Darstellung: setzt die Teil-Mixins fuer Gestaltung, Schriftmenue, Theme,
Menuemodell und Vorschau-Ansicht zusammen. Klassenname und Importpfad bleiben stabil.
"""

from __future__ import annotations

from .blatt_ui_document_font import BlattwerkAppDocumentFontMixin
from .blatt_ui_menu_items import BlattwerkAppMenuItemsMixin
from .blatt_ui_style_design import BlattwerkAppStyleDesignMixin
from .blatt_ui_style_theme import BlattwerkAppStyleThemeMixin
from .blatt_ui_style_view import BlattwerkAppStyleViewMixin


class BlattwerkAppStyleMixin(
    BlattwerkAppDocumentFontMixin,
    BlattwerkAppStyleDesignMixin,
    BlattwerkAppStyleThemeMixin,
    BlattwerkAppMenuItemsMixin,
    BlattwerkAppStyleViewMixin,
):
    """Kapselt Theme-, Menü- und Designprofil-Logik der GUI."""
