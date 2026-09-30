"""Export dialog for presentations.

Split out of export_dialog.py (file-size rule); bodies unchanged."""

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import Checkbox

from ..core.blatt_kern_pptx_export_editable import is_editable_pptx_available
from .dialog_services import filedialog, messagebox
from .ui_theme import get_theme
from .export_dialog_base import _BaseExportDialog, _build_shortcuts_help_text


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
        self.ignore_framebreaks_var = ui.BooleanVar(value=False)
        self.editable_pptx_var = ui.BooleanVar(value=False)
        self._editable_pptx_available = is_editable_pptx_available()

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

        framebreak_row = widgets.Frame(outer)
        framebreak_row.pack(fill="x", pady=(4, 4))
        Checkbox(
            framebreak_row,
            text="Schrittweise Folien (-+) zu einer Folie zusammenfassen",
            variable=self.ignore_framebreaks_var,
        ).pack(side="left")

        self.editable_pptx_row = widgets.Frame(outer)
        self.editable_pptx_checkbutton = Checkbox(
            self.editable_pptx_row,
            text="Editierbare Text-/Bildelemente (experimentell)",
            variable=self.editable_pptx_var,
        )
        self.editable_pptx_checkbutton.pack(side="left")
        self.editable_pptx_hint_label = widgets.Label(
            self.editable_pptx_row,
            text="(benoetigt: pip install -r requirements-editable-pptx.txt)",
            style="Muted.TLabel",
        )
        if not self._editable_pptx_available:
            self.editable_pptx_checkbutton.configure(state="disabled")
            self.editable_pptx_hint_label.pack(side="left", padx=(8, 0))

        out_row = widgets.Frame(outer)
        self._editable_pptx_row_anchor = out_row
        out_row.pack(fill="x", pady=(10, 4))
        widgets.Label(out_row, text="Ausgabe:", width=15).pack(side="left")
        widgets.Entry(out_row, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        widgets.Button(out_row, text="Durchsuchen…", style="SecondaryAction.TButton", command=self._pick_output).pack(side="left")
        self._sync_editable_pptx_row_visibility()

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
        self._sync_editable_pptx_row_visibility()
        if current and not force:
            return

        stem = self.input_path.with_suffix("")
        self.output_var.set(str(stem) + self._extension())

    def _sync_editable_pptx_row_visibility(self):
        """Shows the "Editierbare Text-/Bildelemente"-row only for PPTX exports.

        Kept as an always-inert-when-hidden row (rather than not creating
        it at all for non-PPTX formats) so `self.editable_pptx_var` stays
        a stable, always-present attribute `_confirm()` can read
        unconditionally. `before=` anchors it right above the output row
        every time -- plain `pack()` after a `pack_forget()` would append
        it at the END of the current pack order instead of restoring its
        original position, visibly jumping it below "Ausgabe"/the action
        buttons after toggling the format radio buttons back and forth.
        """

        if self.format_var.get() == "pptx":
            self.editable_pptx_row.pack(fill="x", pady=(4, 4), before=self._editable_pptx_row_anchor)
        else:
            self.editable_pptx_row.pack_forget()

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
            "ignore_framebreaks": bool(self.ignore_framebreaks_var.get()),
            "editable_pptx": bool(self.editable_pptx_var.get()),
            "output_path": out_path,
        }
        self.window.destroy()
