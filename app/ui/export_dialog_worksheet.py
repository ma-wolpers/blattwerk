"""Export dialog for worksheets.

Split out of export_dialog.py (file-size rule); bodies unchanged."""

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import Checkbox

from ..core.help_cards_appendix import (
    HELP_APPENDIX_MODES,
    HELP_APPENDIX_NONE,
    HELP_APPENDIX_SHEET,
    HELP_APPENDIX_SINGLE,
    coerce_help_appendix,
    help_appendix_label,
)
from .dialog_services import filedialog, messagebox
from .ui_theme import get_theme
from .export_dialog_base import CANCEL_KEY, EXPORT_KEY, _BaseExportDialog, _build_shortcuts_help_text, _shortcut_help_entry


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
        allow_expectation_horizon: bool = False,
        default_help_appendix: str = HELP_APPENDIX_NONE,
        allow_help_appendix: bool = False,
    ):
        """Baut den Dialog und zeigt ihn modal an; das Ergebnis steht danach in `result`.

        Args:
            default_mode: Vorauswahl „Inhalt“ (aus der Vorschau-Ansicht).
            default_help_appendix: Vorauswahl „Lernhilfen mit exportieren“
                (`help_cards_appendix.HELP_APPENDIX_*`, aus der Vorschau): bei
                `none` ist die Checkbox aus und die Variante steht auf „eine
                Seite“, sonst ist die Checkbox an und die Variante gewählt.
            allow_help_appendix: Zeile überhaupt anzeigen (Typ mit Anhang und
                sichtbare Lernhilfen vorhanden).
        """
        super().__init__(parent, input_path, theme_key, initial_output_dir=initial_output_dir)
        self.allow_expectation_horizon = bool(allow_expectation_horizon)
        self.worksheet_label = str(worksheet_label or "Aufgaben")
        self.solution_label = str(solution_label or "Loesung")
        self.solution_suffix = str(solution_suffix or "_loesung")
        self.allow_mode_selection = bool(allow_mode_selection)

        self.format_var = ui.StringVar(value=default_format)
        self.mode_var = ui.StringVar(value=default_mode)
        self.allow_help_appendix = bool(allow_help_appendix)
        preselected = coerce_help_appendix(default_help_appendix)
        self.help_appendix_enabled_var = ui.BooleanVar(value=preselected != HELP_APPENDIX_NONE)
        self.help_appendix_variant_var = ui.StringVar(
            value=preselected if preselected != HELP_APPENDIX_NONE else HELP_APPENDIX_SHEET
        )
        self.help_appendix_controls = []

        self.window.title("Arbeitsblatt exportieren")
        self._build_ui()
        self._bind_shortcuts()
        # Wie ein Moduswechsel: bei Vorauswahl „Erwartungshorizont“ (aus der Vorschau)
        # sofort auf PDF/HTML beschränken, dann den Ausgabenamen vorschlagen.
        self._on_mode_changed()
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
            if self.allow_expectation_horizon:
                widgets.Radiobutton(
                    mode_row, text="Erwartungshorizont", value="expectation", variable=self.mode_var,
                    command=self._on_mode_changed,
                ).pack(side="left", padx=(12, 0))
        else:
            self.mode_var.set("worksheet")

        if self.allow_help_appendix:
            self._build_help_appendix_rows(outer)

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
            text=self._build_shortcuts_help_text(self.allow_mode_selection, self.allow_help_appendix),
        ).pack(anchor="w", padx=8, pady=6)

        self._set_shortcuts_help_visible(False)
        self.window.configure(bg=theme["bg_main"])

    @staticmethod
    def _build_shortcuts_help_text(allow_mode_selection: bool, allow_help_appendix: bool = False) -> str:
        """Hilfetext der Shortcuts; `G` (Lernhilfen) erscheint nur, wenn die Zeile angezeigt wird."""
        first_row = (
            ("Exportieren", EXPORT_KEY),
            ("Abbrechen", CANCEL_KEY),
        )
        help_entries = (_shortcut_help_entry("Lernhilfen", "G"),) if allow_help_appendix else ()
        if allow_mode_selection:
            first_line = _build_shortcuts_help_text(first_row)
            second_line = "   ".join(
                (
                    "A/L/B: Inhalt",
                    _shortcut_help_entry("Format wechseln", "P"),
                    _shortcut_help_entry("Durchsuchen", "D"),
                    *help_entries,
                )
            )
            return f"{first_line}\n{second_line}"
        second_row = (("Format wechseln", "P"), ("Durchsuchen", "D"))
        if allow_help_appendix:
            second_row += (("Lernhilfen", "G"),)
        return _build_shortcuts_help_text(first_row, second_row)

    def _extra_char_shortcuts(self):
        """A/L/B (and H with expectation horizon): choose the content; G: cycle the Lernhilfen appendix."""
        shortcuts = []
        if self.allow_mode_selection:
            rows = [("a", "worksheet"), ("l", "solution"), ("b", "both")]
            if self.allow_expectation_horizon:
                rows.append(("h", "expectation"))
            shortcuts.extend(
                (KeySpec.char(key), f"mode.{mode}", lambda mode=mode: self._set_mode(mode)) for key, mode in rows
            )
        if self.allow_help_appendix:
            shortcuts.append((KeySpec.char("g"), "help_appendix.cycle", self._cycle_help_appendix))
        return tuple(shortcuts)

    def _build_help_appendix_rows(self, outer):
        """Zeile „Lernhilfen mit exportieren“ plus eingerückte Varianten-Radios.

        Die Radios sind nur bei gesetzter Checkbox aktiv; die ganze Zeile ist
        bei HTML und beim Erwartungshorizont gesperrt
        (`_sync_help_appendix_controls`).
        """
        check_row = widgets.Frame(outer)
        check_row.pack(fill="x", pady=(4, 0))
        widgets.Label(check_row, text="Lernhilfen:", width=15).pack(side="left")
        self.help_appendix_checkbox = Checkbox(
            check_row,
            text="Lernhilfen mit exportieren",
            variable=self.help_appendix_enabled_var,
            on_select=lambda _selected: self._sync_help_appendix_controls(),
        )
        self.help_appendix_checkbox.pack(side="left")
        self.help_appendix_hint = widgets.Label(check_row, text="(nur PDF/PNG)", style="Muted.TLabel")
        variant_row = widgets.Frame(outer)
        variant_row.pack(fill="x", pady=(2, 4))
        widgets.Label(variant_row, text="", width=17).pack(side="left")
        for mode in (HELP_APPENDIX_SHEET, HELP_APPENDIX_SINGLE):
            radio = widgets.Radiobutton(
                variant_row,
                text=help_appendix_label(mode, short=False),
                value=mode,
                variable=self.help_appendix_variant_var,
            )
            radio.pack(side="left", padx=(0, 12))
            self.help_appendix_controls.append(radio)

    def _help_appendix_possible(self) -> bool:
        """Ob die aktuelle Format-/Inhaltswahl einen Anhang erlaubt (nicht HTML, nicht Erwartungshorizont)."""
        return (
            self.allow_help_appendix
            and self.format_var.get() != "html"
            and self.mode_var.get() != "expectation"
        )

    def _sync_help_appendix_controls(self):
        """Passt Checkbox, Hinweis und Varianten-Radios an Format, Inhalt und Checkbox an."""
        checkbox = getattr(self, "help_appendix_checkbox", None)
        if checkbox is None:
            return
        possible = self._help_appendix_possible()
        checkbox.configure(state="normal" if possible else "disabled")
        if possible:
            self.help_appendix_hint.pack_forget()
        elif not self.help_appendix_hint.winfo_manager():
            self.help_appendix_hint.pack(side="left", padx=(8, 0))
        radios_active = possible and bool(self.help_appendix_enabled_var.get())
        for radio in self.help_appendix_controls:
            radio.configure(state="normal" if radios_active else "disabled")

    def _selected_help_appendix(self) -> str:
        """Die gewählte Anhang-Variante für das Ergebnis (`none`, wenn aus oder nicht möglich)."""
        if not self._help_appendix_possible() or not self.help_appendix_enabled_var.get():
            return HELP_APPENDIX_NONE
        return coerce_help_appendix(self.help_appendix_variant_var.get())

    def _cycle_help_appendix(self):
        """G: Aus → eine Seite → eigene Seite → Aus (nur wenn ein Anhang möglich ist)."""
        if not self._help_appendix_possible():
            return
        position = HELP_APPENDIX_MODES.index(self._selected_help_appendix())
        following = HELP_APPENDIX_MODES[(position + 1) % len(HELP_APPENDIX_MODES)]
        self.help_appendix_enabled_var.set(following != HELP_APPENDIX_NONE)
        if following != HELP_APPENDIX_NONE:
            self.help_appendix_variant_var.set(following)
        self._sync_help_appendix_controls()

    def _set_mode(self, mode):
        """Select the export content *mode* and adapt the format choice."""
        if self.mode_var.get() != mode:
            self.mode_var.set(mode)
        self._on_mode_changed()

    def _on_mode_changed(self):
        """Erwartungshorizont gibt es nur als PDF oder HTML; die Formatwahl wird angepasst."""
        if self.format_var.get() not in self._allowed_formats():
            self.format_var.set("pdf")
        self._refresh_output_suggestion(force=True)

    def _allowed_formats(self):
        if self.mode_var.get() == "expectation":
            return ["pdf", "html"]
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
        """Schlägt den Ausgabenamen vor und gleicht die Lernhilfen-Zeile ab.

        Läuft nach jeder Format- oder Inhaltsänderung (Radios, `P`, `A/L/B/H`),
        deshalb hängt hier auch `_sync_help_appendix_controls` (HTML und
        Erwartungshorizont sperren den Anhang).
        """
        self._sync_help_appendix_controls()
        current = self.output_var.get().strip()
        if current and not force:
            return

        stem = self.input_path.with_suffix("")
        suffix = {"solution": self.solution_suffix, "expectation": "_erwartungshorizont"}.get(self.mode_var.get(), "")
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

        if self.format_var.get() not in self._allowed_formats():
            messagebox.showwarning("Format", "Der Erwartungshorizont gibt es nur als PDF oder HTML.", parent=self.window)
            return
        out_path = Path(out)
        if out_path.suffix.lower() != self._extension():
            out_path = out_path.with_suffix(self._extension())

        self.result = {
            "format": self.format_var.get(),
            "mode": self.mode_var.get(),
            "output_path": out_path,
            "help_appendix": self._selected_help_appendix(),
        }
        self.window.destroy()
