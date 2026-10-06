"""Einklappbare Editor-Panels „Diagnostik“, „Klausur-Übersicht“ und „Struktur“.

Alle drei sind `bw_gui.widgets.CollapsibleSection`s (Baustein aus bw-gui, nicht
lokal). Zwei unabhängige Achsen:

* **Einklappen** (``collapsed``): nur per Nutzerklick; nur dann wird der Zustand
  in ``ui_settings["editor_panels_collapsed"]`` gespeichert.
* **Sichtbarkeit** (gepackt oder nicht): Klausur-Übersicht nur bei `.kbw`,
  „Struktur“ ggf. per `outline_visible_on_start` ausgeblendet. Ein- und
  Ausblenden rührt ``collapsed`` nie an -- beim Wiedereinblenden gilt der
  gespeicherte Zustand weiter.

Reihenfolge immer: Diagnostik -> [Klausur-Übersicht] -> Struktur.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import CollapsibleSection

EDITOR_PANELS_SETTINGS_KEY = "editor_panels_collapsed"
PANEL_DIAGNOSTICS = "diagnostics"
PANEL_EXAM_OVERVIEW = "exam_overview"
PANEL_OUTLINE = "outline"
EDITOR_PANEL_KEYS = (PANEL_DIAGNOSTICS, PANEL_EXAM_OVERVIEW, PANEL_OUTLINE)
PANEL_PACK_OPTIONS = {"fill": "x", "padx": 8, "pady": (0, 8)}


def normalize_editor_panels_collapsed(raw) -> dict[str, bool]:
    """Kanonisches Schema ``{panel: bool}`` aus beliebigen gespeicherten Werten (wirft nie).

    Fehlender oder kaputter Gesamtschlüssel, fehlende Unterkeys und Nicht-``bool``-
    Werte bedeuten „offen“; unbekannte Keys werden verworfen.
    """
    source = raw if isinstance(raw, dict) else {}
    return {key: source.get(key) is True for key in EDITOR_PANEL_KEYS}


class BlattwerkEditorPanelsMixin:
    """Baut die einklappbaren Editor-Panels und speichert ihren Einklapp-Zustand."""

    def _editor_panels_state(self) -> dict[str, bool]:
        settings = getattr(self, "ui_settings", None)
        raw = settings.get(EDITOR_PANELS_SETTINGS_KEY) if isinstance(settings, dict) else None
        return normalize_editor_panels_collapsed(raw)

    def _build_editor_section(self, parent, key: str, title: str) -> CollapsibleSection:
        """Legt ein einklappbares Panel an (noch nicht gepackt)."""
        sections = self.__dict__.setdefault("_editor_sections", {})
        section = CollapsibleSection(
            parent,
            title,
            collapsed=self._editor_panels_state()[key],
            on_toggle=lambda requested, panel=key: self._on_editor_panel_toggled(panel, requested),
        )
        sections[key] = section
        return section

    def _editor_section(self, key: str) -> CollapsibleSection | None:
        return self.__dict__.get("_editor_sections", {}).get(key)

    def _on_editor_panel_toggled(self, key: str, collapsed: bool) -> None:
        """Nutzerklick: Zustand kanonisch in die UI-Settings schreiben und speichern."""
        state = self._editor_panels_state()
        state[key] = bool(collapsed)
        if isinstance(getattr(self, "ui_settings", None), dict):
            self.ui_settings[EDITOR_PANELS_SETTINGS_KEY] = state
        save = getattr(self, "_save_ui_settings", None)
        if callable(save):
            save()

    def _build_editor_outline_panel(self, parent, preferences) -> None:
        """Panel „Struktur“ (Gliederungsliste); `outline_visible_on_start=False` blendet es ganz aus."""
        outline_section = self._build_editor_section(parent, PANEL_OUTLINE, "Struktur")
        if bool(preferences.get("outline_visible_on_start", True)):
            outline_section.pack(**PANEL_PACK_OPTIONS)
        outline_frame = outline_section.content
        outline_frame.columnconfigure(0, weight=1)

        self.editor_outline_listbox = ui.Listbox(
            outline_frame,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            height=6,
        )
        self.editor_outline_listbox.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(6, 8))
        self.editor_outline_listbox.bind("<<ListboxSelect>>", self._on_editor_outline_selected)
        self.editor_outline_listbox.bind("<ButtonRelease-1>", self._on_editor_outline_click)

        outline_scrollbar = widgets.Scrollbar(
            outline_frame,
            orient="vertical",
            command=self.editor_outline_listbox.yview,
        )
        outline_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(6, 8))
        self.editor_outline_listbox.configure(yscrollcommand=outline_scrollbar.set)

    def _show_exam_overview_section(self, visible: bool) -> None:
        """Blendet die Klausur-Übersicht ein/aus -- immer zwischen Diagnostik und Struktur."""
        section = self._editor_section(PANEL_EXAM_OVERVIEW)
        if section is None:
            return
        if not visible:
            if section.winfo_manager():
                section.pack_forget()
            return
        if section.winfo_manager():
            return
        outline = self._editor_section(PANEL_OUTLINE)
        if outline is not None and outline.winfo_manager():
            section.pack(**PANEL_PACK_OPTIONS, before=outline)
        else:
            section.pack(**PANEL_PACK_OPTIONS)
