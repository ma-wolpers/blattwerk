"""Shared base and shortcut-help helpers of the export dialogs.

Split out of export_dialog.py (file-size rule); bodies unchanged."""

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui
from bw_gui.shortcuts import compose_hover_text as compose_shared_hover_text

from .ui_theme import apply_window_theme, configure_ttk_theme


def _localize_shortcut_label(shortcut_label: str) -> str:
    """Map shared shortcut wording to existing German UI labels."""

    text = str(shortcut_label or "")
    return text.replace("Ctrl", "Strg").replace("Escape", "Esc")


def _shortcut_help_entry(description: str, sequence: str | None) -> str:
    """Build one compact shortcut help entry via the shared formatter."""

    desc = str(description or "").strip()
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
