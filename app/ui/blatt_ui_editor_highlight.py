"""Schreibbereich: Tags, Syntax- und Blockpaar-Hervorhebung, Theme-Farben (BlattwerkApp-Mixin).

Aus ``blatt_ui_editor.py`` ausgelagert (300-Zeilen-Regel), Methoden unverändert."""

from __future__ import annotations

import re

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui

from ..core.control_markers import control_marker_line_match
from ..core.inline_markup.style_spans import STYLE_MARKER_REGEX
from ..core.struktogramm_parse import INDENTED_LINE_MARKER_RE, STRUKTOGRAMM_HEADER_RE
from .ui_theme import get_theme, is_dark_theme

_INLINE_STYLE_MARKER_PATTERN = re.compile(STYLE_MARKER_REGEX)
_LINE_MARKER_PATTERN = re.compile(r"^([§%&])(?=\s|$)")


def _struktogramm_content_lines(text_lines, pairs):
    """Zeilennummern (1-basiert) im Inhalt von Struktogramm-Blöcken.

    Dort stehen Zeilenmarker nach der Einrückung (`INDENTED_LINE_MARKER_RE`),
    überall sonst nur am absoluten Zeilenanfang. `pairs` sind die
    `(öffnende Zeile, schließende Zeile)`-Paare aus der Blockstrukturanalyse.
    """
    lines = set()
    for open_line, close_line in pairs:
        if 0 < open_line <= len(text_lines) and STRUKTOGRAMM_HEADER_RE.match(text_lines[open_line - 1]):
            lines.update(range(open_line + 1, close_line))
    return lines


_SYNTAX_TAGS = (
    "syn_frontmatter_delim",
    "syn_frontmatter_key",
    "syn_block_fence",
    "syn_block_type",
    "syn_option_key",
    "syn_option_value",
    "syn_marker",
    "syn_inline_style",
    "syn_control",
    "syn_block_close_error",
    "syn_block_pair",
)


class BlattwerkAppEditorHighlightMixin:
    """Schreibbereich: Tags, Syntax- und Blockpaar-Hervorhebung, Theme-Farben (BlattwerkApp-Mixin)."""

    def _configure_editor_diagnostic_tags(self):
        """Configures text tags for diagnostic line highlighting."""

        if self.editor_widget is None:
            return

        dark_theme = is_dark_theme(self.theme_var.get() if hasattr(self, "theme_var") else None)
        if dark_theme:
            self.editor_widget.tag_configure("diag_warning", background="#3F331F")
            self.editor_widget.tag_configure("diag_error", background="#4A2329")
        else:
            self.editor_widget.tag_configure("diag_warning", background="#fff4d8")
            self.editor_widget.tag_configure("diag_error", background="#ffe2e2")

    def _configure_editor_syntax_tags(self):
        """Configures text tags for syntax highlighting plus search-match highlighting in markdown editor."""

        if self.editor_widget is None:
            return

        theme = get_theme(self.theme_var.get() if hasattr(self, "theme_var") else None)
        dark_theme = is_dark_theme(self.theme_var.get() if hasattr(self, "theme_var") else None)

        if dark_theme:
            self.editor_widget.tag_configure("syn_frontmatter_delim", foreground="#4FC1FF")
            self.editor_widget.tag_configure("syn_frontmatter_key", foreground="#9CDCFE")
            self.editor_widget.tag_configure("syn_block_fence", foreground="#D7BA7D")
            self.editor_widget.tag_configure("syn_block_type", foreground="#C586C0")
            self.editor_widget.tag_configure("syn_option_key", foreground="#4EC9B0")
            self.editor_widget.tag_configure("syn_option_value", foreground="#CE9178")
            self.editor_widget.tag_configure("syn_marker", foreground="#F44747")
            self.editor_widget.tag_configure("syn_inline_style", foreground="#DCDCAA")
            self.editor_widget.tag_configure("syn_control", foreground="#D7BA7D")
            self.editor_widget.tag_configure("syn_block_close_error", background="#5A1F2A", foreground="#FF9DA4")
            self.editor_widget.tag_configure("syn_block_pair", background="#2C3744")
            self.editor_widget.tag_configure("search_match", background="#5C4A1E")
            self.editor_widget.tag_configure("search_match_current", background="#B36B00", foreground="#1A1A1A")
        else:
            self.editor_widget.tag_configure("syn_frontmatter_delim", foreground="#0b7285")
            self.editor_widget.tag_configure("syn_frontmatter_key", foreground="#1864ab")
            self.editor_widget.tag_configure("syn_block_fence", foreground="#b35c00")
            self.editor_widget.tag_configure("syn_block_type", foreground="#9c36b5")
            self.editor_widget.tag_configure("syn_option_key", foreground="#0b7285")
            self.editor_widget.tag_configure("syn_option_value", foreground="#8d6b00")
            self.editor_widget.tag_configure("syn_marker", foreground="#c92a2a")
            self.editor_widget.tag_configure("syn_inline_style", foreground="#5f3dc4")
            self.editor_widget.tag_configure("syn_control", foreground="#b35c00")
            self.editor_widget.tag_configure("syn_block_close_error", background="#ffe2e2", foreground="#8b0000")
            self.editor_widget.tag_configure("syn_block_pair", background=theme["accent_soft"])
            self.editor_widget.tag_configure("search_match", background="#fff3bf")
            self.editor_widget.tag_configure("search_match_current", background="#ffa94d", foreground="#1a1a1a")

    def _apply_editor_theme_widgets(self):
        """Applies theme colors to editor side widgets beyond the main text area."""

        theme = get_theme(self.theme_var.get() if hasattr(self, "theme_var") else None)
        dark_theme = is_dark_theme(self.theme_var.get() if hasattr(self, "theme_var") else None)

        border_hex = theme["border"]
        if dark_theme:
            border_hex = "#3A4654"

        listbox_kwargs = {
            "background": theme["bg_surface"],
            "foreground": theme["fg_primary"],
            "selectbackground": theme["accent_soft"],
            "selectforeground": theme["fg_primary"],
            "highlightthickness": 1,
            "highlightbackground": border_hex,
            "highlightcolor": theme["accent"],
            "relief": "flat",
            "borderwidth": 0,
        }

        self._apply_editor_diagnostics_theme_widgets()

        if self.editor_outline_listbox is not None:
            self.editor_outline_listbox.configure(**listbox_kwargs)

        if self._editor_completion_listbox is not None:
            self._editor_completion_listbox.configure(**listbox_kwargs)

        if self._editor_completion_popup is not None and self._editor_completion_popup.winfo_exists():
            try:
                self._editor_completion_popup.configure(
                    background=theme["bg_surface"],
                    highlightthickness=1,
                    highlightbackground=border_hex,
                )
            except ui.TclError:
                pass

    def _queue_editor_highlighting(self, immediate: bool = False):
        """Schedules syntax highlighting refresh with light debounce."""

        if self.editor_widget is None:
            return

        if self._editor_highlighting_after_id is not None:
            self.root.after_cancel(self._editor_highlighting_after_id)
            self._editor_highlighting_after_id = None

        if immediate:
            self._refresh_editor_highlighting()
            return

        self._editor_highlighting_after_id = self.root.after(
            self._editor_highlighting_delay_ms,
            self._refresh_editor_highlighting,
        )

    def _refresh_editor_highlighting(self):
        """Applies lightweight syntax highlighting to frontmatter and block headers."""

        self._editor_highlighting_after_id = None
        if self.editor_widget is None:
            return

        for tag_name in _SYNTAX_TAGS:
            self.editor_widget.tag_remove(tag_name, "1.0", "end")

        full_text = self.editor_widget.get("1.0", "end-1c")
        structure = self._analyze_editor_block_structure(full_text)
        closing_lines = {line_no for _open, line_no in structure["pairs"]}
        closing_suffix_lines = {line_no for line_no, _block_type in structure["close_suffix_lines"]}
        self._editor_block_pairs_cache = list(structure["pairs"])

        last_line = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        # Both `full_text` and `last_line` come from the same "end-1c" Tk index
        # taken here, so `text_lines` always has exactly `last_line` entries --
        # no per-line widget round-trip needed (verified: `full_text.split("\n")`
        # matches `widget.get(f"{n}.0", f"{n}.end")` line-for-line, including for
        # an empty buffer and a trailing newline).
        text_lines = full_text.split("\n")
        struktogramm_lines = _struktogramm_content_lines(text_lines, structure["pairs"])
        in_frontmatter = False
        frontmatter_delim_seen = 0

        for line_no in range(1, max(1, last_line) + 1):
            line_start = f"{line_no}.0"
            line_end = f"{line_no}.end"
            line_text = text_lines[line_no - 1]
            stripped = line_text.strip()

            if stripped == "---":
                self.editor_widget.tag_add("syn_frontmatter_delim", line_start, line_end)
                frontmatter_delim_seen += 1
                in_frontmatter = frontmatter_delim_seen == 1
                if frontmatter_delim_seen >= 2:
                    in_frontmatter = False
                continue

            if in_frontmatter:
                key_match = re.match(r"^(\s*)([^:\s][^:]*)(\s*:)", line_text)
                if key_match:
                    key_start = len(key_match.group(1))
                    key_end = key_start + len(key_match.group(2))
                    self.editor_widget.tag_add(
                        "syn_frontmatter_key",
                        f"{line_no}.{key_start}",
                        f"{line_no}.{key_end}",
                    )
                continue

            if line_no in closing_lines:
                marker_col = line_text.find(":::")
                if marker_col >= 0:
                    self.editor_widget.tag_add(
                        "syn_block_fence",
                        f"{line_no}.{marker_col}",
                        f"{line_no}.{marker_col + 3}",
                    )

                if line_no in closing_suffix_lines and marker_col >= 0:
                    content_end = len(line_text)
                    error_start = marker_col + 3
                    while error_start < content_end and line_text[error_start].isspace():
                        error_start += 1
                    if error_start < content_end:
                        self.editor_widget.tag_add(
                            "syn_block_close_error",
                            f"{line_no}.{error_start}",
                            f"{line_no}.{content_end}",
                        )
                continue

            # Kontrollmarker (`--hm`, `--!`, `--# …` …): abgeleitet aus `CONTROL_MARKERS`.
            control_match = control_marker_line_match(line_text)
            if control_match:
                self.editor_widget.tag_add("syn_control", f"{line_no}.{control_match.start(2)}", f"{line_no}.{control_match.end(2)}")
                continue

            header_match = re.match(r"^(\s*)(:::(\w+))(.*)$", line_text)
            if header_match:
                indent = len(header_match.group(1))
                token = header_match.group(2)
                token_start = indent
                token_end = token_start + len(token)
                self.editor_widget.tag_add(
                    "syn_block_fence",
                    f"{line_no}.{token_start}",
                    f"{line_no}.{min(token_start + 3, token_end)}",
                )
                self.editor_widget.tag_add(
                    "syn_block_type",
                    f"{line_no}.{min(token_start + 3, token_end)}",
                    f"{line_no}.{token_end}",
                )

                options_part = header_match.group(4) or ""
                options_offset = token_end
                for option_match in re.finditer(
                    r"([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|[^\s]+)",
                    options_part,
                ):
                    key_start = options_offset + option_match.start(1)
                    key_end = options_offset + option_match.end(1)
                    value_start = options_offset + option_match.start(2)
                    value_end = options_offset + option_match.end(2)
                    self.editor_widget.tag_add(
                        "syn_option_key",
                        f"{line_no}.{key_start}",
                        f"{line_no}.{key_end}",
                    )
                    self.editor_widget.tag_add(
                        "syn_option_value",
                        f"{line_no}.{value_start}",
                        f"{line_no}.{value_end}",
                    )

            marker_pattern = INDENTED_LINE_MARKER_RE if line_no in struktogramm_lines else _LINE_MARKER_PATTERN
            for marker_match in marker_pattern.finditer(line_text):
                marker_start = marker_match.start(1)
                marker_end = marker_match.end(1)
                self.editor_widget.tag_add(
                    "syn_marker",
                    f"{line_no}.{marker_start}",
                    f"{line_no}.{marker_end}",
                )

            # Inline-Stile `-<SPEC>`/`-<>`: dieselbe Regex wie der Parser (`style_spans.py`).
            for style_match in _INLINE_STYLE_MARKER_PATTERN.finditer(line_text):
                self.editor_widget.tag_add(
                    "syn_inline_style",
                    f"{line_no}.{style_match.start()}",
                    f"{line_no}.{style_match.end()}",
                )

        self._refresh_editor_block_pair_highlight()

    def _queue_editor_block_pair_highlight(self, immediate: bool = False):
        """Schedules a block-pair highlight refresh (debounced on KeyRelease)."""

        if self.editor_widget is None:
            return

        if self._editor_block_pair_after_id is not None:
            self.root.after_cancel(self._editor_block_pair_after_id)
            self._editor_block_pair_after_id = None

        if immediate:
            self._refresh_editor_block_pair_highlight()
            return

        self._editor_block_pair_after_id = self.root.after(
            self._editor_block_pair_delay_ms,
            self._refresh_editor_block_pair_highlight,
        )

    def _refresh_editor_block_pair_highlight(self):
        """Highlights opening/closing marker pair for block at current cursor line."""

        self._editor_block_pair_after_id = None
        if self.editor_widget is None:
            return

        self.editor_widget.tag_remove("syn_block_pair", "1.0", "end")

        pairs = getattr(self, "_editor_block_pairs_cache", [])
        if not pairs:
            return

        insert_index = self.editor_widget.index("insert")
        current_line = int(insert_index.split(".")[0])
        containing_pairs = [
            (open_line, close_line)
            for open_line, close_line in pairs
            if open_line <= current_line <= close_line
        ]
        if not containing_pairs:
            return

        open_line, close_line = min(
            containing_pairs,
            key=lambda pair: (pair[1] - pair[0], pair[0]),
        )

        self._tag_block_pair_marker(open_line, include_type=True)
        self._tag_block_pair_marker(close_line, include_type=False)

    def _tag_block_pair_marker(self, line_no: int, include_type: bool):
        """Applies block-pair highlight tag to marker token at given line."""

        if self.editor_widget is None:
            return

        line_text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
        marker_col = line_text.find(":::")
        if marker_col < 0:
            return

        if include_type:
            match = re.match(r"^(\s*)(:::(\w+))", line_text)
            if match:
                start_col = len(match.group(1))
                end_col = start_col + len(match.group(2))
            else:
                start_col = marker_col
                end_col = marker_col + 3
        else:
            start_col = marker_col
            end_col = marker_col + 3

        self.editor_widget.tag_add(
            "syn_block_pair",
            f"{line_no}.{start_col}",
            f"{line_no}.{end_col}",
        )
