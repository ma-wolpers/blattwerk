"""Shared base and shortcut-help helpers of the export dialogs.

Split out of export_dialog.py (file-size rule); bodies unchanged."""

from pathlib import Path
from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts.key_spec import KeySpec
from bw_gui.runtime import WindowShortcutBinder, ui
from bw_gui.shortcuts import compose_hover_text as compose_shared_hover_text

from .local_keys import bind_actions
from .ui_theme import apply_window_theme, configure_ttk_theme


EXPORT_KEY = KeySpec.parse("Ctrl+E")
CANCEL_KEY = KeySpec.parse("Escape (tolerate: Shift)")
_ENTER_KEY = KeySpec.parse("Enter (tolerate: Shift)")


def _localize_shortcut_label(shortcut_label: str) -> str:
    """Map shared shortcut wording to existing German UI labels."""

    text = str(shortcut_label or "")
    return text.replace("Ctrl", "Strg").replace("Escape", "Esc")


def _shortcut_help_entry(description: str, shortcut: KeySpec | str | None) -> str:
    """Build one compact shortcut help entry via the shared formatter.

    Args:
        description: Action text.
        shortcut: The bound ``KeySpec`` (help and binding share it) or a display text.
    """

    desc = str(description or "").strip()
    merged = compose_shared_hover_text(desc, shortcut)
    marker = "\nShortcut: "
    if marker not in merged:
        return merged

    resolved_desc, resolved_shortcut = merged.split(marker, 1)
    shortcut = _localize_shortcut_label(resolved_shortcut.strip())
    if not resolved_desc:
        return shortcut
    return f"{shortcut}: {resolved_desc}"


def _build_shortcuts_help_text(*rows: tuple[tuple[str, KeySpec | str | None], ...]) -> str:
    """Compose multi-line shortcuts help text from action/shortcut rows."""

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

    def _bind_shortcuts(self):
        """Bind the dialog keys on a window binder of the dialog (bw-gui keyboard contract).

        Common to all export dialogs: Enter is swallowed (no accidental export),
        Ctrl+E exports, Escape cancels (both also while a text field has focus); the
        letter keys ``?``/D/P and the dialog-specific ones from
        :meth:`_extra_char_shortcuts` only act while no text field has focus - the
        binder's text-input gating replaces the former class-name check, which missed
        ttk entries.
        """
        keys = WindowShortcutBinder(self.window)
        always = ((_ENTER_KEY, "swallow_enter", lambda: None), (EXPORT_KEY, "confirm", self._confirm), (CANCEL_KEY, "cancel", self._cancel))
        bind_actions(keys, always, text=True, prefix="export")
        letters = (
            (KeySpec.char("?"), "help", self._toggle_shortcuts_help),
            (KeySpec.char("d"), "browse", self._pick_output),
            (KeySpec.char("p"), "format", self._cycle_export_format),
            *self._extra_char_shortcuts(),
        )
        bind_actions(keys, letters, text=False, prefix="export")

    def _extra_char_shortcuts(self):
        """Dialog-specific letter shortcuts ``(KeySpec, binding_id, action)``; none by default."""
        return ()

    def _cycle_export_format(self):
        """P: switch to the next allowed export format and refresh the output suggestion."""
        export_formats = self._allowed_formats()
        current = self.format_var.get()
        try:
            index = export_formats.index(current)
        except ValueError:
            index = 0
        self.format_var.set(export_formats[(index + 1) % len(export_formats)])
        self._refresh_output_suggestion(force=True)

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

    def _cancel(self):
        self.window.destroy()
