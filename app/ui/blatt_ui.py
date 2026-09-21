"""Façade module preserving public GUI imports."""

from __future__ import annotations

from .blatt_ui_base import BlattwerkAppBase
from .blatt_ui_block_insert_menu import BlattwerkAppBlockInsertMenuMixin
from .blatt_ui_build import BlattwerkAppBuildMixin
from .blatt_ui_editor import BlattwerkAppEditorMixin
from .blatt_ui_editor_diagnostics import BlattwerkAppEditorDiagnosticsMixin
from .blatt_ui_editor_diagnostics_ack import BlattwerkAppEditorDiagnosticsAckMixin
from .blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin
from .blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin
from .blatt_ui_editor_completion_ranking import BlattwerkAppEditorCompletionRankingMixin
from .blatt_ui_editor_search import BlattwerkAppEditorSearchMixin
from .blatt_ui_export import BlattwerkAppExportMixin
from .blatt_ui_external_open import BlattwerkAppExternalOpenMixin
from .blatt_ui_export_multi import BlattwerkAppExportMultiMixin
from .blatt_ui_help_docs import BlattwerkAppHelpDocsMixin
from .blatt_ui_help_preview import BlattwerkAppHelpPreviewMixin
from .blatt_ui_persistence import BlattwerkAppPersistenceMixin
from .blatt_ui_preview import BlattwerkAppPreviewMixin
from .blatt_ui_style import BlattwerkAppStyleMixin
from .blatt_ui_tab_strip import BlattwerkAppTabStripMixin
from bw_libs.shared_gui_core import ensure_bw_gui_on_path
from app.bootstrap.single_instance import InstanceServer
from app.bootstrap.wiring import AppDependencies, build_gui_dependencies
from .window_identity import configure_windows_process_identity

ensure_bw_gui_on_path()
from bw_gui.dialogs import open_tabbed_settings_dialog as _open_tabbed_settings_dialog_contract_marker
from bw_gui.shortcuts import compose_hover_text as _compose_hover_text_contract_marker
from bw_gui.widgets import HoverTooltip as _SharedHoverTooltipContractMarker


class BlattwerkApp(
    BlattwerkAppExportMultiMixin,
    BlattwerkAppExportMixin,
    BlattwerkAppEditorCompletionRankingMixin,
    BlattwerkAppEditorCompletionContextMixin,
    BlattwerkAppEditorCompletionPopupMixin,
    BlattwerkAppEditorSearchMixin,
    BlattwerkAppEditorMixin,
    BlattwerkAppBlockInsertMenuMixin,
    BlattwerkAppEditorDiagnosticsMixin,
    BlattwerkAppEditorDiagnosticsAckMixin,
    BlattwerkAppPreviewMixin,
    BlattwerkAppHelpDocsMixin,
    BlattwerkAppHelpPreviewMixin,
    BlattwerkAppBuildMixin,
    BlattwerkAppTabStripMixin,
    BlattwerkAppExternalOpenMixin,
    BlattwerkAppPersistenceMixin,
    BlattwerkAppStyleMixin,
    BlattwerkAppBase,
):
    """Vorschau-zentrierte GUI für Blattwerk."""


def run_gui(
    dependencies: AppDependencies | None = None,
    startup_file: str | None = None,
    instance_server: InstanceServer | None = None,
):
    """Startet die Tkinter-Anwendung.

    Args:
        dependencies: Composition-Root-Payload; Standard aus ``build_gui_dependencies()``.
        startup_file: Absoluter Pfad einer beim Start zu öffnenden Datei (Kommandozeile).
        instance_server: Bereits gestarteter Server, über den spätere Starts ihre Dateien
            an dieses Fenster übergeben (wird beim Beenden gestoppt), oder ``None``, wenn
            der Port nicht belegt werden konnte. Die Startdatei wird in beiden Fällen geöffnet.
    """

    resolved_dependencies = dependencies or build_gui_dependencies()
    configure_windows_process_identity()
    app = BlattwerkApp(deps=resolved_dependencies, startup_file=startup_file)
    try:
        app.start_external_open_listener(instance_server)
        app.run()
    finally:
        if instance_server is not None:
            instance_server.stop()
