"""Tabbasierter Einstellungsdialog mit linker Tabnavigation."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..storage.user_preferences_adapter import (
    get_tab_specs,
    normalize_user_preferences,
)
from .ui_theme import apply_window_theme, configure_ttk_theme, get_theme


class SettingsDialog:
    """Zeigt alle Einstellungen in einer scrollbaren Tabansicht."""

    def __init__(
        self,
        parent,
        *,
        theme_key: str,
        preferences: dict[str, object],
        initial_tab: str | None = None,
        on_live_apply=None,
        on_commit=None,
    ):
        self.parent = parent
        self.result: dict[str, object] | None = None
        self._on_live_apply = on_live_apply
        self._on_commit = on_commit
        self._last_committed = normalize_user_preferences(preferences)
        self._tab_specs = get_tab_specs()
        self._field_vars: dict[str, tk.Variable] = {}
        self._active_tab_key: str = self._tab_specs[0][0] if self._tab_specs else ""
        self._theme = get_theme(theme_key)
        self._toggle_widgets: dict[str, dict[str, object]] = {}

        self.window = tk.Toplevel(parent)
        self.window.title("Einstellungen")
        self.window.transient(parent)
        self.window.geometry("980x700")
        self.window.minsize(920, 620)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        apply_window_theme(self.window, theme_key)
        configure_ttk_theme(self.window, theme_key)

        root = ttk.Frame(self.window, padding=10)
        root.grid(row=0, column=0, sticky="nsew")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)

        self._build_tab_list(root)
        self._build_content_area(root)
        self._build_buttons(root)

        self._initialize_fields(self._last_committed)
        target_tab = initial_tab if self._tab_exists(initial_tab) else self._active_tab_key
        self._select_tab(target_tab)

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.window.grab_set()
        self.window.focus_set()
        self._apply_dialog_theme(theme_key)
        self.parent.wait_window(self.window)

    def _apply_dialog_theme(self, theme_key: str):
        """Wendet Theme auch auf klassische Tk-Widgets des Dialogs an."""
        theme = get_theme(theme_key)
        self._theme = theme

        self.tab_listbox.configure(
            background=theme["bg_surface"],
            foreground=theme["fg_primary"],
            selectbackground=theme["accent_soft"],
            selectforeground=theme["fg_primary"],
            highlightthickness=1,
            highlightbackground=theme["border"],
            highlightcolor=theme["accent"],
            borderwidth=0,
            relief="flat",
        )

        self.content_canvas.configure(
            background=theme["bg_main"],
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )
        self._refresh_visible_toggles()

    def _refresh_visible_toggles(self):
        """Aktualisiert die Darstellung aller aktuell sichtbaren Toggle-Widgets."""
        for toggle_data in self._toggle_widgets.values():
            refresh_cb = toggle_data.get("refresh")
            if callable(refresh_cb):
                refresh_cb()

    def _build_tab_list(self, root):
        side = ttk.Frame(root)
        side.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        side.rowconfigure(0, weight=1)

        self.tab_listbox = tk.Listbox(side, exportselection=False, height=24)
        self.tab_listbox.grid(row=0, column=0, sticky="ns")

        tab_scroll = ttk.Scrollbar(side, orient="vertical", command=self.tab_listbox.yview)
        tab_scroll.grid(row=0, column=1, sticky="ns")
        self.tab_listbox.configure(yscrollcommand=tab_scroll.set)

        for _, tab_label, _ in self._tab_specs:
            self.tab_listbox.insert("end", tab_label)

        self.tab_listbox.bind("<<ListboxSelect>>", self._on_tab_select)

    def _build_content_area(self, root):
        content = ttk.Frame(root)
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self.content_canvas = tk.Canvas(content, highlightthickness=0)
        self.content_canvas.grid(row=0, column=0, sticky="nsew")

        content_scroll = ttk.Scrollbar(content, orient="vertical", command=self.content_canvas.yview)
        content_scroll.grid(row=0, column=1, sticky="ns")
        self.content_canvas.configure(yscrollcommand=content_scroll.set)

        self.content_frame = ttk.Frame(self.content_canvas, padding=(6, 2, 10, 10))
        self.content_window_id = self.content_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)
        self.content_canvas.bind("<MouseWheel>", self._on_mouse_wheel)

    def _build_buttons(self, root):
        buttons = ttk.Frame(root)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)

        ttk.Button(buttons, text="Tab-Standard", command=self._reset_tab_defaults).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Alle Standard", command=self._reset_all_defaults).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(buttons, text="Abbrechen", command=self._on_cancel).grid(row=0, column=2, sticky="e")
        ttk.Button(buttons, text="Anwenden", command=self._on_apply).grid(row=0, column=3, sticky="e", padx=(8, 0))
        ttk.Button(buttons, text="Speichern", command=self._on_save).grid(row=0, column=4, sticky="e", padx=(8, 0))

    def _tab_exists(self, tab_key: str | None) -> bool:
        if not tab_key:
            return False
        for key, _, _ in self._tab_specs:
            if key == tab_key:
                return True
        return False

    def _initialize_fields(self, preferences: dict[str, object]):
        normalized = normalize_user_preferences(preferences)
        for _, _, tab_items in self._tab_specs:
            for pref_key, spec in tab_items:
                pref_type = spec.get("type")
                value = normalized.get(pref_key)

                if pref_type == "bool":
                    var = tk.BooleanVar(value=bool(value))
                elif pref_type in {"int", "float"}:
                    var = tk.StringVar(value=str(value))
                else:
                    var = tk.StringVar(value=str(value))

                self._field_vars[pref_key] = var
                if bool(spec.get("live_apply")):
                    var.trace_add("write", self._on_live_change)

    def _on_tab_select(self, _event=None):
        selection = self.tab_listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        tab_key = self._tab_specs[index][0]
        self._select_tab(tab_key)

    def _select_tab(self, tab_key: str):
        self._active_tab_key = tab_key
        for idx, (candidate, _, _) in enumerate(self._tab_specs):
            if candidate == tab_key:
                self.tab_listbox.selection_clear(0, "end")
                self.tab_listbox.selection_set(idx)
                self.tab_listbox.see(idx)
                break

        for child in self.content_frame.winfo_children():
            child.destroy()
        self._toggle_widgets = {}

        header = ttk.Label(self.content_frame, text=self._get_tab_label(tab_key), style="SectionTitle.TLabel")
        header.grid(row=0, column=0, sticky="w", pady=(0, 8))

        row = 1
        for pref_key, spec in self._iter_tab_items(tab_key):
            row = self._render_field(row, pref_key, spec)

        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.columnconfigure(1, weight=1)
        self.content_canvas.yview_moveto(0.0)

    def _get_tab_label(self, tab_key: str) -> str:
        for key, label, _ in self._tab_specs:
            if key == tab_key:
                return label
        return tab_key

    def _iter_tab_items(self, tab_key: str):
        for key, _, tab_items in self._tab_specs:
            if key == tab_key:
                yield from tab_items

    def _render_field(self, row_index: int, pref_key: str, spec: dict[str, object]) -> int:
        label = ttk.Label(self.content_frame, text=str(spec.get("label", pref_key)))
        label.grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=5)

        pref_type = spec.get("type")
        var = self._field_vars[pref_key]

        if pref_type == "bool":
            self._render_boolean_toggle(row_index, pref_key, var)
            return row_index + 1

        if pref_type == "enum":
            values = list(spec.get("values", []))
            widget = ttk.Combobox(self.content_frame, textvariable=var, values=values, state="readonly", width=34)
            widget.grid(row=row_index, column=1, sticky="w", pady=5)
            return row_index + 1

        widget = ttk.Entry(self.content_frame, textvariable=var, width=38)
        widget.grid(row=row_index, column=1, sticky="w", pady=5)

        hint_parts: list[str] = []
        if spec.get("type") == "int":
            hint_parts.append("Ganzzahl")
        if spec.get("type") == "float":
            hint_parts.append("Dezimalzahl")
        if spec.get("min") is not None or spec.get("max") is not None:
            hint_parts.append(f"min={spec.get('min')} max={spec.get('max')}")

        if hint_parts:
            hint = ttk.Label(self.content_frame, text=" | ".join(hint_parts), style="Muted.TLabel")
            hint.grid(row=row_index + 1, column=1, sticky="w", pady=(0, 6))
            return row_index + 2

        return row_index + 1

    def _collect_preferences(self) -> dict[str, object]:
        raw: dict[str, object] = {}
        for pref_key, var in self._field_vars.items():
            raw[pref_key] = var.get()
        return normalize_user_preferences(raw)

    def _on_live_change(self, *_args):
        if self._on_live_apply is None:
            return
        self._on_live_apply(self._collect_preferences())

    def _render_boolean_toggle(self, row_index: int, pref_key: str, var: tk.Variable):
        """Rendert boolesche Einstellungen als modernisierten Toggle-Switch."""

        container = tk.Frame(self.content_frame, bd=0, highlightthickness=0)
        container.grid(row=row_index, column=1, sticky="w", pady=5)

        canvas = tk.Canvas(
            container,
            width=44,
            height=24,
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )
        canvas.pack(side="left")

        state_label = ttk.Label(container, text="", style="Muted.TLabel")
        state_label.pack(side="left", padx=(8, 0))

        def _toggle_state(_event=None):
            var.set(not bool(var.get()))
            _refresh()

        def _refresh():
            on_state = bool(var.get())
            theme = self._theme

            track_bg = theme["accent"] if on_state else theme["border"]
            track_outline = theme["accent_hover"] if on_state else theme["border"]
            knob_bg = theme["bg_surface"]
            knob_outline = theme["border"]

            container.configure(background=theme["bg_main"])
            canvas.configure(background=theme["bg_main"])
            canvas.delete("all")

            # Track (pill shape)
            canvas.create_oval(2, 2, 22, 22, fill=track_bg, outline=track_outline, width=1)
            canvas.create_oval(22, 2, 42, 22, fill=track_bg, outline=track_outline, width=1)
            canvas.create_rectangle(12, 2, 32, 22, fill=track_bg, outline=track_bg, width=0)

            # Knob
            knob_left = 22 if on_state else 2
            knob_right = 42 if on_state else 22
            canvas.create_oval(
                knob_left,
                2,
                knob_right,
                22,
                fill=knob_bg,
                outline=knob_outline,
                width=1,
            )

            state_label.configure(
                text="Ein" if on_state else "Aus",
                foreground=theme["fg_primary"] if on_state else theme["fg_muted"],
            )

        canvas.bind("<Button-1>", _toggle_state)
        state_label.bind("<Button-1>", _toggle_state)
        container.bind("<Button-1>", _toggle_state)

        self._toggle_widgets[pref_key] = {"refresh": _refresh}
        _refresh()

    def _reset_tab_defaults(self):
        defaults = normalize_user_preferences({})
        for pref_key, _ in self._iter_tab_items(self._active_tab_key):
            var = self._field_vars[pref_key]
            var.set(str(defaults[pref_key]) if not isinstance(var, tk.BooleanVar) else bool(defaults[pref_key]))
        self._refresh_visible_toggles()

    def _reset_all_defaults(self):
        defaults = normalize_user_preferences({})
        for pref_key, var in self._field_vars.items():
            value = defaults[pref_key]
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))
        self._refresh_visible_toggles()

    def _on_apply(self):
        self.result = self._collect_preferences()
        self._last_committed = dict(self.result)
        if self._on_commit is not None:
            self._on_commit(self.result)
        if self._on_live_apply is not None:
            self._on_live_apply(self.result)

    def _on_save(self):
        self.result = self._collect_preferences()
        self._last_committed = dict(self.result)
        if self._on_commit is not None:
            self._on_commit(self.result)
        if self._on_live_apply is not None:
            self._on_live_apply(self.result)
        self.window.destroy()

    def _on_cancel(self):
        if self._on_live_apply is not None:
            self._on_live_apply(dict(self._last_committed))
        self.window.destroy()

    def _on_content_configure(self, _event):
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.content_canvas.itemconfigure(self.content_window_id, width=event.width)

    def _on_mouse_wheel(self, event):
        if not self.window.winfo_exists():
            return
        if self.window.focus_displayof() is None:
            return
        delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta != 0:
            self.content_canvas.yview_scroll(delta, "units")
