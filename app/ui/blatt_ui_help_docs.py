"""GUI mixin module."""

from __future__ import annotations

from pathlib import Path

import markdown

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.theming._theme_manager import mix_hex
from bw_gui.widgets import configure_doc_text_tags, html_to_events, render_events_into_text

from .ui_theme import apply_window_theme, configure_ttk_theme, get_theme

HELP_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "nutzer"
HELP_DOCS_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def _help_doc_label(path: Path) -> str:
    """Derives a display label from a doc's first H1 heading, falling back to its filename."""

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except OSError:
        pass
    return path.stem.replace("_", " ").title()


def discover_help_docs(directory: Path) -> list[tuple[str, Path]]:
    """Returns (label, path) pairs for every ``*.md`` file directly in *directory*.

    Sorted by filename for a stable, predictable order. Returns an empty list
    (never raises) if *directory* is missing -- the popup must still open and
    show a friendly message rather than crash on a broken installation.
    """

    if not directory.is_dir():
        return []
    return [(_help_doc_label(path), path) for path in sorted(directory.glob("*.md"))]


class BlattwerkAppHelpDocsMixin:
    """Zeigt die Nutzer-Dokumentation (``docs/nutzer/*.md``) in einem eigenen Popup."""

    def open_help_docs_dialog(self) -> None:
        """Opens (or focuses) the documentation popup, listing all docs/nutzer/ guides."""

        if self.help_docs_window is not None:
            try:
                if int(self.help_docs_window.winfo_exists()):
                    self.help_docs_window.deiconify()
                    self.help_docs_window.lift()
                    self.help_docs_window.focus_force()
                    return
            except Exception:
                self.help_docs_window = None

        window = ui.Toplevel(self.root)
        window.title("Dokumentation")
        window.geometry("1000x680")
        window.minsize(760, 480)
        self._track_popup_window(window, policy_id="dialog.non_blocking")
        window.protocol("WM_DELETE_WINDOW", self._close_help_docs_window)

        body = widgets.Frame(window, padding=10)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        side = widgets.Frame(body)
        side.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        side.rowconfigure(0, weight=1)

        listbox = ui.Listbox(side, exportselection=False, height=28, width=34)
        listbox.grid(row=0, column=0, sticky="ns")
        side_scroll = widgets.Scrollbar(side, orient="vertical", command=listbox.yview)
        side_scroll.grid(row=0, column=1, sticky="ns")
        listbox.configure(yscrollcommand=side_scroll.set)
        listbox.bind("<<ListboxSelect>>", self._on_help_doc_selected)

        content = widgets.Frame(body)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        text = ui.Text(content, wrap="word", borderwidth=0, highlightthickness=0, state="disabled")
        text.grid(row=0, column=0, sticky="nsew")
        text_scroll = widgets.Scrollbar(content, orient="vertical", command=text.yview)
        text_scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=text_scroll.set)

        self.help_docs_window = window
        self.help_docs_listbox = listbox
        self.help_docs_text = text
        self.help_docs_catalog = discover_help_docs(HELP_DOCS_DIR)

        self._configure_help_docs_style()

        if self.help_docs_catalog:
            for label, _path in self.help_docs_catalog:
                listbox.insert("end", label)
            listbox.selection_set(0)
            self._render_help_doc(self.help_docs_catalog[0][1])
        else:
            self._render_help_docs_empty_state()

    def _close_help_docs_window(self) -> None:
        """Closes the documentation popup and resets its state."""

        if self.help_docs_window is not None and self.help_docs_window.winfo_exists():
            self.help_docs_window.destroy()
        self.help_docs_window = None
        self.help_docs_listbox = None
        self.help_docs_text = None
        self.help_docs_catalog = []

    def _on_help_doc_selected(self, _event=None) -> None:
        """Renders the doc selected in the sidebar listbox."""

        listbox = self.help_docs_listbox
        if listbox is None:
            return
        selection = listbox.curselection()
        if not selection or selection[0] >= len(self.help_docs_catalog):
            return
        _label, path = self.help_docs_catalog[selection[0]]
        self._render_help_doc(path)

    def _render_help_doc(self, path: Path) -> None:
        """Converts one markdown doc to HTML and renders it into the popup's Text widget."""

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as error:
            self._render_help_docs_message(f"Datei konnte nicht gelesen werden: {error}")
            return

        html = markdown.Markdown(extensions=HELP_DOCS_MARKDOWN_EXTENSIONS).convert(raw_text)
        events = html_to_events(html)

        text = self.help_docs_text
        if text is None:
            return
        text.configure(state="normal")
        text.delete("1.0", "end")
        render_events_into_text(text, events, on_copy=self._copy_help_doc_snippet)
        text.configure(state="disabled")

    def _render_help_docs_empty_state(self) -> None:
        """Shown when docs/nutzer/ has no markdown files -- never a crash."""

        self._render_help_docs_message(
            "Keine Dokumentation gefunden -- der Ordner docs/nutzer/ ist leer oder fehlt."
        )

    def _render_help_docs_message(self, message: str) -> None:
        """Replaces the Text widget content with a single plain status message."""

        text = self.help_docs_text
        if text is None:
            return
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", message, ("body",))
        text.configure(state="disabled")

    def _copy_help_doc_snippet(self, code: str) -> None:
        """Copies one code block's raw text to the clipboard, confirmed via the status bar."""

        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.status_var.set("Code in Zwischenablage kopiert")

    def _help_docs_text_style(self, theme_key: str | None) -> dict:
        """Builds the plain color/font dict bw_gui's doc renderer expects, from the app theme."""

        theme = get_theme(theme_key)
        return {
            "fg_primary": theme["fg_primary"],
            "bg_surface": theme["bg_surface"],
            "bg_code": mix_hex(theme["border"], theme["bg_surface"], 0.35),
            "font_family": "Segoe UI",
            "mono_font_family": "Consolas",
            "base_size": 10,
        }

    def _configure_help_docs_style(self) -> None:
        """Applies window chrome and Text tag colors/fonts from the currently active theme."""

        window = self.help_docs_window
        if window is None or not window.winfo_exists():
            return
        theme_key = self.theme_var.get() if hasattr(self, "theme_var") else None
        apply_window_theme(window, theme_key)
        configure_ttk_theme(window, theme_key)
        if self.help_docs_text is not None:
            configure_doc_text_tags(self.help_docs_text, self._help_docs_text_style(theme_key))

    def _apply_help_docs_theme(self) -> None:
        """Theme-change hook (called from ``_apply_theme``): re-styles and re-renders."""

        if self.help_docs_window is None or not self.help_docs_window.winfo_exists():
            return
        self._configure_help_docs_style()

        if not self.help_docs_catalog:
            self._render_help_docs_empty_state()
            return
        listbox = self.help_docs_listbox
        selection = listbox.curselection() if listbox is not None else ()
        index = selection[0] if selection else 0
        if index >= len(self.help_docs_catalog):
            index = 0
        self._render_help_doc(self.help_docs_catalog[index][1])
