"""GUI-Mixin fuer Exporte: setzt die Teil-Mixins fuer Hilfsfunktionen, Dokumentformate,
Lernhilfen und Exportdialoge zusammen.

Klassenname und Importpfad bleiben stabil; die Export-Vorgaben (`_normalize_choice`,
`_resolve_export_default_*`) werden aus `export_defaults.py` re-exportiert.
"""

from __future__ import annotations

from .export_defaults import (  # noqa: F401 -- re-exportiert fuer bestehende Importe
    _normalize_choice,
    _resolve_export_default_format,
    _resolve_export_default_page_format,
)
from .blatt_ui_export_support import BlattwerkAppExportSupportMixin
from .blatt_ui_export_documents import BlattwerkAppExportDocumentsMixin
from .blatt_ui_export_images import BlattwerkAppExportImagesMixin
from .blatt_ui_export_help_cards import BlattwerkAppExportHelpCardsMixin
from .blatt_ui_export_dialogs import BlattwerkAppExportDialogsMixin


class BlattwerkAppExportMixin(
    BlattwerkAppExportSupportMixin,
    BlattwerkAppExportDocumentsMixin,
    BlattwerkAppExportImagesMixin,
    BlattwerkAppExportHelpCardsMixin,
    BlattwerkAppExportDialogsMixin,
):
    """Stellt Export-Workflows für PDF/HTML/PNG/ZIP bereit."""

    _SURFACED_COMPILE_WARNING_CODES = {"SL005", "SL007", "PT002", "IM003", "PPTX001", "PPTX002"}
    """`PT002` (Präsentations-Overflow), `IM003` (Worterklärung passt nicht
    sauber an den Seitenrand, nur im gerenderten PDF messbar) plus die beiden Fallback-Diagnosen des
    experimentellen editierbaren PPTX-Exports (`blatt_kern_pptx_export.py`):
    `PPTX001` (einzelne Folie gerastert) und `PPTX002` (kompletter Fallback
    auf den Raster-Export). Ein interner Fallback darf nie unsichtbar
    bleiben -- deshalb hier mit aufgenommen, statt nur PT002 zu zeigen."""
