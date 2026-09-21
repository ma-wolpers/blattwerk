"""Document tab strip: a horizontally scrollable notebook with an always-visible close button."""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets
from bw_gui.widgets import ScrollableFrame

_TAB_SCAN_STEP_PX = 2
_TAB_SCAN_Y_PX = 4


class BlattwerkAppTabStripMixin:
    """Baut die Dokument-Tab-Leiste und hält den aktiven Tab im sichtbaren Bereich."""

    def _build_document_tab_strip(self, parent) -> None:
        """Build the close button and the scrollable notebook inside *parent*.

        Layout rationale: ``pack`` allocates space in call order, so the close
        button is packed first (``side="right"``) and can never be pushed out of
        view. The notebook lives in a horizontal ``ScrollableFrame`` (bw-gui's
        scroll SSOT, see ``docs/SCROLLABILITY_CONTRACT.md``) that gets whatever
        space is left: with few tabs it shrink-wraps them, with many tabs it is
        clipped and scrolls (scrollbar below, mouse wheel over the strip) instead
        of squeezing the tab headers or the button.

        Args:
            parent: The control-strip row that hosts the strip and the button.

        Side effects:
            Sets ``self.document_tab_strip`` and ``self.document_notebook`` and
            binds ``<<NotebookTabChanged>>`` (tab-state switch, then scroll the
            newly selected tab into view).
        """
        widgets.Button(
            parent,
            text="×",
            width=3,
            style="SecondaryAction.TButton",
            command=self.close_active_document_tab,
        ).pack(side="right", padx=(8, 0))

        self.document_tab_strip = ScrollableFrame(parent, orient="horizontal", style="ControlStrip.TFrame")
        self.document_tab_strip.content.configure(style="ControlStrip.TFrame")
        self.document_tab_strip.pack(side="left", fill="x", expand=True)

        self.document_notebook = widgets.Notebook(self.document_tab_strip.content, style="ControlStrip.TNotebook")
        self.document_notebook.pack(side="left")
        self.document_notebook.bind("<<NotebookTabChanged>>", self._on_document_tab_changed)
        self.document_notebook.bind("<<NotebookTabChanged>>", self._schedule_scroll_active_tab_into_view, add="+")

    def _document_tab_x_range(self, tab_index: int) -> tuple[int, int] | None:
        """Return the ``(left, right)`` x-span of a tab in notebook coordinates.

        ``ttk.Notebook`` has no per-tab bounding-box command (``Misc.bbox`` is the
        *grid* bbox and is unrelated), so the span is recovered by probing
        ``index("@x,y")`` across the tab row. The step keeps the probe cheap
        (a few hundred Tcl calls at most) and costs at most one step of
        inaccuracy at the right edge, which is added back.

        Args:
            tab_index: Position of the tab within ``document_notebook.tabs()``.

        Returns:
            ``(left, right)`` in pixels, or ``None`` if the tab is not laid out.
        """
        notebook = self.document_notebook
        left: int | None = None
        right: int | None = None
        for x_pos in range(0, notebook.winfo_width(), _TAB_SCAN_STEP_PX):
            try:
                hit = notebook.index(f"@{x_pos},{_TAB_SCAN_Y_PX}")
            except ui.TclError:
                continue
            if hit != tab_index:
                continue
            if left is None:
                left = x_pos
            right = x_pos
        if left is None or right is None:
            return None
        return left, right + _TAB_SCAN_STEP_PX

    def _schedule_scroll_active_tab_into_view(self, _event=None) -> None:
        """Defer the scroll until Tk has laid out a just-added/selected tab."""
        self.root.after_idle(self._scroll_active_tab_into_view)

    def _scroll_active_tab_into_view(self) -> None:
        """Scroll the tab strip just far enough to show the selected tab (no-op if visible)."""
        strip = getattr(self, "document_tab_strip", None)
        notebook = getattr(self, "document_notebook", None)
        if strip is None or notebook is None:
            return
        strip.update_idletasks()
        selected = notebook.select()
        if not selected:
            return
        span = self._document_tab_x_range(notebook.index(selected))
        if span is None:
            return
        offset = notebook.winfo_x()
        strip.see_x_range(offset + span[0], offset + span[1])
