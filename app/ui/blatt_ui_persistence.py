"""GUI-Mixin fuer Persistenz: setzt die Teil-Mixins fuer Dokument-Tabs, Einstellungen und Verlauf zusammen.

Klassenname und Importpfad bleiben stabil; die Methoden leben nach Verantwortung
getrennt in `blatt_ui_persistence_*.py`.
"""

from __future__ import annotations


from .blatt_ui_persistence_tabs import BlattwerkAppPersistenceTabsMixin
from .blatt_ui_persistence_settings import BlattwerkAppPersistenceSettingsMixin
from .blatt_ui_persistence_history import BlattwerkAppPersistenceHistoryMixin


class BlattwerkAppPersistenceMixin(
    BlattwerkAppPersistenceTabsMixin,
    BlattwerkAppPersistenceSettingsMixin,
    BlattwerkAppPersistenceHistoryMixin,
):
    """Verwaltet Persistenz für Verlauf, Dialogpfade und UI-Einstellungen."""
