"""Modal export dialogs for worksheet, presentation, and lernhilfen flows."""

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets

try:
    from bw_gui.shortcuts import compose_hover_text as compose_shared_hover_text
except ModuleNotFoundError:
    compose_shared_hover_text = None

from .dialog_services import filedialog, messagebox
from .ui_theme import apply_window_theme, configure_ttk_theme, get_theme


def _localize_shortcut_label(shortcut_label: str) -> str:
    """Map shared shortcut wording to existing German UI labels."""

    text = str(shortcut_label or "")
    return text.replace("Ctrl", "Strg").replace("Escape", "Esc")


def _shortcut_help_entry(description: str, sequence: str | None) -> str:
    """Build one compact shortcut help entry via the shared formatter."""

    desc = str(description or "").strip()
    if compose_shared_hover_text is None:
        shortcut = _localize_shortcut_label(str(sequence or "").strip())
        if not shortcut:
            return desc
        if not desc:
            return shortcut
        return f"{shortcut}: {desc}"

    merged = compose_shared_hover_text(desc, sequence)
    marker = "\nShortcut: "
    if marker not in merged:
        return merged

    resolved_desc, resolved_shortcut = merged.split(marker, 1)
    shortcut = _localize_shortcut_label(resolved_shortcut.strip())
    if not resolved_desc:
        return shortcut
    return f"{shortcut}: {resolved_desc}"


def _build_shortcuts_help_text(*rows: tuple[tuple[str, str | None], ...]) -> str:
    """Compose multi-line shortcuts help text from action/sequence rows."""

    lines: list[str] = []
    for row in rows:
        entries = [_shortcut_help_entry(description, sequence) for description, sequence in row]
        lines.append("   ".join(item for item in entries if item.strip()))
    return "\n".join(line for line in lines if line.strip())


class _BaseExportDialog:
    """Shared modal dialog helpers for export workflows."""

    def __init__(self, parent, input_path: Path, theme_key: str, initial_output_dir: str | None = None):
        self.parent = parent
        self.input_path = input_path
        self.theme_key = theme_key
        self.initial_output_dir = initial_output_dir
        self.result = None
        self.output_var = ui.StringVar()
        self.shortcuts_visible = False

        self.window = ui.Toplevel(parent)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)

        apply_window_theme(self.window, self.theme_key)
        configure_ttk_theme(self.window, self.theme_key)

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

    def _show_window(self):
        self.window.update_idletasks()
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()
        self.parent.wait_window(self.window)

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


class WorksheetExportDialog(_BaseExportDialog):
    """Modaler Dialog für Arbeitsblatt-Exporte."""

    def __init__(
        self,
        parent,
        input_path: Path,
        default_format: str,
        default_mode: str,
        theme_key: str,
        initial_output_dir: str | None = None,
        worksheet_label: str = "Aufgaben",
        solution_label: str = "Loesung",
        solution_suffix: str = "_loesung",
        allow_mode_selection: bool = True,
    ):
        super().__init__(parent, input_path, theme_key, initial_output_dir=initial_output_dir)
        self.worksheet_label = str(worksheet_label or "Aufgaben")
        self.solution_label = str(solution_label or "Loesung")
        self.solution_suffix = str(solution_suffix or "_loesung")
        self.allow_mode_selection = bool(allow_mode_selection)

        self.format_var = ui.StringVar(value=default_format)
        self.mode_var = ui.StringVar(value=default_mode)

        self.window.title("Arbeitsblatt exportieren")
        self._build_ui()
        self._bind_shortcuts()
        self._refresh_output_suggestion(force=True)
        self._show_window()

    def _build_ui(self):
        theme = get_theme(self.theme_key)

        outer = widgets.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)

        widgets.Label(outer, text="Exportoptionen", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        fmt_row = widgets.Frame(outer)
        fmt_row.pack(fill="x", pady=(10, 4))
        widgets.Label(fmt_row, text="Format:", width=15).pack(side="left")
        widgets.Radiobutton(fmt_row, text="PDF", value="pdf", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left")
        widgets.Radiobutton(fmt_row, text="PNG", value="png", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(fmt_row, text="PNG (ZIP)", value="pngzip", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(fmt_row, text="HTML", value="html", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))

        if self.allow_mode_selection:
            mode_row = widgets.Frame(outer)
            mode_row.pack(fill="x", pady=(4, 4))
            widgets.Label(mode_row, text="Inhalt:", width=15).pack(side="left")
            widgets.Radiobutton(mode_row, text=self.worksheet_label, value="worksheet", variable=self.mode_var, command=self._refresh_output_suggestion).pack(side="left")
            widgets.Radiobutton(mode_row, text=self.solution_label, value="solution", variable=self.mode_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
            widgets.Radiobutton(mode_row, text="Beides", value="both", variable=self.mode_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        else:
            self.mode_var.set("worksheet")

        out_row = widgets.Frame(outer)
        out_row.pack(fill="x", pady=(10, 4))
        widgets.Label(out_row, text="Ausgabe:", width=15).pack(side="left")
        widgets.Entry(out_row, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        widgets.Button(out_row, text="Durchsuchen…", style="SecondaryAction.TButton", command=self._pick_output).pack(side="left")

        actions = widgets.Frame(outer)
        actions.pack(fill="x", pady=(12, 0))
        widgets.Button(actions, text="?", width=3, style="SecondaryAction.TButton", command=self._toggle_shortcuts_help).pack(side="right")
        widgets.Button(actions, text="Exportieren", style="PrimaryAction.TButton", command=self._confirm).pack(side="left")
        widgets.Button(actions, text="Abbrechen", style="SecondaryAction.TButton", command=self._cancel).pack(side="left", padx=(8, 0))

        self.shortcuts_frame = widgets.LabelFrame(outer, text="Shortcuts")
        widgets.Label(
            self.shortcuts_frame,
            style="Muted.TLabel",
            justify="left",
            text=self._build_shortcuts_help_text(self.allow_mode_selection),
        ).pack(anchor="w", padx=8, pady=6)

        self._set_shortcuts_help_visible(False)
        self.window.configure(bg=theme["bg_main"])

    @staticmethod
    def _build_shortcuts_help_text(allow_mode_selection: bool) -> str:
        first_row = (
            ("Exportieren", "<Control-e>"),
            ("Abbrechen", "<Escape>"),
        )
        if allow_mode_selection:
            first_line = _build_shortcuts_help_text(first_row)
            second_line = "   ".join(
                (
                    "A/L/B: Inhalt",
                    _shortcut_help_entry("Format wechseln", "P"),
                    _shortcut_help_entry("Durchsuchen", "D"),
                )
            )
            return f"{first_line}\n{second_line}"
        return _build_shortcuts_help_text(
            first_row,
            (
                ("Format wechseln", "P"),
                ("Durchsuchen", "D"),
            ),
        )

    def _bind_shortcuts(self):
        self.window.bind("<Return>", lambda _event: "break")
        self.window.bind("<KP_Enter>", lambda _event: "break")
        self.window.bind("<Control-e>", lambda _event: self._confirm_shortcut())
        self.window.bind("<Escape>", lambda _event: self._cancel())
        self.window.bind("<KeyPress-question>", lambda _event: self._toggle_shortcuts_help_shortcut())

        if self.allow_mode_selection:
            self.window.bind("<KeyPress-a>", lambda _event: self._set_mode("worksheet"))
            self.window.bind("<KeyPress-l>", lambda _event: self._set_mode("solution"))
            self.window.bind("<KeyPress-b>", lambda _event: self._set_mode("both"))

        self.window.bind("<KeyPress-d>", lambda _event: self._browse_output_shortcut())
        self.window.bind("<KeyPress-p>", lambda _event: self._toggle_export_format())

    def _set_mode(self, mode):
        if not self.allow_mode_selection:
            return "break"
        if not self._can_handle_char_shortcut():
            return "break"

        if self.mode_var.get() != mode:
            self.mode_var.set(mode)
        self._refresh_output_suggestion(force=True)
        return "break"

    def _browse_output_shortcut(self):
        if not self._can_handle_char_shortcut():
            return "break"

        self._pick_output()
        return "break"

    def _toggle_export_format(self):
        if not self._can_handle_char_shortcut():
            return "break"

        export_formats = self._allowed_formats()
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

    @staticmethod
    def _allowed_formats():
        return ["pdf", "png", "pngzip", "html"]

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
        suffix = self.solution_suffix if self.mode_var.get() == "solution" else ""
        self.output_var.set(str(stem) + suffix + self._extension())

    def _pick_output(self):
        ext = self._extension()
        fmt_label = (
            "PDF" if ext == ".pdf"
            else "HTML" if ext == ".html"
            else "PNG" if ext == ".png"
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
            messagebox.showwarning("Fehlende Ausgabe", "Bitte gib eine Ausgabedatei an.", parent=self.window)
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


class PresentationExportDialog(_BaseExportDialog):
    """Modaler Dialog fuer Praesentations-Exporte."""

    def __init__(
        self,
        parent,
        input_path: Path,
        default_format: str,
        black_screen_default: str,
        theme_key: str,
        initial_output_dir: str | None = None,
    ):
        super().__init__(parent, input_path, theme_key, initial_output_dir=initial_output_dir)
        self.format_var = ui.StringVar(value=default_format)
        self.black_screen_var = ui.StringVar(value=black_screen_default)

        self.window.title("Praesentation exportieren")
        self._build_ui()
        self._bind_shortcuts()
        self._refresh_output_suggestion(force=True)
        self._show_window()

    def _build_ui(self):
        theme = get_theme(self.theme_key)

        outer = widgets.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)

        widgets.Label(outer, text="Praesentations-Export", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        fmt_row = widgets.Frame(outer)
        fmt_row.pack(fill="x", pady=(10, 4))
        widgets.Label(fmt_row, text="Format:", width=15).pack(side="left")
        widgets.Radiobutton(fmt_row, text="PDF", value="pdf", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left")
        widgets.Radiobutton(fmt_row, text="PPTX", value="pptx", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(fmt_row, text="PNG", value="png", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(fmt_row, text="PNG (ZIP)", value="pngzip", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(fmt_row, text="HTML", value="html", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))

        black_row = widgets.Frame(outer)
        black_row.pack(fill="x", pady=(4, 4))
        widgets.Label(black_row, text="Black-Screen:", width=15).pack(side="left")
        widgets.Radiobutton(black_row, text="Aus", value="none", variable=self.black_screen_var).pack(side="left")
        widgets.Radiobutton(black_row, text="Vorher", value="before", variable=self.black_screen_var).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(black_row, text="Nachher", value="after", variable=self.black_screen_var).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(black_row, text="Beides", value="both", variable=self.black_screen_var).pack(side="left", padx=(12, 0))

        out_row = widgets.Frame(outer)
        out_row.pack(fill="x", pady=(10, 4))
        widgets.Label(out_row, text="Ausgabe:", width=15).pack(side="left")
        widgets.Entry(out_row, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        widgets.Button(out_row, text="Durchsuchen…", style="SecondaryAction.TButton", command=self._pick_output).pack(side="left")

        actions = widgets.Frame(outer)
        actions.pack(fill="x", pady=(12, 0))
        widgets.Button(actions, text="?", width=3, style="SecondaryAction.TButton", command=self._toggle_shortcuts_help).pack(side="right")
        widgets.Button(actions, text="Exportieren", style="PrimaryAction.TButton", command=self._confirm).pack(side="left")
        widgets.Button(actions, text="Abbrechen", style="SecondaryAction.TButton", command=self._cancel).pack(side="left", padx=(8, 0))

        self.shortcuts_frame = widgets.LabelFrame(outer, text="Shortcuts")
        widgets.Label(
            self.shortcuts_frame,
            style="Muted.TLabel",
            justify="left",
            text=self._build_shortcuts_help_text(),
        ).pack(anchor="w", padx=8, pady=6)

        self._set_shortcuts_help_visible(False)
        self.window.configure(bg=theme["bg_main"])

    @staticmethod
    def _build_shortcuts_help_text() -> str:
        return _build_shortcuts_help_text(
            (
                ("Exportieren", "<Control-e>"),
                ("Abbrechen", "<Escape>"),
            ),
            (
                ("Format wechseln", "P"),
                ("Black-Screen beides", "K"),
                ("Durchsuchen", "D"),
            ),
        )

    def _bind_shortcuts(self):
        self.window.bind("<Return>", lambda _event: "break")
        self.window.bind("<KP_Enter>", lambda _event: "break")
        self.window.bind("<Control-e>", lambda _event: self._confirm_shortcut())
        self.window.bind("<Escape>", lambda _event: self._cancel())
        self.window.bind("<KeyPress-question>", lambda _event: self._toggle_shortcuts_help_shortcut())
        self.window.bind("<KeyPress-d>", lambda _event: self._browse_output_shortcut())
        self.window.bind("<KeyPress-p>", lambda _event: self._toggle_export_format())
        self.window.bind("<KeyPress-k>", lambda _event: self._set_black_screen_both())

    @staticmethod
    def _allowed_formats():
        return ["pdf", "pptx", "png", "pngzip", "html"]

    def _set_black_screen_both(self):
        if not self._can_handle_char_shortcut():
            return "break"

        self.black_screen_var.set("both")
        return "break"

    def _browse_output_shortcut(self):
        if not self._can_handle_char_shortcut():
            return "break"

        self._pick_output()
        return "break"

    def _toggle_export_format(self):
        if not self._can_handle_char_shortcut():
            return "break"

        export_formats = self._allowed_formats()
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

    def _extension(self):
        selected_format = self.format_var.get()
        if selected_format == "pdf":
            return ".pdf"
        if selected_format == "html":
            return ".html"
        if selected_format == "png":
            return ".png"
        if selected_format == "pptx":
            return ".pptx"
        return ".zip"

    def _refresh_output_suggestion(self, force=False):
        current = self.output_var.get().strip()
        if current and not force:
            return

        stem = self.input_path.with_suffix("")
        self.output_var.set(str(stem) + self._extension())

    def _pick_output(self):
        ext = self._extension()
        fmt_label = (
            "PDF" if ext == ".pdf"
            else "PPTX" if ext == ".pptx"
            else "HTML" if ext == ".html"
            else "PNG" if ext == ".png"
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
            messagebox.showwarning("Fehlende Ausgabe", "Bitte gib eine Ausgabedatei an.", parent=self.window)
            return

        out_path = Path(out)
        if out_path.suffix.lower() != self._extension():
            out_path = out_path.with_suffix(self._extension())

        self.result = {
            "format": self.format_var.get(),
            "mode": "worksheet",
            "black_screen": self.black_screen_var.get(),
            "output_path": out_path,
        }
        self.window.destroy()


class LernhilfenExportDialog(_BaseExportDialog):
    """Modaler Dialog für Lernhilfen-Exporte."""

    def __init__(
        self,
        parent,
        input_path: Path,
        default_format: str,
        theme_key: str,
        initial_output_dir: str | None = None,
    ):
        super().__init__(parent, input_path, theme_key, initial_output_dir=initial_output_dir)
        self.format_var = ui.StringVar(value=default_format)

        self.window.title("Lernhilfen exportieren")
        self._build_ui()
        self._bind_shortcuts()
        self._refresh_output_suggestion(force=True)
        self._show_window()

    def _build_ui(self):
        theme = get_theme(self.theme_key)

        outer = widgets.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)

        widgets.Label(outer, text="Lernhilfen-Export", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        fmt_row = widgets.Frame(outer)
        fmt_row.pack(fill="x", pady=(10, 4))
        widgets.Label(fmt_row, text="Format:", width=15).pack(side="left")
        widgets.Radiobutton(fmt_row, text="PDF", value="pdf", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left")
        widgets.Radiobutton(fmt_row, text="PNG", value="png", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))
        widgets.Radiobutton(fmt_row, text="PNG (ZIP)", value="pngzip", variable=self.format_var, command=self._refresh_output_suggestion).pack(side="left", padx=(12, 0))

        out_row = widgets.Frame(outer)
        out_row.pack(fill="x", pady=(10, 4))
        widgets.Label(out_row, text="Ausgabe:", width=15).pack(side="left")
        widgets.Entry(out_row, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        widgets.Button(out_row, text="Durchsuchen…", style="SecondaryAction.TButton", command=self._pick_output).pack(side="left")

        actions = widgets.Frame(outer)
        actions.pack(fill="x", pady=(12, 0))
        widgets.Button(actions, text="?", width=3, style="SecondaryAction.TButton", command=self._toggle_shortcuts_help).pack(side="right")
        widgets.Button(actions, text="Exportieren", style="PrimaryAction.TButton", command=self._confirm).pack(side="left")
        widgets.Button(actions, text="Abbrechen", style="SecondaryAction.TButton", command=self._cancel).pack(side="left", padx=(8, 0))

        self.shortcuts_frame = widgets.LabelFrame(outer, text="Shortcuts")
        widgets.Label(
            self.shortcuts_frame,
            style="Muted.TLabel",
            justify="left",
            text=_build_shortcuts_help_text(
                (
                    ("Exportieren", "<Control-e>"),
                    ("Abbrechen", "<Escape>"),
                ),
                (
                    ("Format wechseln", "P"),
                    ("Durchsuchen", "D"),
                ),
            ),
        ).pack(anchor="w", padx=8, pady=6)

        self._set_shortcuts_help_visible(False)
        self.window.configure(bg=theme["bg_main"])

    def _bind_shortcuts(self):
        self.window.bind("<Return>", lambda _event: "break")
        self.window.bind("<KP_Enter>", lambda _event: "break")
        self.window.bind("<Control-e>", lambda _event: self._confirm_shortcut())
        self.window.bind("<Escape>", lambda _event: self._cancel())
        self.window.bind("<KeyPress-question>", lambda _event: self._toggle_shortcuts_help_shortcut())
        self.window.bind("<KeyPress-d>", lambda _event: self._browse_output_shortcut())
        self.window.bind("<KeyPress-p>", lambda _event: self._toggle_export_format())

    def _allowed_formats(self):
        return ["pdf", "png", "pngzip"]

    def _browse_output_shortcut(self):
        if not self._can_handle_char_shortcut():
            return "break"

        self._pick_output()
        return "break"

    def _toggle_export_format(self):
        if not self._can_handle_char_shortcut():
            return "break"

        export_formats = self._allowed_formats()
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

    def _extension(self):
        selected_format = self.format_var.get()
        if selected_format == "pdf":
            return ".pdf"
        if selected_format == "png":
            return ".png"
        return ".zip"

    def _refresh_output_suggestion(self, force=False):
        current = self.output_var.get().strip()
        if current and not force:
            return

        stem = self.input_path.with_suffix("")
        self.output_var.set(str(stem) + "_lernhilfen" + self._extension())

    def _pick_output(self):
        ext = self._extension()
        fmt_label = "PDF" if ext == ".pdf" else "PNG" if ext == ".png" else "ZIP"
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
            messagebox.showwarning("Fehlende Ausgabe", "Bitte gib eine Ausgabedatei an.", parent=self.window)
            return

        selected_format = self.format_var.get()
        if selected_format not in self._allowed_formats():
            messagebox.showwarning(
                "Format erforderlich",
                "Lernhilfen unterstützen nur PDF, PNG oder PNG (ZIP).",
                parent=self.window,
            )
            return

        out_path = Path(out)
        if out_path.suffix.lower() != self._extension():
            out_path = out_path.with_suffix(self._extension())

        self.result = {
            "format": selected_format,
            "mode": "help_cards",
            "output_path": out_path,
        }
        self.window.destroy()


