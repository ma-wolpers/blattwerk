"""Popup tracking, shortcut runtime context, Escape escalation and Laufkern hooks (BlattwerkAppBase mixin).

Split out of blatt_ui_base.py (file-size rule); method bodies unchanged."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui


from .ui_constants import EDITOR_VIEW_BOTH, EDITOR_VIEW_EDITOR_ONLY, EDITOR_VIEW_PREVIEW_ONLY
from bw_gui.contracts.keybinding import (
    UI_MODE_DIALOG,
    UI_MODE_EDITOR,
    UI_MODE_GLOBAL,
    UI_MODE_OFFLINE,
    UI_MODE_PREVIEW,
    KeyBindingDefinition,
    KeybindingRuntimeContext,
)
from bw_gui.contracts.hsm import ESCAPE_CLOSE_POPUP, ESCAPE_EXIT_INLINE_EDITOR, ESCAPE_POP_PARENT
from bw_gui.laufkern import aggregate_completion, emit_tracking_artifact, verify_manifest, verify_reachability
from .laufkern_manifest_provider import build_runtime_shortcut_manifest


class BlattwerkShortcutRuntimeMixin:
    """Popup tracking, shortcut runtime context, Escape escalation and Laufkern hooks (BlattwerkAppBase mixin)."""

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
        """Return whether a dialog-like context currently has focus priority."""

        self._sync_popup_sessions_from_windows()

        menu_bar = getattr(self, "_menu_bar", None)
        if menu_bar is not None and bool(getattr(menu_bar, "_popup_stack", [])):
            return True

        if self.popup_policy_registry.has_mode_blocking_popup():
            return True

        return False

    def _sync_popup_sessions_from_windows(self) -> None:
        """Synchronize popup policy stack from currently visible Tk toplevel windows."""

        visible_popup_ids: set[str] = set()

        for child in self.root.winfo_children():
            if not isinstance(child, ui.Toplevel):
                continue
            try:
                if not int(child.winfo_exists()):
                    continue
                if str(child.state()).lower() == "withdrawn":
                    continue
            except Exception:
                continue

            popup_id = str(child)
            visible_popup_ids.add(popup_id)
            if popup_id in self._tracked_popup_ids:
                continue

            popup_title = ""
            try:
                popup_title = str(child.title() or "")
            except Exception:
                popup_title = ""

            self.popup_policy_registry.open_popup(
                popup_id=popup_id,
                title=popup_title,
                policy_id="dialog.modal",
            )
            self._tracked_popup_ids.add(popup_id)

        stale_popup_ids = self._tracked_popup_ids - visible_popup_ids
        for popup_id in tuple(stale_popup_ids):
            self.popup_policy_registry.close_popup(popup_id)
            self._tracked_popup_ids.discard(popup_id)

    def _track_popup_window(self, window: ui.Toplevel, *, policy_id: str = "dialog.modal") -> None:
        """Register a popup immediately in the popup policy registry."""

        popup_id = str(window)
        if popup_id in self._tracked_popup_ids:
            return
        popup_title = ""
        try:
            popup_title = str(window.title() or "")
        except Exception:
            popup_title = ""
        self.popup_policy_registry.open_popup(popup_id=popup_id, title=popup_title, policy_id=policy_id)
        self._tracked_popup_ids.add(popup_id)

    def _collect_shortcut_runtime_context(self) -> dict[str, object]:
        """Collect current runtime context used by shortcut resolver and diagnostics."""

        focused_widget = self.root.focus_get()
        text_input_focused = self.shortcut_manager._is_text_input_widget(focused_widget)
        dialog_open = self._has_dialog_context()
        offline = bool(self.shortcut_debug_offline_var.get())

        if offline:
            active_mode = UI_MODE_OFFLINE
        elif dialog_open:
            active_mode = UI_MODE_DIALOG
        elif text_input_focused:
            active_mode = UI_MODE_EDITOR
        elif self._is_widget_descendant_of(focused_widget, getattr(self, "preview_container", None)):
            active_mode = UI_MODE_PREVIEW
        elif self.editor_view_mode_var.get() in {EDITOR_VIEW_BOTH, EDITOR_VIEW_EDITOR_ONLY}:
            active_mode = UI_MODE_EDITOR
        else:
            active_mode = UI_MODE_GLOBAL

        return {
            "active_mode": active_mode,
            "offline": offline,
            "dialog_open": dialog_open,
            "text_input_focused": text_input_focused,
            "focused_widget_class": focused_widget.winfo_class() if focused_widget is not None else "none",
            "active_popup": (
                self.popup_policy_registry.active_popup().popup_id
                if self.popup_policy_registry.active_popup() is not None
                else "none"
            ),
        }

    def _close_active_popup_on_escape(self) -> bool:
        """Close top-most escape-closable popup and return success."""

        self._sync_popup_sessions_from_windows()
        active_popup = self.popup_policy_registry.active_popup()
        if active_popup is None:
            return False

        try:
            policy = self.popup_policy_registry.policy(active_popup.policy_id)
        except Exception:
            policy = None
        if policy is not None and not policy.close_on_escape:
            return False

        popup_id = active_popup.popup_id
        for child in self.root.winfo_children():
            if not isinstance(child, ui.Toplevel):
                continue
            if str(child) != popup_id:
                continue
            try:
                child.destroy()
            except Exception:
                pass
            break

        self.popup_policy_registry.close_popup(popup_id)
        self._tracked_popup_ids.discard(popup_id)
        return True

    def _handle_global_escape(self, _event=None):
        """Resolve escape action via centralized HSM priority rules."""

        has_popup = self.popup_policy_registry.has_active_popup()
        has_inline_editor = bool(getattr(self, "_editor_completion_popup", None))
        has_parent_state = self.editor_view_mode_var.get() != EDITOR_VIEW_PREVIEW_ONLY

        action = self.hsm_contract.resolve_escape_action(
            has_popup=has_popup,
            has_inline_editor=has_inline_editor,
            has_parent_state=has_parent_state,
        )
        if action == ESCAPE_CLOSE_POPUP and self._close_active_popup_on_escape():
            return "break"
        if action == ESCAPE_EXIT_INLINE_EDITOR:
            self._close_editor_completion()
            return "break"
        if action == ESCAPE_POP_PARENT:
            self._set_editor_view_mode(EDITOR_VIEW_PREVIEW_ONLY)
            return "break"
        return "break"

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
