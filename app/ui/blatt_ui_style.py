"""GUI-Mixin fuer Darstellung: setzt die Teil-Mixins fuer Gestaltung, Theme, Menue und
Vorschau-Ansicht zusammen. Klassenname und Importpfad bleiben stabil.
"""

from __future__ import annotations


from .blatt_ui_style_design import BlattwerkAppStyleDesignMixin
from .blatt_ui_style_theme import BlattwerkAppStyleThemeMixin
from .blatt_ui_style_menu import BlattwerkAppStyleMenuMixin
from .blatt_ui_style_view import BlattwerkAppStyleViewMixin


class BlattwerkAppStyleMixin(
    BlattwerkAppStyleDesignMixin,
    BlattwerkAppStyleThemeMixin,
    BlattwerkAppStyleMenuMixin,
    BlattwerkAppStyleViewMixin,
):
    """Kapselt Theme-, Menü- und Designprofil-Logik der GUI."""
