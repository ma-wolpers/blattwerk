"""Modaler Exportdialog für Blattwerk.

Bewusst getrennt von der Haupt-UI, damit Exportoptionen
unabhängig erweiterbar bleiben (z. B. neue Formate/Profile).
"""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .ui_theme import apply_window_theme, configure_ttk_theme, get_theme


class ExportDialog:
    """Modaler Dialog für den Export mit allen Ausgabeoptionen."""

    def __init__(
        self,
        parent,
        input_path: Path,
        default_format: str,
        default_mode: str,
        theme_key: str,
        initial_output_dir: str | None = None,
    ):
        self.parent = parent
        self.input_path = input_path
        self.theme_key = theme_key
        self.initial_output_dir = initial_output_dir

        self.result = None

        self.format_var = tk.StringVar(value=default_format)
        self.mode_var = tk.StringVar(value=default_mode)
        self.output_var = tk.StringVar()
        self.shortcuts_visible = False

        self.window = tk.Toplevel(parent)
        self.window.title("Exportieren")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)

        apply_window_theme(self.window, self.theme_key)
        configure_ttk_theme(self.window, self.theme_key)

        self._build_ui()
        self._bind_shortcuts()
        self._refresh_output_suggestion(force=True)

        self.window.update_idletasks()
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()
        self.parent.wait_window(self.window)

    def _build_ui(self):
        theme = get_theme(self.theme_key)

        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Exportoptionen", font=("Segoe UI", 11, "bold")).pack(
            anchor="w"
        )

        fmt_row = ttk.Frame(outer)
        fmt_row.pack(fill="x", pady=(10, 4))
        ttk.Label(fmt_row, text="Format:", width=15).pack(side="left")
        ttk.Radiobutton(
            fmt_row,
            text="PDF",
            value="pdf",
            variable=self.format_var,
            command=self._refresh_output_suggestion,
        ).pack(side="left")
        ttk.Radiobutton(
            fmt_row,
            text="PNG",
            value="png",
            variable=self.format_var,
            command=self._refresh_output_suggestion,
        ).pack(side="left", padx=(12, 0))
        ttk.Radiobutton(
            fmt_row,
            text="PNG (ZIP)",
            value="pngzip",
            variable=self.format_var,
            command=self._refresh_output_suggestion,
        ).pack(side="left", padx=(12, 0))
        ttk.Radiobutton(
            fmt_row,
            text="HTML",
            value="html",
            variable=self.format_var,
            command=self._refresh_output_suggestion,
        ).pack(side="left", padx=(12, 0))

        mode_row = ttk.Frame(outer)
        mode_row.pack(fill="x", pady=(4, 4))
        ttk.Label(mode_row, text="Inhalt:", width=15).pack(side="left")
        ttk.Radiobutton(
            mode_row,
            text="Aufgaben",
            value="worksheet",
            variable=self.mode_var,
            command=self._on_mode_changed,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_row,
            text="Lösung",
            value="solution",
            variable=self.mode_var,
            command=self._on_mode_changed,
        ).pack(side="left", padx=(12, 0))
        ttk.Radiobutton(
            mode_row,
            text="Beides",
            value="both",
            variable=self.mode_var,
            command=self._on_mode_changed,
        ).pack(side="left", padx=(12, 0))
        ttk.Radiobutton(
            mode_row,
            text="Nur Hilfekarten",
            value="help_cards",
            variable=self.mode_var,
            command=self._on_mode_changed,
        ).pack(side="left", padx=(12, 0))

        out_row = ttk.Frame(outer)
        out_row.pack(fill="x", pady=(10, 4))
        ttk.Label(out_row, text="Ausgabe:", width=15).pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(
            out_row,
            text="Durchsuchen…",
            style="SecondaryAction.TButton",
            command=self._pick_output,
        ).pack(side="left")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(
            actions,
            text="?",
            width=3,
            style="SecondaryAction.TButton",
            command=self._toggle_shortcuts_help,
        ).pack(side="right")
        ttk.Button(
            actions,
            text="Exportieren",
            style="PrimaryAction.TButton",
            command=self._confirm,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Abbrechen",
            style="SecondaryAction.TButton",
            command=self._cancel,
        ).pack(side="left", padx=(8, 0))

        self.shortcuts_frame = ttk.LabelFrame(outer, text="Shortcuts")
        ttk.Label(
            self.shortcuts_frame,
            style="Muted.TLabel",
            justify="left",
            text=(
                "Enter: Exportieren   Esc: Abbrechen\n"
                "A/L/B/H: Inhalt   P: Format wechseln   D: Durchsuchen"
            ),
        ).pack(anchor="w", padx=8, pady=6)

        self._set_shortcuts_help_visible(False)

        if hasattr(self, "window"):
            self.window.configure(bg=theme["bg_main"])

    def _bind_shortcuts(self):
        self.window.bind("<Return>", lambda _event: self._confirm_shortcut())
        self.window.bind("<KP_Enter>", lambda _event: self._confirm_shortcut())
        self.window.bind("<Escape>", lambda _event: self._cancel())
        self.window.bind(
            "<KeyPress-question>", lambda _event: self._toggle_shortcuts_help_shortcut()
        )

        self.window.bind("<KeyPress-a>", lambda _event: self._set_mode("worksheet"))
        self.window.bind("<KeyPress-l>", lambda _event: self._set_mode("solution"))
        self.window.bind("<KeyPress-b>", lambda _event: self._set_mode("both"))
        self.window.bind("<KeyPress-h>", lambda _event: self._set_mode("help_cards"))

        self.window.bind("<KeyPress-d>", lambda _event: self._browse_output_shortcut())
        self.window.bind("<KeyPress-p>", lambda _event: self._toggle_export_format())

    @staticmethod
    def _is_text_input_widget(widget):
        if widget is None:
            return False

        widget_class = widget.winfo_class().lower()
        return widget_class in {
            "entry",
            "ttk::entry",
            "text",
            "spinbox",
            "ttk::combobox",
        }

    def _can_handle_char_shortcut(self):
        return not self._is_text_input_widget(self.window.focus_get())

    def _set_mode(self, mode):
        if not self._can_handle_char_shortcut():
            return "break"

        if self.mode_var.get() != mode:
            self.mode_var.set(mode)
        self._on_mode_changed(force=True)
        return "break"

    def _on_mode_changed(self, force=True):
        if self.mode_var.get() == "help_cards" and self.format_var.get() != "png":
            self.format_var.set("png")
        self._refresh_output_suggestion(force=force)

    def _browse_output_shortcut(self):
        if not self._can_handle_char_shortcut():
            return "break"

        self._pick_output()
        return "break"

    def _toggle_export_format(self):
        if not self._can_handle_char_shortcut():
            return "break"

        export_formats = ["pdf", "png", "pngzip", "html"]
        current = self.format_var.get()
        try:
            index = export_formats.index(current)
        except ValueError:
            index = 0
        new_value = export_formats[(index + 1) % len(export_formats)]
        self.format_var.set(new_value)
        self._refresh_output_suggestion(force=True)
        return "break"

    def _confirm_shortcut(self):
        self._confirm()
        return "break"

    def _set_shortcuts_help_visible(self, visible: bool):
        self.shortcuts_visible = bool(visible)
        if self.shortcuts_visible:
            self.shortcuts_frame.pack(fill="x", pady=(10, 0))
        else:
            self.shortcuts_frame.pack_forget()

    def _toggle_shortcuts_help(self):
        self._set_shortcuts_help_visible(not self.shortcuts_visible)

    def _toggle_shortcuts_help_shortcut(self):
        if not self._can_handle_char_shortcut():
            return "break"

        self._toggle_shortcuts_help()
        return "break"

    def _cancel(self):
        self.window.destroy()
        return "break"

    def _extension(self):
        selected_format = self.format_var.get()
        if selected_format == "pdf":
            return ".pdf"
        if selected_format == "html":
            return ".html"
        if selected_format == "png":
            return ".png"
        return ".zip"

    def _refresh_output_suggestion(self, force=False):
        current = self.output_var.get().strip()
        if current and not force:
            return

        stem = self.input_path.with_suffix("")
        mode = self.mode_var.get()
        suffix = ""
        if mode == "solution":
            suffix += "_loesung"
        elif mode == "help_cards":
            suffix += "_hilfe"

        self.output_var.set(str(stem) + suffix + self._extension())

    def _pick_output(self):
        ext = self._extension()
        fmt_label = (
            "PDF"
            if ext == ".pdf"
            else "HTML"
            if ext == ".html"
            else "PNG"
            if ext == ".png"
            else "ZIP"
        )
        dialog_kwargs = {
            "title": "Ausgabe speichern unter",
            "defaultextension": ext,
            "initialfile": Path(self.output_var.get().strip() or f"export{ext}").name,
            "filetypes": [(fmt_label, f"*{ext}"), ("Alle Dateien", "*.*")],
        }
        if self.initial_output_dir and Path(self.initial_output_dir).is_dir():
            dialog_kwargs["initialdir"] = self.initial_output_dir

        selected = filedialog.asksaveasfilename(**dialog_kwargs)
        if selected:
            self.output_var.set(selected)

    def _confirm(self):
        out = self.output_var.get().strip().strip('"').strip("'")
        if not out:
            messagebox.showwarning(
                "Fehlende Ausgabe",
                "Bitte gib eine Ausgabedatei an.",
                parent=self.window,
            )
            return

        if self.mode_var.get() == "help_cards" and self.format_var.get() != "png":
            messagebox.showwarning(
                "Format erforderlich",
                "Der Modus 'Nur Hilfekarten' kann nur als PNG exportiert werden.",
                parent=self.window,
            )
            return

        out_path = Path(out)
        if out_path.suffix.lower() != self._extension():
            out_path = out_path.with_suffix(self._extension())

        self.result = {
            "format": self.format_var.get(),
            "mode": self.mode_var.get(),
            "output_path": out_path,
        }
        self.window.destroy()
