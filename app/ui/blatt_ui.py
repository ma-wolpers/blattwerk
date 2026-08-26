"""Façade module preserving public GUI imports."""

from __future__ import annotations

from .blatt_ui_base import BlattwerkAppBase
from .blatt_ui_build import BlattwerkAppBuildMixin
from .blatt_ui_editor import BlattwerkAppEditorMixin
from .blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin
from .blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin
from .blatt_ui_editor_completion_ranking import BlattwerkAppEditorCompletionRankingMixin
from .blatt_ui_editor_search import BlattwerkAppEditorSearchMixin
from .blatt_ui_export import BlattwerkAppExportMixin
from .blatt_ui_export_multi import BlattwerkAppExportMultiMixin
from .blatt_ui_help_docs import BlattwerkAppHelpDocsMixin
from .blatt_ui_help_preview import BlattwerkAppHelpPreviewMixin
from .blatt_ui_persistence import BlattwerkAppPersistenceMixin
from .blatt_ui_preview import BlattwerkAppPreviewMixin
from .blatt_ui_style import BlattwerkAppStyleMixin
from bw_libs.shared_gui_core import ensure_bw_gui_on_path
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
    BlattwerkAppPreviewMixin,
    BlattwerkAppHelpDocsMixin,
    BlattwerkAppHelpPreviewMixin,
    BlattwerkAppBuildMixin,
    BlattwerkAppPersistenceMixin,
    BlattwerkAppStyleMixin,
    BlattwerkAppBase,
):
    """Vorschau-zentrierte GUI für Blattwerk."""


def run_gui(dependencies: AppDependencies | None = None):
    """Startet die Tkinter-Anwendung."""

    resolved_dependencies = dependencies or build_gui_dependencies()
    configure_windows_process_identity()
    BlattwerkApp(deps=resolved_dependencies).run()
