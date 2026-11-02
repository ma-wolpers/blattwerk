"""Schreibbereich: Tags, Syntax- und Blockpaar-Hervorhebung, Theme-Farben (BlattwerkApp-Mixin).

Aus ``blatt_ui_editor.py`` ausgelagert (300-Zeilen-Regel), Methoden unverändert."""

from __future__ import annotations

import re

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.runtime import ui

from ..core.control_markers import control_marker_line_match
from ..core.inline_markup.style_spans import STYLE_MARKER_REGEX
from ..core.block_line_scan import LineKind, scan_block_lines
from ..core.diagram_block_catalog import DIAGRAM_BLOCK_NAMES
from ..core.frontmatter import frontmatter_editing_lines
from ..core.diagram_text import INDENTED_LINE_MARKER_RE
from .ui_theme import get_theme, is_dark_theme

_INLINE_STYLE_MARKER_PATTERN = re.compile(STYLE_MARKER_REGEX)
_LINE_MARKER_PATTERN = re.compile(r"^([§%&])(?=\s|$)")


def _diagram_content_lines(scan):
    """Zeilennummern (1-basiert) im Inhalt geschlossener Diagrammblöcke.

    Dort stehen Zeilenmarker nach der Einrückung (`INDENTED_LINE_MARKER_RE`),
    überall sonst nur am absoluten Zeilenanfang. `scan` ist die Blockstruktur
    aus `scan_block_lines`.
    """
    lines = set()
    for span in scan.spans:
        if span.close_line is not None and span.block_type in DIAGRAM_BLOCK_NAMES:
            lines.update(range(span.open_line + 1, span.close_line))
    return lines


def _header_token_end(line_text: str, block_type: str) -> tuple[int, int]:
    """`(Anfang, Ende)` des Tokens `:::name` in einer Kopfzeile (Einrückung berücksichtigt)."""
    start = len(line_text) - len(line_text.lstrip())
    return start, start + 3 + len(block_type)


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
        scan = scan_block_lines(full_text)
        self._editor_block_scan = scan

        last_line = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        # Both `full_text` and `last_line` come from the same "end-1c" Tk index
        # taken here, so `text_lines` always has exactly `last_line` entries --
        # no per-line widget round-trip needed (verified: `full_text.split("\n")`
        # matches `widget.get(f"{n}.0", f"{n}.end")` line-for-line, including for
        # an empty buffer and a trailing newline).
        text_lines = full_text.split("\n")
        diagram_lines = _diagram_content_lines(scan)
        frontmatter_lines = frontmatter_editing_lines(full_text)
        # Öffnungs- und (falls schon geschrieben) Schlusszeile; nie eine `---`-Trennlinie im Rumpf.
        frontmatter_delims = {frontmatter_lines.start, frontmatter_lines.stop} if frontmatter_lines else set()

        for line_no in range(1, max(1, last_line) + 1):
            line_start = f"{line_no}.0"
            line_end = f"{line_no}.end"
            line_text = text_lines[line_no - 1]
            scanned = scan.line(line_no)

            if line_no in frontmatter_delims:
                self.editor_widget.tag_add("syn_frontmatter_delim", line_start, line_end)
                continue

            if line_no in frontmatter_lines:
                # GRENZE: Nur die Position des Schlüssels zum Färben; YAML selbst liest `frontmatter.py`.
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

            if scanned.kind in (LineKind.CLOSE, LineKind.MALFORMED):
                marker_col = line_text.find(":::")
                self.editor_widget.tag_add(
                    "syn_block_fence",
                    f"{line_no}.{marker_col}",
                    f"{line_no}.{marker_col + 3}",
                )

                if scanned.kind is LineKind.MALFORMED:
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

            if scanned.is_header:
                token_start, token_end = _header_token_end(line_text, scanned.header_type)
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

                options_part = line_text[token_end:]
                options_offset = token_end
                # GRENZE: Färbt nur Zeichenpositionen. `parse_options` (shlex) liefert keine
                # Positionen, daher ein eigenes Muster; die Bedeutung der Optionen bleibt beim Parser.
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

            marker_pattern = INDENTED_LINE_MARKER_RE if line_no in diagram_lines else _LINE_MARKER_PATTERN
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

        scan = getattr(self, "_editor_block_scan", None)
        if scan is None:
            return

        current_line = int(self.editor_widget.index("insert").split(".")[0])
        span = scan.span_at(current_line)
        if span is None or span.close_line is None:
            return

        self._tag_block_pair_marker(span.open_line, span.block_type)
        self._tag_block_pair_marker(span.close_line, None)

    def _tag_block_pair_marker(self, line_no: int, block_type: str | None):
        """Markiert das Token `:::name` (Kopfzeile, `block_type` gesetzt) bzw. `:::` (Schlusszeile)."""

        if self.editor_widget is None:
            return

        line_text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
        if block_type is not None:
            start_col, end_col = _header_token_end(line_text, block_type)
        else:
            start_col = line_text.find(":::")
            end_col = start_col + 3

        self.editor_widget.tag_add(
            "syn_block_pair",
            f"{line_no}.{start_col}",
            f"{line_no}.{end_col}",
        )
