"""Editor-Panel „Klausur-Übersicht“: Punkte und AFB-Verteilung live (nur `.kbw`).

Zeigt ausschließlich das Ergebnis von `exam_analysis.analyze_exam` in derselben
Textform wie der Erwartungshorizont (`format_analysis_lines`): Prozente immer
bezogen auf die Gesamtpunktzahl und nur bei vollständiger Auswertung; ohne
`--hm` keine Teilzeilen.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import widgets

from ..core.blatt_kern_shared import parse_blocks
from ..core.exam_analysis import analyze_exam, format_analysis_lines
from ..core.frontmatter import content_after_frontmatter


class BlattwerkExamOverviewMixin:
    """Baut und aktualisiert die Klausur-Übersicht unter der Diagnostik."""

    def _build_exam_overview_panel(self, parent) -> None:
        self._exam_overview_frame = widgets.LabelFrame(parent, text="Klausur-Übersicht")
        self._exam_overview_label = widgets.Label(self._exam_overview_frame, text="", anchor="w", justify="left")
        self._exam_overview_label.pack(fill="x", padx=8, pady=(4, 6))

    def _refresh_exam_overview(self, text: str, document_type: str | None) -> None:
        """Zeigt das Panel nur bei Klausuren und füllt es mit der aktuellen Auswertung."""
        frame = getattr(self, "_exam_overview_frame", None)
        if frame is None:
            return
        if document_type != "exam":
            if frame.winfo_manager():
                frame.pack_forget()
            return
        try:
            content, _line = content_after_frontmatter(text)
            analysis = analyze_exam(parse_blocks(content.strip()), document_type)
            summary = "\n".join(format_analysis_lines(analysis))
        except Exception as error:  # Auswertung darf das Tippen nie stören
            summary = f"Auswertung nicht möglich: {error}"
        self._exam_overview_label.configure(text=summary)
        if not frame.winfo_manager():
            frame.pack(fill="x", padx=8, pady=(0, 8))
