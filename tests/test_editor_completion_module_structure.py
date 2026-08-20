"""Struktur-Regressionstests für den B0-Completion-Refactor.

Reiner Struktur-Refactor (Aufteilung von `blatt_ui_editor.py` in drei
Completion-Module) ohne Verhaltensänderung -- diese Tests sichern nur ab,
dass die Module sauber importierbar sind, in `BlattwerkApp` korrekt
eingebunden wurden und die zentralen Completion-Methoden nachweisbar aus
dem dafür vorgesehenen Modul aufgelöst werden (keine stille
Fehlauflösung durch MRO-Reihenfolge oder Doppeldefinition).
"""

from app.ui.blatt_ui import BlattwerkApp
from app.ui.blatt_ui_editor_completion_context import BlattwerkAppEditorCompletionContextMixin
from app.ui.blatt_ui_editor_completion_popup import BlattwerkAppEditorCompletionPopupMixin
from app.ui.blatt_ui_editor_completion_ranking import BlattwerkAppEditorCompletionRankingMixin


def test_completion_context_mixin_is_a_base_of_blattwerk_app():
    assert issubclass(BlattwerkApp, BlattwerkAppEditorCompletionContextMixin)


def test_completion_popup_mixin_is_a_base_of_blattwerk_app():
    assert issubclass(BlattwerkApp, BlattwerkAppEditorCompletionPopupMixin)


def test_completion_ranking_mixin_is_a_base_of_blattwerk_app():
    assert issubclass(BlattwerkApp, BlattwerkAppEditorCompletionRankingMixin)


def test_central_popup_methods_resolve_from_completion_popup_module():
    for method_name in (
        "_open_editor_completion",
        "_close_editor_completion",
        "_on_editor_completion_accept",
        "_resolve_completion_insert",
    ):
        resolved = getattr(BlattwerkApp, method_name)
        assert resolved.__module__ == "app.ui.blatt_ui_editor_completion_popup", (
            f"{method_name} resolved from {resolved.__module__}, expected the popup module"
        )


def test_context_collection_resolves_from_completion_context_module():
    resolved = getattr(BlattwerkApp, "_collect_editor_completion_context")
    assert resolved.__module__ == "app.ui.blatt_ui_editor_completion_context"


def test_ranking_methods_resolve_from_completion_ranking_module():
    for method_name in ("_rank_block_type_suggestions", "_rank_option_value_suggestions"):
        resolved = getattr(BlattwerkApp, method_name)
        assert resolved.__module__ == "app.ui.blatt_ui_editor_completion_ranking"
