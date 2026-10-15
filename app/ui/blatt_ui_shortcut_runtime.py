"""Popup gating, shortcut runtime context, Escape escalation and Laufkern hooks (BlattwerkAppBase mixin).

Split out of blatt_ui_base.py (file-size rule). Popup gating and the Escape target read
the bw-gui overlay stack (``OVERLAY_STACK_CONTRACT.md``): modal dialogs and menu popups
(the completion list registers as a menu while visible) block the window shortcuts
(``blocking(include_menus=True)``); the help and shortcut-debug windows register as
non-modal and do not. This reproduces the former scan, which counted every visible
direct child toplevel of the root unless it had been tracked as non-blocking
(``tests/test_overlay_gating_tk.py``)."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts.events import EventResult
from bw_gui.runtime import WindowShortcutBinder, accepts_text_input, topmost_window, ui
from bw_gui.runtime.overlay_stack import OverlayCategory, blocking, register_overlay


from .ui_constants import EDITOR_VIEW_BOTH, EDITOR_VIEW_EDITOR_ONLY, EDITOR_VIEW_PREVIEW_ONLY
from bw_gui.contracts.keybinding import (
    UI_MODE_EDITOR,
    UI_MODE_GLOBAL,
    UI_MODE_PREVIEW,
    KeyBindingDefinition,
    KeybindingRuntimeContext,
    derive_active_mode,
)
from bw_gui.contracts.hsm import ESCAPE_CLOSE_POPUP, ESCAPE_EXIT_INLINE_EDITOR, ESCAPE_POP_PARENT
from bw_gui.laufkern import aggregate_completion, emit_tracking_artifact, verify_manifest, verify_reachability
from .laufkern_manifest_provider import build_runtime_shortcut_manifest


class BlattwerkShortcutRuntimeMixin:
    """Popup gating, shortcut runtime context, Escape escalation and Laufkern hooks (BlattwerkAppBase mixin)."""

    @staticmethod
    def _is_widget_descendant_of(widget: ui.Misc | None, parent: ui.Misc | None) -> bool:
        """Return whether widget is nested below parent in the widget tree."""

        if widget is None or parent is None:
            return False

        current = widget
        while current is not None:
            if current == parent:
                return True
            current = getattr(current, "master", None)
        return False

    def _has_dialog_context(self) -> bool:
        """Return whether a modal dialog or a menu popup is open (bw-gui overlay stack).

        Menu popups include the editor completion list while it is visible (it
        registers as ``MENU``); the help and shortcut-debug windows are non-modal and do
        not count.
        """
        return blocking(self.root, include_menus=True)()

    def _register_popup_window(self, window: ui.Toplevel, *, blocking_shortcuts: bool = True) -> None:
        """Register a raw ``Toplevel`` of the app in the bw-gui overlay stack (ends on ``<Destroy>``).

        Args:
            blocking_shortcuts: ``True`` (default) registers a ``MODAL_DIALOG`` that blocks
                the window shortcuts while open; ``False`` a ``NON_MODAL_POPUP`` tool window
                (help documentation, shortcut debug) that does not.
        """
        category = OverlayCategory.MODAL_DIALOG if blocking_shortcuts else OverlayCategory.NON_MODAL_POPUP
        register_overlay(window, category, toplevel=window)

    def _install_window_shortcuts(self) -> None:
        """Bind every registry definition on a ``WindowShortcutBinder`` of the main window.

        The registry (``self.keybinding_registry``) stays the declarative source for
        debug overlay, LaufKern manifest and HSM intents; the binder keeps its own
        internal registry. Gating sources are the same ones the debug overlay uses
        (:meth:`_shortcut_base_mode`, :meth:`_has_dialog_context`, the offline toggle,
        bw-gui's text-input contract). An executed shortcut consumes the key.
        """
        binder = WindowShortcutBinder(
            self.root,
            hsm_contract=self.hsm_contract,
            dialog_open=self._has_dialog_context,
            offline=lambda: bool(self.shortcut_debug_offline_var.get()),
            mode_provider=self._shortcut_base_mode,
            on_dispatch=self._record_laufkern_intent_dispatch,
        )
        for definition in self.keybinding_registry.all():
            action = definition.handler or (lambda: None)

            def _run(_event, action=action) -> EventResult:
                action()
                return EventResult.HANDLED

            binder.bind(
                definition.keys,
                _run,
                binding_id=definition.binding_id,
                intent=definition.intent,
                modes=definition.modes,
                allow_when_text_input=definition.allow_when_text_input,
                allow_when_offline=definition.allow_when_offline,
                description=definition.description,
            )
        self._window_shortcut_binder = binder

    def _shortcut_base_mode(self) -> str:
        """Base UI mode without offline/dialog/text overrides: preview focus, editor view or global."""

        focused_widget = self.root.focus_get()
        if self._is_widget_descendant_of(focused_widget, getattr(self, "preview_container", None)):
            return UI_MODE_PREVIEW
        if self.editor_view_mode_var.get() in {EDITOR_VIEW_BOTH, EDITOR_VIEW_EDITOR_ONLY}:
            return UI_MODE_EDITOR
        return UI_MODE_GLOBAL

    def _collect_shortcut_runtime_context(self) -> dict[str, object]:
        """Collect current runtime context used by shortcut diagnostics (same sources as the binder)."""

        focused_widget = self.root.focus_get()
        text_input_focused = accepts_text_input(focused_widget)
        dialog_open = self._has_dialog_context()
        offline = bool(self.shortcut_debug_offline_var.get())
        active_mode = derive_active_mode(
            offline=offline,
            dialog_open=dialog_open,
            text_input_focused=text_input_focused,
            base_mode=self._shortcut_base_mode(),
        )

        return {
            "active_mode": active_mode,
            "offline": offline,
            "dialog_open": dialog_open,
            "text_input_focused": text_input_focused,
            "focused_widget_class": focused_widget.winfo_class() if focused_widget is not None else "none",
            "active_popup": str(topmost_window(self.root) or "none"),
        }

    def _close_active_popup_on_escape(self) -> bool:
        """Close the most recently opened escape-closable popup (``topmost_window``) and return success."""

        popup = topmost_window(self.root)
        if popup is None:
            return False
        try:
            popup.destroy()  # also ends its overlay registration
        except Exception:
            pass
        return True

    def _handle_global_escape(self, _event=None):
        """Resolve escape action via centralized HSM priority rules."""

        has_popup = topmost_window(self.root) is not None
        has_inline_editor = bool(getattr(self, "_editor_completion_popup", None))
        has_parent_state = self.editor_view_mode_var.get() != EDITOR_VIEW_PREVIEW_ONLY

        action = self.hsm_contract.resolve_escape_action(
            has_popup=has_popup,
            has_inline_editor=has_inline_editor,
            has_parent_state=has_parent_state,
        )
        if action == ESCAPE_CLOSE_POPUP and self._close_active_popup_on_escape():
            return
        if action == ESCAPE_EXIT_INLINE_EDITOR:
            self._close_editor_completion()
            return
        if action == ESCAPE_POP_PARENT:
            self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY)

    def _evaluate_keybinding_runtime(
        self,
        definition: KeyBindingDefinition,
        *,
        active_mode_override: str | None = None,
    ) -> tuple[bool, str]:
        """Evaluate whether one keybinding is executable in current runtime context."""

        context = self._collect_shortcut_runtime_context()
        intent_ok, intent_reason = self.hsm_contract.validate_intent(definition.intent)
        if not intent_ok:
            return False, intent_reason

        runtime_context = KeybindingRuntimeContext(
            active_mode=str(context["active_mode"]),
            offline=bool(context["offline"]),
            text_input_focused=bool(context["text_input_focused"]),
            dialog_open=bool(context["dialog_open"]),
        )
        return self.keybinding_registry.evaluate_runtime(
            definition,
            runtime_context,
            active_mode_override=active_mode_override,
        )

    def _build_laufkern_manifest(self):
        """Build one declarative LaufKern manifest from registered runtime shortcuts."""

        return build_runtime_shortcut_manifest(self.keybinding_registry)

    def _summarize_laufkern_reachability(
        self,
        *,
        runtime_context: KeybindingRuntimeContext,
    ) -> str:
        """Return compact LaufKern reachability summary for current runtime state."""

        manifest = self._build_laufkern_manifest()
        manifest_ok, manifest_errors = verify_manifest(manifest)
        if not manifest_ok:
            return f"LaufKern manifest-errors={len(manifest_errors)}"

        results = verify_reachability(manifest=manifest, context=runtime_context)
        reachable = sum(1 for result in results if result.reachable)
        return f"LaufKern intents {reachable}/{len(results)} erreichbar"

    def _laufkern_step_id_for_intent(self, intent: str) -> str:
        """Return stable runtime-tracking step id for one intent during this session."""

        existing = self._laufkern_tracking_step_ids.get(intent)
        if existing is not None:
            return existing

        next_index = len(self._laufkern_tracking_step_ids) + 1
        step_id = f"LK-D-RTC-{next_index:03d}"
        self._laufkern_tracking_step_ids[intent] = step_id
        return step_id

    def _record_laufkern_intent_dispatch(self, intent: str, *, success: bool) -> None:
        """Record runtime intent dispatch result as LaufKern tracking artifact."""

        self._laufkern_tracking_sequence += 1
        artifact = emit_tracking_artifact(
            run_id=self._laufkern_tracking_run_id,
            repo_name="blattwerk",
            step_id=self._laufkern_step_id_for_intent(intent),
            phase="D",
            state="done" if success else "failed",
            sequence=self._laufkern_tracking_sequence,
            mandatory=True,
            producer="laufkern-runtime",
            evidence_ref=intent,
        )
        self._laufkern_tracking_artifacts.append(artifact)

    def _summarize_laufkern_completion(self) -> str:
        """Return compact completion status summary from tracked runtime artifacts."""

        if not self._laufkern_tracking_artifacts:
            return "LK completion n/a"

        summary = aggregate_completion(
            self._laufkern_tracking_artifacts,
            trusted_producers={"laufkern-runtime"},
        )
        return f"LK completion {summary.status} {summary.completed_steps}/{summary.mandatory_steps}"
