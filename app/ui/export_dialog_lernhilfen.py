"""Export dialog for learning aids (Lernhilfen).

Split out of export_dialog.py (file-size rule); bodies unchanged."""

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import Checkbox

from .dialog_services import filedialog, messagebox
from .ui_theme import get_theme
from .export_dialog_base import _BaseExportDialog, _build_shortcuts_help_text


class LernhilfenExportDialog(_BaseExportDialog):
    """Modaler Dialog für Lernhilfen-Exporte."""

    def __init__(
        self,
        parent,
        input_path: Path,
        default_format: str,
        theme_key: str,
        initial_output_dir: str | None = None,
        allow_all_tabs_export: bool = False,
    ):
        super().__init__(parent, input_path, theme_key, initial_output_dir=initial_output_dir)
        self.format_var = ui.StringVar(value=default_format)
        self.allow_all_tabs_export = bool(allow_all_tabs_export)
        self.export_all_tabs_var = ui.BooleanVar(value=False)

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

        if self.allow_all_tabs_export:
            all_tabs_row = widgets.Frame(outer)
            all_tabs_row.pack(fill="x", pady=(4, 4))
            Checkbox(
                all_tabs_row,
                text="Alle offenen Dokumente exportieren (ein ZIP mit je einer PDF-Datei)",
                variable=self.export_all_tabs_var,
                on_select=lambda _selected: self._refresh_output_suggestion(force=True),
            ).pack(side="left")

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
        if self.allow_all_tabs_export and bool(self.export_all_tabs_var.get()):
            return ".zip"
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

        if self.allow_all_tabs_export and bool(self.export_all_tabs_var.get()):
            suggestion_dir = self.input_path.with_suffix("").parent
            self.output_var.set(str(suggestion_dir / "lernhilfen_alle_dokumente.zip"))
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

        export_all_tabs = self.allow_all_tabs_export and bool(self.export_all_tabs_var.get())

        selected_format = self.format_var.get()
        if not export_all_tabs and selected_format not in self._allowed_formats():
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
            "format": "pdf" if export_all_tabs else selected_format,
            "mode": "help_cards",
            "output_path": out_path,
            "export_all_tabs": export_all_tabs,
        }
        self.window.destroy()
