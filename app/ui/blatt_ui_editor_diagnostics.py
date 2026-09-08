"""Editor mixin for the "Diagnostik" panel: live diagnostics list and line markers.

Mechanically extracted from `blatt_ui_editor.py` (Schritt 1 of the
"Warnungen abhaken"-Feature, siehe `docs/intern/DEVELOPMENT_LOG.md`) --
pure move, no behavior change. Kept as its own mixin so the
acknowledgment feature (Schritt 2/3) has a focused, sub-300-line home
instead of growing the already large editor mixin further.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui, widgets

import re

from ..core.blatt_kern_shared import build_block_index_line_map
from ..core.document_diagnostics import inspect_document_text
from ..core.document_types import DOCUMENT_TYPE_KURZENTWURF


class BlattwerkAppEditorDiagnosticsMixin:
    """Adds the "Diagnostik" panel (list + line markers) below the editor."""

    def _build_editor_diagnostics_panel(self, parent):
        """Creates the diagnostics list widget and wires selection/click events."""

        diagnostics_frame = widgets.LabelFrame(parent, text="Diagnostik")
        diagnostics_frame.pack(fill="x", padx=8, pady=(0, 8))
        diagnostics_frame.columnconfigure(2, weight=1)

        widgets.Label(diagnostics_frame, text="Zeile").grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(6, 4))
        widgets.Label(diagnostics_frame, text="Code").grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(6, 4))
        widgets.Label(diagnostics_frame, text="Hinweis").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=(6, 4))

        self.editor_diagnostics_listbox = ui.Listbox(
            diagnostics_frame,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            height=6,
        )
        self.editor_diagnostics_listbox.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self.editor_diagnostics_listbox.bind("<<ListboxSelect>>", self._on_editor_diagnostic_selected)
        self.editor_diagnostics_listbox.bind("<ButtonRelease-1>", self._on_editor_diagnostic_click)

        diagnostics_scrollbar = widgets.Scrollbar(
            diagnostics_frame,
            orient="vertical",
            command=self.editor_diagnostics_listbox.yview,
        )
        diagnostics_scrollbar.grid(row=1, column=3, sticky="ns", padx=(0, 8), pady=(0, 8))
        self.editor_diagnostics_listbox.configure(yscrollcommand=diagnostics_scrollbar.set)
        diagnostics_frame.rowconfigure(1, weight=1)

    def _queue_editor_diagnostics(self, immediate: bool = False):
        """Schedules a debounced diagnostics refresh for current editor text."""

        preferences = getattr(self, "user_preferences", {})
        if not bool(preferences.get("diagnostics_live_enabled", True)) and not immediate:
            return

        if self.editor_widget is None:
            return

        if self._editor_diagnostics_after_id is not None:
            self.root.after_cancel(self._editor_diagnostics_after_id)
            self._editor_diagnostics_after_id = None

        if immediate:
            self._refresh_editor_diagnostics()
            return

        self._editor_diagnostics_after_id = self.root.after(
            self._editor_diagnostics_delay_ms,
            self._refresh_editor_diagnostics,
        )

    def _refresh_editor_diagnostics(self):
        """Collects diagnostics and updates list + line markers in the editor."""

        self._editor_diagnostics_after_id = None

        if self.editor_widget is None:
            return

        text = self.editor_widget.get("1.0", "end-1c")
        preferences = getattr(self, "user_preferences", {})
        detection_mode = preferences.get("document_type_detection_mode", "yaml_keys")
        try:
            source_path = None
            if hasattr(self, "_active_document_tab_state"):
                try:
                    tab_state = self._active_document_tab_state()
                except Exception:
                    tab_state = None
                if isinstance(tab_state, dict):
                    raw_path = str(tab_state.get("path", "") or "").strip()
                    if raw_path:
                        source_path = raw_path

            inspected = inspect_document_text(text, detection_mode=detection_mode, source_path=source_path)
        except Exception:
            self._set_editor_diagnostics([])
            return

        index_line_map = self._build_editor_diagnostics_line_map(text)
        structure = self._analyze_editor_block_structure(text)
        self._editor_block_pairs_cache = list(structure["pairs"])
        items = []
        for diagnostic in inspected.diagnostics:
            if diagnostic.line_number is not None:
                line = diagnostic.line_number
            elif diagnostic.block_index is None:
                line = 1
            else:
                line = index_line_map.get(diagnostic.block_index, 1)

            items.append(
                {
                    "line": max(1, int(line)),
                    "code": diagnostic.code,
                    "severity": diagnostic.severity,
                    "message": diagnostic.message,
                }
            )

        if inspected.document_type != DOCUMENT_TYPE_KURZENTWURF:
            for line_no in structure["close_suffix_lines"]:
                items.append(
                    {
                        "line": max(1, int(line_no)),
                        "code": "SY001",
                        "severity": "error",
                        "message": "Nach schließendem ::: ist kein weiterer Text erlaubt.",
                    }
                )

            for line_no in structure["unclosed_open_lines"]:
                items.append(
                    {
                        "line": max(1, int(line_no)),
                        "code": "SY002",
                        "severity": "error",
                        "message": "Block ist geöffnet, aber nicht mit ::: geschlossen.",
                    }
                )

        self._set_editor_diagnostics(items)

    @staticmethod
    def _analyze_editor_block_structure(markdown_text: str) -> dict:
        """Parses block openings/closings to drive mapping, outline and pair matching."""

        pairs = []
        close_suffix_lines = []
        block_stack = []
        lines = markdown_text.splitlines()

        self_closing_pattern = re.compile(r"^:::(\w+)(.*?):::$")
        opening_pattern = re.compile(r"^:::(\w+)(.*)$")

        for line_no, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue

            if self_closing_pattern.match(stripped):
                continue

            opening_match = opening_pattern.match(stripped)
            if opening_match:
                block_stack.append((opening_match.group(1).lower(), line_no))
                continue

            if stripped.startswith(":::") and block_stack:
                _open_type, open_line = block_stack.pop()
                pairs.append((open_line, line_no))
                if stripped != ":::":
                    close_suffix_lines.append(line_no)

        unclosed_open_lines = [line_no for _block_type, line_no in block_stack]

        return {
            "pairs": pairs,
            "close_suffix_lines": close_suffix_lines,
            "unclosed_open_lines": unclosed_open_lines,
        }

    def _build_editor_diagnostics_line_map(self, markdown_text: str) -> dict[int, int]:
        """Maps validator block indices to original editor line numbers."""

        content_text, content_base_line = self._extract_validation_content_and_base_line(markdown_text)
        if not content_text:
            return {}

        local_index_map = build_block_index_line_map(content_text)
        return {
            block_index: content_base_line + max(0, int(local_line) - 1)
            for block_index, local_line in local_index_map.items()
        }

    @staticmethod
    def _extract_validation_content_and_base_line(markdown_text: str) -> tuple[str, int]:
        """Returns validator content plus 1-based base line in original markdown."""

        lines = markdown_text.splitlines(keepends=True)
        content_start_line = 1
        content_raw = markdown_text

        if lines and lines[0].strip() == "---":
            for line_index in range(1, len(lines)):
                if lines[line_index].strip() == "---":
                    content_start_line = line_index + 2
                    content_raw = "".join(lines[line_index + 1 :])
                    break

        content_for_validation = content_raw.strip()
        if not content_for_validation:
            return "", content_start_line

        leading_removed_chars = len(content_raw) - len(content_raw.lstrip())
        leading_removed_text = content_raw[:leading_removed_chars]
        leading_removed_lines = leading_removed_text.count("\n")
        base_line = content_start_line + leading_removed_lines
        return content_for_validation, max(1, base_line)

    def _set_editor_diagnostics(self, items):
        """Renders diagnostics into listbox and colored line tags."""

        preferences = getattr(self, "user_preferences", {})
        threshold = str(preferences.get("diagnostics_severity_threshold", "warning"))
        threshold_rank = {"error": 2, "warning": 1, "info": 0}
        min_rank = threshold_rank.get(threshold, 1)
        filtered_items = []
        for item in items:
            severity = str(item.get("severity", "warning"))
            if threshold_rank.get(severity, 1) >= min_rank:
                filtered_items.append(item)

        self._editor_diagnostics_items = list(filtered_items)

        if self.editor_widget is not None:
            self.editor_widget.tag_remove("diag_warning", "1.0", "end")
            self.editor_widget.tag_remove("diag_error", "1.0", "end")

            line_severity = {}
            for item in self._editor_diagnostics_items:
                existing = line_severity.get(item["line"])
                severity = item["severity"]
                if existing == "error":
                    continue
                if severity == "error" or existing is None:
                    line_severity[item["line"]] = severity

            last_line = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
            for line, severity in line_severity.items():
                safe_line = max(1, min(int(line), max(1, last_line)))
                if severity != "error" and not bool(preferences.get("syntax_warning_highlight_enabled", True)):
                    continue
                tag_name = "diag_error" if severity == "error" else "diag_warning"
                start = f"{safe_line}.0"
                end = f"{safe_line}.0 lineend+1c"
                self.editor_widget.tag_add(tag_name, start, end)

        if self.editor_diagnostics_listbox is None:
            return

        self.editor_diagnostics_listbox.delete(0, "end")
        if not self._editor_diagnostics_items:
            self.editor_diagnostics_listbox.insert("end", "Keine Diagnostik")
            return

        for item in self._editor_diagnostics_items:
            severity_label = "Fehler" if item["severity"] == "error" else "Warnung"
            self.editor_diagnostics_listbox.insert(
                "end",
                f"{item['line']:>4}  {item['code']:<5}  {severity_label}: {item['message']}",
            )

    def _on_editor_diagnostic_selected(self, _event=None):
        """Jumps to selected diagnostic line and moves cursor to that location."""

        if self.editor_widget is None or self.editor_diagnostics_listbox is None:
            return

        selection = self.editor_diagnostics_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self._editor_diagnostics_items):
            return

        line = self._editor_diagnostics_items[index]["line"]
        line_index = f"{max(1, int(line))}.0"
        self.editor_widget.mark_set("insert", line_index)
        self.editor_widget.see(line_index)
        self.editor_widget.focus_set()
        self._refresh_editor_block_pair_highlight()

    def _on_editor_diagnostic_click(self, _event=None):
        """Ensures click on already selected diagnostic still triggers jump."""

        if hasattr(self, "root"):
            self.root.after_idle(self._on_editor_diagnostic_selected)
