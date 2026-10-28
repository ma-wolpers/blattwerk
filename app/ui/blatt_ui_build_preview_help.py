"""Vorschau-Leiste: Gruppe „Lernhilfen“ (Anhang Aus / Eine Seite / Einzeln).

Eigenes Mixin, weil `blatt_ui_build_preview.py` an der 300-Zeilen-Grenze liegt;
es bündelt alles zu diesem einen Bedienelement: Aufbau, Sichtbarkeit je
Dokumenttyp und Aktivierung je nach vorhandenen Lernhilfen. Den *wirksamen*
Wert für Vorschau und Exportdialog liefert `_effective_help_appendix` im
Vorschau-Toolbar-Mixin (neben `_preview_capability_active`).
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import widgets

from ..core.help_cards_appendix import HELP_APPENDIX_MODES, help_appendix_label


class BlattwerkPreviewHelpAppendixMixin:
    """Lernhilfen-Anhang in der Vorschau (BlattwerkApp-Mixin)."""

    def _build_preview_help_appendix_group(self, format_section):
        """Baut die Gruppe „Lernhilfen:“ mit einem Radio je Anhang-Variante.

        Die Radios schreiben in `preview_help_appendix_var` und lösen
        `refresh_preview` aus; Texte kommen aus `help_cards_appendix`
        (Kurzform). Ob die Gruppe sichtbar ist, entscheidet
        `_apply_preview_help_appendix_controls`.

        Args:
            format_section: Container der Format-Zeile (responsive Gruppen).

        Returns:
            Den Gruppen-Frame zum Registrieren als optionale Gruppe.
        """
        group = self.format_group_help = widgets.Frame(format_section)
        widgets.Separator(group, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        widgets.Label(group, text="Lernhilfen:").pack(side="left")
        self.preview_help_appendix_buttons = []
        for mode in HELP_APPENDIX_MODES:
            button = widgets.Radiobutton(
                group,
                text=help_appendix_label(mode, short=True),
                value=mode,
                variable=self.preview_help_appendix_var,
                command=self.refresh_preview,
            )
            button.pack(side="left", padx=(6, 0))
            self.preview_help_appendix_buttons.append(button)
        return group

    def _apply_preview_help_appendix_controls(self, show: bool) -> None:
        """Blendet die Gruppe ein oder aus (Capability `show_help_appendix`).

        Ausgeblendet für Typen ohne Anhang (Präsentation, Kurzentwurf, …) und in
        der Erwartungshorizont-Ansicht, die ein eigenes Layout hat.
        """
        group = getattr(self, "format_group_help", None)
        if group is not None:
            self._set_responsive_group_hidden(group, not show)

    def _set_preview_help_appendix_enabled(self, has_lernhilfen: bool) -> None:
        """Aktiviert die Radios nur, wenn das Dokument sichtbare Lernhilfen hat."""
        for button in getattr(self, "preview_help_appendix_buttons", []):
            button.configure(state="normal" if has_lernhilfen else "disabled")
