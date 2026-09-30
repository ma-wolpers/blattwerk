"""Shortcut debug overlay and popup (BlattwerkAppBase mixin).

Split out of blatt_ui_base.py (file-size rule); method bodies unchanged."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets


from bw_gui.contracts.keybinding import UI_MODE_DIALOG, UI_MODE_EDITOR, UI_MODE_GLOBAL, UI_MODE_OFFLINE, UI_MODE_PREVIEW, KeybindingRuntimeContext
from bw_gui.widgets import Switch


class BlattwerkShortcutDebugMixin:
    """Shortcut debug overlay and popup (BlattwerkAppBase mixin)."""

    def _build_shortcut_debug_overlay_rows(self) -> list[tuple[str, str, str, str, str]]:
        """Build compact diagnostics rows for the shortcut debug table."""

        rows: list[tuple[str, str, str, str, str]] = []
        for mode in (UI_MODE_GLOBAL, UI_MODE_EDITOR, UI_MODE_PREVIEW, UI_MODE_DIALOG, UI_MODE_OFFLINE):
            for definition in self.keybinding_registry.all():
                if mode not in definition.modes and UI_MODE_GLOBAL not in definition.modes:
                    continue

                can_execute, reason = self._evaluate_keybinding_runtime(
                    definition,
                    active_mode_override=mode,
                )
                rows.append(
                    (
                        mode,
                        definition.sequence,
                        definition.binding_id,
                        "active" if can_execute else "disabled",
                        "" if can_execute else reason,
                    )
                )

        return rows

    def _refresh_shortcut_debug_overlay(self) -> None:
        """Refresh shortcut debug overlay text when overlay is visible."""

        if not bool(self.shortcut_debug_enabled_var.get()):
            return

        if self.shortcut_debug_table is None:
            return

        context = self._collect_shortcut_runtime_context()
        runtime_context = KeybindingRuntimeContext(
            active_mode=str(context["active_mode"]),
            offline=bool(context["offline"]),
            text_input_focused=bool(context["text_input_focused"]),
            dialog_open=bool(context["dialog_open"]),
        )
        self.shortcut_debug_context_var.set(
            " | ".join(
                [
                    f"mode={context['active_mode']}",
                    f"offline={context['offline']}",
                    f"dialog={context['dialog_open']}",
                    f"focus={context['focused_widget_class']}",
                    f"popup={context['active_popup']}",
                ]
            )
        )

        for item_id in self.shortcut_debug_table.get_children(""):
            self.shortcut_debug_table.delete(item_id)

        rows = self._build_shortcut_debug_overlay_rows()
        active_count = 0
        disabled_count = 0
        for mode, sequence, binding_id, status, reason in rows:
            tags = ("row_active",) if status == "active" else ("row_disabled",)
            if status == "active":
                active_count += 1
            else:
                disabled_count += 1
            self.shortcut_debug_table.insert(
                "",
                "end",
                values=(mode, sequence, binding_id, status, reason),
                tags=tags,
            )

        self.shortcut_debug_summary_var.set(
            " | ".join(
                [
                    f"Bindings: {len(rows)} total",
                    f"{active_count} active",
                    f"{disabled_count} disabled",
                    self._summarize_laufkern_reachability(runtime_context=runtime_context),
                    self._summarize_laufkern_completion(),
                ]
            )
        )

    def _schedule_shortcut_debug_overlay_refresh(self) -> None:
        """Schedule recurring refresh while debug overlay is visible."""

        if self._shortcut_debug_refresh_after_id is not None:
            try:
                self.root.after_cancel(self._shortcut_debug_refresh_after_id)
            except Exception:
                pass
            self._shortcut_debug_refresh_after_id = None

        if not bool(self.shortcut_debug_enabled_var.get()):
            return

        self._refresh_shortcut_debug_overlay()
        self._shortcut_debug_refresh_after_id = self.root.after(500, self._schedule_shortcut_debug_overlay_refresh)

    def _set_shortcut_debug_overlay_visible(self, visible: bool) -> None:
        """Show or hide the shortcut debug popup window."""

        if visible:
            self._open_shortcut_debug_popup()
            self.shortcut_debug_enabled_var.set(True)
            self._schedule_shortcut_debug_overlay_refresh()
            self.status_var.set("Shortcut-Runtime-Debug aktiv")
            return

        self.shortcut_debug_enabled_var.set(False)
        if self._shortcut_debug_refresh_after_id is not None:
            try:
                self.root.after_cancel(self._shortcut_debug_refresh_after_id)
            except Exception:
                pass
            self._shortcut_debug_refresh_after_id = None

        if self.shortcut_debug_window is not None:
            try:
                if int(self.shortcut_debug_window.winfo_exists()):
                    self.shortcut_debug_window.destroy()
            except Exception:
                pass
        self.shortcut_debug_window = None
        self.shortcut_debug_table = None
        self.status_var.set("Shortcut-Runtime-Debug ausgeblendet")

    def _open_shortcut_debug_popup(self) -> None:
        """Open (or focus) shortcut runtime debug popup."""

        if self.shortcut_debug_window is not None:
            try:
                if int(self.shortcut_debug_window.winfo_exists()):
                    self.shortcut_debug_window.deiconify()
                    self.shortcut_debug_window.lift()
                    self.shortcut_debug_window.focus_force()
                    return
            except Exception:
                self.shortcut_debug_window = None

        window = ui.Toplevel(self.root)
        window.title("Shortcut-Runtime-Debug")
        window.geometry("980x540")
        window.minsize(820, 420)
        self._track_popup_window(window, policy_id="dialog.non_blocking")

        toolbar = widgets.Frame(window, padding=(10, 8))
        toolbar.pack(fill="x")
        widgets.Label(toolbar, textvariable=self.shortcut_debug_context_var, style="Muted.TLabel").pack(
            side="left",
            fill="x",
            expand=True,
        )
        Switch(
            toolbar,
            text="Offline simulieren",
            variable=self.shortcut_debug_offline_var,
            on_change=lambda _offline: self._on_shortcut_debug_offline_changed(),
        ).pack(side="left", padx=(12, 0))
        widgets.Button(
            toolbar,
            text="Aktualisieren",
            style="SecondaryAction.TButton",
            command=self._refresh_shortcut_debug_overlay,
        ).pack(side="left", padx=(8, 0))
        widgets.Button(
            toolbar,
            text="Schliessen",
            style="SecondaryAction.TButton",
            command=lambda: self._set_shortcut_debug_overlay_visible(False),
        ).pack(side="right")

        debug_body = widgets.Frame(window, padding=(10, 0, 10, 8))
        debug_body.pack(fill="both", expand=True)
        columns = ("mode", "sequence", "binding", "status", "reason")
        self.shortcut_debug_table = widgets.Treeview(
            debug_body,
            columns=columns,
            show="headings",
            height=10,
        )
        self.shortcut_debug_table.heading("mode", text="Mode")
        self.shortcut_debug_table.heading("sequence", text="Key")
        self.shortcut_debug_table.heading("binding", text="Binding")
        self.shortcut_debug_table.heading("status", text="Status")
        self.shortcut_debug_table.heading("reason", text="Reason")
        self.shortcut_debug_table.column("mode", width=90, anchor="center", stretch=False)
        self.shortcut_debug_table.column("sequence", width=130, anchor="center", stretch=False)
        self.shortcut_debug_table.column("binding", width=280, anchor="w", stretch=True)
        self.shortcut_debug_table.column("status", width=90, anchor="center", stretch=False)
        self.shortcut_debug_table.column("reason", width=180, anchor="w", stretch=True)
        self.shortcut_debug_table.pack(side="left", fill="both", expand=True)

        debug_scrollbar = widgets.Scrollbar(debug_body, orient="vertical", command=self.shortcut_debug_table.yview)
        debug_scrollbar.pack(side="right", fill="y")
        self.shortcut_debug_table.configure(yscrollcommand=debug_scrollbar.set)

        widgets.Label(
            window,
            textvariable=self.shortcut_debug_summary_var,
            style="Muted.TLabel",
        ).pack(fill="x", padx=10, pady=(0, 8))

        window.protocol("WM_DELETE_WINDOW", lambda: self._set_shortcut_debug_overlay_visible(False))
        self.shortcut_debug_window = window

    def _toggle_shortcut_debug_overlay(self) -> None:
        """Toggle shortcut debug overlay visibility."""

        self._set_shortcut_debug_overlay_visible(not bool(self.shortcut_debug_enabled_var.get()))

    def _toggle_shortcut_debug_offline(self) -> None:
        """Toggle simulated offline context for shortcut diagnostics."""

        self.shortcut_debug_offline_var.set(not bool(self.shortcut_debug_offline_var.get()))
        self._refresh_shortcut_debug_overlay()

    def _on_shortcut_debug_offline_changed(self) -> None:
        """Handle offline simulation switch updates in debug overlay (immediate effect)."""

        self._refresh_shortcut_debug_overlay()
