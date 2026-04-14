"""Editor mixin for loading and live-saving markdown text in the main window."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re
import shutil
import tkinter as tk
from tkinter import messagebox, ttk

from ..core.blatt_kern_shared import build_block_index_line_map
from ..core.completion_catalogs import (
    get_completion_block_types,
    get_completion_options_for_block,
    get_completion_option_values,
)
from ..core.blatt_validator import (
    inspect_markdown_text,
)
from ..storage.local_config_store import (
    get_block_type_decay_scores,
    get_option_value_decay_scores,
    record_block_type_usage,
    record_block_type_usage_batch,
    record_option_value_usage,
)
from .ui_constants import (
    EDITOR_VIEW_BOTH,
    EDITOR_VIEW_EDITOR_ONLY,
    EDITOR_VIEW_PREVIEW_ONLY,
)
from .ui_theme import get_theme, is_dark_theme


_EDITOR_FRONTMATTER_KEYS = (
    "Titel",
    "Fach",
    "Thema",
    "show_student_header",
    "show_document_header",
    "mode",
    "lochen",
    "copyright",
)

_SYNTAX_TAGS = (
    "syn_frontmatter_delim",
    "syn_frontmatter_key",
    "syn_block_fence",
    "syn_block_type",
    "syn_option_key",
    "syn_option_value",
    "syn_marker",
    "syn_block_close_error",
    "syn_block_pair",
)


class BlattwerkAppEditorMixin:
    """Adds a basic markdown editor area with debounced live save."""

    def _build_editor_panel(self, parent):
        """Creates the editor widget and wires change events for live save."""

        editor_toolbar = ttk.Frame(parent)
        editor_toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(editor_toolbar, text="Schreibbereich").pack(side="left")

        editor_body = ttk.Frame(parent)
        editor_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.editor_widget = tk.Text(
            editor_body,
            wrap="word",
            undo=True,
            borderwidth=0,
            highlightthickness=0,
        )
        self.editor_widget.pack(side="left", fill="both", expand=True)

        self.editor_vertical_scrollbar = ttk.Scrollbar(
            editor_body,
            orient="vertical",
            command=self.editor_widget.yview,
        )
        self.editor_vertical_scrollbar.pack(side="right", fill="y")
        self.editor_widget.configure(yscrollcommand=self.editor_vertical_scrollbar.set)
        self.editor_widget.bind("<<Modified>>", self._on_editor_modified)
        self.editor_widget.bind("<KeyRelease>", self._on_editor_key_release)
        self.editor_widget.bind("<Button-1>", self._on_editor_mouse_click)
        self.editor_widget.bind("<FocusIn>", self._on_editor_focus_in)

        preferences = getattr(self, "user_preferences", {})
        if bool(preferences.get("shortcuts_editor_group_enabled", True)):
            self.editor_widget.bind("<Control-space>", self._on_editor_completion_trigger)
            self.editor_widget.bind("<Control-Shift-period>", self._on_editor_insert_triple_pair)
            self.editor_widget.bind("<Control-colon>", self._on_editor_insert_triple_pair)
            self.editor_widget.bind("<Escape>", self._on_editor_escape)
            self.editor_widget.bind("<Tab>", self._on_editor_tab)
            self.editor_widget.bind("<Shift-Tab>", self._on_editor_shift_tab)
            self.editor_widget.bind("<ISO_Left_Tab>", self._on_editor_shift_tab)
            self.editor_widget.bind("<Up>", self._on_editor_completion_move_up)
            self.editor_widget.bind("<Down>", self._on_editor_completion_move_down)
            self.editor_widget.bind("<Return>", self._on_editor_completion_enter)

        diagnostics_frame = ttk.LabelFrame(parent, text="Diagnostik")
        diagnostics_frame.pack(fill="x", padx=8, pady=(0, 8))
        diagnostics_frame.columnconfigure(2, weight=1)

        ttk.Label(diagnostics_frame, text="Zeile").grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(6, 4))
        ttk.Label(diagnostics_frame, text="Code").grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(6, 4))
        ttk.Label(diagnostics_frame, text="Hinweis").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=(6, 4))

        self.editor_diagnostics_listbox = tk.Listbox(
            diagnostics_frame,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            height=6,
        )
        self.editor_diagnostics_listbox.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self.editor_diagnostics_listbox.bind("<<ListboxSelect>>", self._on_editor_diagnostic_selected)
        self.editor_diagnostics_listbox.bind("<ButtonRelease-1>", self._on_editor_diagnostic_click)

        diagnostics_scrollbar = ttk.Scrollbar(
            diagnostics_frame,
            orient="vertical",
            command=self.editor_diagnostics_listbox.yview,
        )
        diagnostics_scrollbar.grid(row=1, column=3, sticky="ns", padx=(0, 8), pady=(0, 8))
        self.editor_diagnostics_listbox.configure(yscrollcommand=diagnostics_scrollbar.set)
        diagnostics_frame.rowconfigure(1, weight=1)

        outline_frame = ttk.LabelFrame(parent, text="Struktur")
        outline_frame.pack(fill="x", padx=8, pady=(0, 8))
        outline_frame.columnconfigure(0, weight=1)
        if not bool(preferences.get("outline_visible_on_start", True)):
            outline_frame.pack_forget()

        self.editor_outline_listbox = tk.Listbox(
            outline_frame,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            height=6,
        )
        self.editor_outline_listbox.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(6, 8))
        self.editor_outline_listbox.bind("<<ListboxSelect>>", self._on_editor_outline_selected)
        self.editor_outline_listbox.bind("<ButtonRelease-1>", self._on_editor_outline_click)

        outline_scrollbar = ttk.Scrollbar(
            outline_frame,
            orient="vertical",
            command=self.editor_outline_listbox.yview,
        )
        outline_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(6, 8))
        self.editor_outline_listbox.configure(yscrollcommand=outline_scrollbar.set)

        self._configure_editor_diagnostic_tags()
        self._configure_editor_syntax_tags()

    def _load_editor_content(self, input_path: Path):
        """Loads the selected markdown file into the editor widget."""

        if self.editor_widget is None:
            return

        try:
            content = input_path.read_text(encoding="utf-8")
        except Exception as error:
            messagebox.showerror("Datei konnte nicht gelesen werden", str(error))
            self.status_var.set("Datei konnte nicht gelesen werden")
            return

        self._editor_loading_content = True
        try:
            self.editor_widget.delete("1.0", "end")
            self.editor_widget.insert("1.0", content)
            self.editor_widget.edit_modified(False)
            self._editor_has_unsaved_changes = False
            self._editor_last_loaded_path = input_path
            self._update_editor_source_snapshot(input_path)
            self._editor_last_saved_block_type_counts = self._collect_editor_block_type_counts(content)
            self._queue_editor_highlighting(immediate=True)
            self._queue_editor_diagnostics(immediate=True)
            self._queue_editor_outline(immediate=True)
        finally:
            self._editor_loading_content = False

    @staticmethod
    def _format_external_change_age(file_mtime_ns: int) -> str:
        """Formats the age of the external file change for conflict prompts."""

        changed_at = datetime.fromtimestamp(file_mtime_ns / 1_000_000_000)
        now = datetime.now()
        delta_seconds = max(0, int((now - changed_at).total_seconds()))
        if delta_seconds < 60:
            relative = f"vor {delta_seconds} s"
        elif delta_seconds < 3600:
            relative = f"vor {delta_seconds // 60} min"
        elif delta_seconds < 86400:
            relative = f"vor {delta_seconds // 3600} h"
        else:
            relative = f"vor {delta_seconds // 86400} Tagen"

        return f"{relative} ({changed_at.strftime('%Y-%m-%d %H:%M:%S')})"

    def _update_editor_source_snapshot(self, input_path: Path):
        """Stores the latest known source timestamp for the active editor file."""

        try:
            file_stat = input_path.stat()
        except Exception:
            return

        self._editor_last_known_source_path = input_path
        self._editor_last_known_source_mtime_ns = int(file_stat.st_mtime_ns)

    def _show_editor_source_conflict_dialog(self, *, input_path: Path, age_text: str) -> str:
        """Shows a modal conflict dialog and returns discard, overwrite, or cancel."""

        dialog = tk.Toplevel(self.root)
        dialog.title("Externe Änderung erkannt")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        try:
            dialog.grab_set()
        except Exception:
            pass

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill="both", expand=True)

        ttk.Label(
            body,
            text=(
                "Die Quelldatei wurde extern geändert.\n"
                f"Datei: {input_path.name}\n"
                f"Geändert: {age_text}\n\n"
                "Lokale ungespeicherte Änderungen sind vorhanden."
            ),
            justify="left",
        ).pack(anchor="w")

        button_row = ttk.Frame(body)
        button_row.pack(fill="x", pady=(12, 0))

        result = {"value": "cancel"}

        def choose(value: str):
            result["value"] = value
            dialog.destroy()

        ttk.Button(button_row, text="Verwerfen", command=lambda: choose("discard")).pack(side="left")
        ttk.Button(button_row, text="Überschreiben", command=lambda: choose("overwrite")).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Abbrechen", command=lambda: choose("cancel")).pack(side="right")

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        dialog.wait_window()
        return result["value"]

    def _sync_editor_with_source(self, trigger: str = "focus"):
        """Reconciles editor state with external file changes before editing continues."""

        del trigger  # currently only used for tracing when needed

        if self.editor_widget is None:
            return
        if self._editor_loading_content:
            return
        if self._editor_source_sync_in_progress:
            return

        input_path = self._get_input_path_if_exists()
        if input_path is None:
            return

        try:
            current_mtime_ns = int(input_path.stat().st_mtime_ns)
        except Exception:
            return

        known_path = self._editor_last_known_source_path
        known_mtime_ns = self._editor_last_known_source_mtime_ns

        if known_path != input_path or known_mtime_ns is None:
            self._editor_last_known_source_path = input_path
            self._editor_last_known_source_mtime_ns = current_mtime_ns
            return

        if current_mtime_ns <= known_mtime_ns:
            return

        self._editor_source_sync_in_progress = True
        try:
            if self._editor_has_unsaved_changes:
                age_text = self._format_external_change_age(current_mtime_ns)
                decision = self._show_editor_source_conflict_dialog(input_path=input_path, age_text=age_text)
                if decision == "discard":
                    self._load_editor_content(input_path)
                    self.status_var.set("Externe Änderung übernommen (lokale Änderungen verworfen)")
                elif decision == "overwrite":
                    self._save_editor_content()
                    if self._editor_has_unsaved_changes:
                        self.status_var.set("Überschreiben fehlgeschlagen")
                    else:
                        self.status_var.set("Externe Änderung überschrieben (lokaler Stand gespeichert)")
                else:
                    self.status_var.set("Konflikt mit externer Änderung: keine Aktion")
            else:
                self._load_editor_content(input_path)
                self.status_var.set("Externe Änderung übernommen")
        finally:
            self._editor_source_sync_in_progress = False

    def _on_editor_focus_in(self, _event=None):
        """Synchronizes the editor with external file changes when focus enters."""

        self._sync_editor_with_source(trigger="focus")

    def _on_editor_modified(self, _event=None):
        """Schedules a debounced save after user edits."""

        if self.editor_widget is None:
            return

        if self._editor_loading_content:
            self.editor_widget.edit_modified(False)
            return

        if not self.editor_widget.edit_modified():
            return

        self.editor_widget.edit_modified(False)
        self._editor_has_unsaved_changes = True
        self.status_var.set("Ungespeichert")
        self._queue_editor_highlighting()
        self._queue_editor_diagnostics()
        self._queue_editor_outline()

        if self._editor_save_after_id is not None:
            self.root.after_cancel(self._editor_save_after_id)

        self._editor_save_after_id = self.root.after(self._editor_save_delay_ms, self._save_editor_content)

    def _save_editor_content(self):
        """Writes the current editor content back to the selected markdown file."""

        self._editor_save_after_id = None

        if self.editor_widget is None:
            return

        input_path = self._validate_input()
        if input_path is None:
            return

        content = self.editor_widget.get("1.0", "end-1c")
        try:
            self.status_var.set("Speichert…")
            preferences = getattr(self, "user_preferences", {})
            if bool(preferences.get("backup_on_save", False)) and input_path.exists():
                keep_versions = int(str(preferences.get("backup_versions_keep", 3) or 3))
                keep_versions = max(1, min(50, keep_versions))
                backup_dir = input_path.parent / "backup_pre_migration"
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{input_path.stem}_{timestamp}{input_path.suffix}"
                backup_path = backup_dir / backup_name
                shutil.copy2(input_path, backup_path)

                backup_files = sorted(
                    backup_dir.glob(f"{input_path.stem}_*{input_path.suffix}"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                for stale_file in backup_files[keep_versions:]:
                    try:
                        stale_file.unlink()
                    except Exception:
                        pass

            input_path.write_text(content, encoding="utf-8")
            self._record_editor_manual_block_type_usage(content)
            self._editor_has_unsaved_changes = False
            self._update_editor_source_snapshot(input_path)
            self.status_var.set("Gespeichert")
            self._queue_editor_highlighting(immediate=True)
            self._queue_editor_diagnostics(immediate=True)
            self._queue_editor_outline(immediate=True)
        except Exception as error:
            self.status_var.set("Speichern fehlgeschlagen")
            messagebox.showerror("Speichern fehlgeschlagen", str(error))

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
        """Configures text tags for syntax highlighting in markdown editor."""

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
            self.editor_widget.tag_configure("syn_block_close_error", background="#5A1F2A", foreground="#FF9DA4")
            self.editor_widget.tag_configure("syn_block_pair", background="#2C3744")
        else:
            self.editor_widget.tag_configure("syn_frontmatter_delim", foreground="#0b7285")
            self.editor_widget.tag_configure("syn_frontmatter_key", foreground="#1864ab")
            self.editor_widget.tag_configure("syn_block_fence", foreground="#b35c00")
            self.editor_widget.tag_configure("syn_block_type", foreground="#9c36b5")
            self.editor_widget.tag_configure("syn_option_key", foreground="#0b7285")
            self.editor_widget.tag_configure("syn_option_value", foreground="#8d6b00")
            self.editor_widget.tag_configure("syn_marker", foreground="#c92a2a")
            self.editor_widget.tag_configure("syn_block_close_error", background="#ffe2e2", foreground="#8b0000")
            self.editor_widget.tag_configure("syn_block_pair", background=theme["accent_soft"])

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

        if self.editor_diagnostics_listbox is not None:
            self.editor_diagnostics_listbox.configure(**listbox_kwargs)

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
            except tk.TclError:
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
        closing_suffix_lines = set(structure["close_suffix_lines"])
        self._editor_block_pairs_cache = list(structure["pairs"])

        last_line = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        in_frontmatter = False
        frontmatter_delim_seen = 0

        for line_no in range(1, max(1, last_line) + 1):
            line_start = f"{line_no}.0"
            line_end = f"{line_no}.end"
            line_text = self.editor_widget.get(line_start, line_end)
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

            for marker_match in re.finditer(r"(^|\s)([§$&])(?=\s|$)", line_text):
                marker_start = marker_match.start(2)
                marker_end = marker_match.end(2)
                self.editor_widget.tag_add(
                    "syn_marker",
                    f"{line_no}.{marker_start}",
                    f"{line_no}.{marker_end}",
                )

        self._refresh_editor_block_pair_highlight()

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
        try:
            inspected = inspect_markdown_text(text)
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

    def _on_editor_key_release(self, event=None):
        """Keeps completion popup in sync while typing on matching contexts."""

        if self.editor_widget is None:
            return

        if event is None:
            return

        if event.keysym in {"Escape"}:
            return

        if event.keysym in {
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Meta_L",
            "Meta_R",
            "ISO_Level3_Shift",
        }:
            return

        if event.keysym in {"period", "colon"} and self._is_editor_completion_visible():
            return

        if event.keysym in {"Up", "Down", "Left", "Right"}:
            self._refresh_editor_block_pair_highlight()
            return

        preferences = getattr(self, "user_preferences", {})
        if not bool(preferences.get("completion_auto_enabled", True)):
            self._refresh_editor_block_pair_highlight()
            return

        trigger_chars = {"_", " "}
        if bool(preferences.get("completion_trigger_colon", True)):
            trigger_chars.add(":")
        if bool(preferences.get("completion_trigger_equals", True)):
            trigger_chars.add("=")

        trigger_keys = {"BackSpace"}
        if bool(preferences.get("completion_trigger_enter", True)):
            trigger_keys.add("Return")

        should_trigger = (
            event.keysym in trigger_keys
            or bool(event.char and (event.char.isalnum() or event.char in trigger_chars))
        )

        if should_trigger:
            self._open_editor_completion(auto=True)
        else:
            self._close_editor_completion()

        self._refresh_editor_block_pair_highlight()

    def _on_editor_completion_trigger(self, _event=None):
        """Opens completion suggestions manually via Ctrl+Space."""

        self._open_editor_completion(auto=False)
        return "break"

    def _on_editor_insert_triple_pair(self, _event=None):
        """Inserts `::: :::` and opens completion at center cursor position."""

        if self.editor_widget is None:
            return "break"

        insert_index = self.editor_widget.index("insert")
        self.editor_widget.insert(insert_index, "::: :::")
        self.editor_widget.mark_set("insert", f"{insert_index}+3c")
        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        self._open_editor_completion(auto=False)
        return "break"

    def _on_editor_escape(self, _event=None):
        """Closes completion popup when escape is pressed in editor."""

        self._close_editor_completion()
        if self.root is not None and bool(self.root.winfo_exists()):
            self.root.focus_set()
        return "break"

    def _on_editor_tab(self, _event=None):
        """Applies selected completion on tab when popup is visible."""

        if self._editor_completion_items:
            return self._on_editor_completion_accept()
        return None

    def _on_editor_shift_tab(self, _event=None):
        """No-op for completion flow when no popup action applies."""

        return None

    def _on_editor_completion_move_up(self, _event=None):
        """Moves completion selection up when popup is visible."""

        if not self._is_editor_completion_visible() or self._editor_completion_listbox is None:
            return None

        selection = self._editor_completion_listbox.curselection()
        current = selection[0] if selection else 0
        new_index = max(0, current - 1)
        self._editor_completion_listbox.selection_clear(0, "end")
        self._editor_completion_listbox.selection_set(new_index)
        self._editor_completion_listbox.activate(new_index)
        self._editor_completion_listbox.see(new_index)
        return "break"

    def _on_editor_completion_move_down(self, _event=None):
        """Moves completion selection down when popup is visible."""

        if not self._is_editor_completion_visible() or self._editor_completion_listbox is None:
            return None

        selection = self._editor_completion_listbox.curselection()
        current = selection[0] if selection else 0
        max_index = max(0, len(self._editor_completion_items) - 1)
        new_index = min(max_index, current + 1)
        self._editor_completion_listbox.selection_clear(0, "end")
        self._editor_completion_listbox.selection_set(new_index)
        self._editor_completion_listbox.activate(new_index)
        self._editor_completion_listbox.see(new_index)
        return "break"

    def _on_editor_completion_enter(self, _event=None):
        """Accepts completion on enter when popup is visible."""

        if self._editor_completion_items:
            return self._on_editor_completion_accept()
        return None

    def _on_editor_mouse_click(self, _event=None):
        """Closes completion popup when user clicks in editor."""

        self._close_editor_completion()
        if hasattr(self, "root"):
            self.root.after_idle(self._refresh_editor_block_pair_highlight)

    def _open_editor_completion(self, auto: bool):
        """Collects completion suggestions and renders popup near caret."""

        if self.editor_widget is None:
            return

        context = self._collect_editor_completion_context(auto=auto)
        if context is None:
            self._close_editor_completion()
            return

        suggestions = context.get("suggestions") or []
        if not suggestions:
            self._close_editor_completion()
            return

        completion_kind = context.get("kind")
        raw_meta = context.get("meta")
        completion_meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
        if completion_kind == "block_type":
            suggestions = self._rank_block_type_suggestions(suggestions)
        if completion_kind == "option_value":
            suggestions = self._rank_option_value_suggestions(
                suggestions,
                block_type=str(completion_meta.get("block_type") or ""),
                option_key=str(completion_meta.get("option_key") or ""),
            )

        self._editor_completion_replace_start = context["replace_start"]
        self._editor_completion_replace_end = context["replace_end"]
        self._editor_completion_context_kind = completion_kind
        self._editor_completion_context_meta = completion_meta

        if self._editor_completion_popup is None or not self._editor_completion_popup.winfo_exists():
            popup = tk.Toplevel(self.root)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.transient(self.root)

            listbox = tk.Listbox(
                popup,
                activestyle="none",
                height=min(8, len(suggestions)),
                width=72,
            )
            listbox.pack(fill="both", expand=True)
            listbox.bind("<Double-Button-1>", self._on_editor_completion_accept)
            listbox.bind("<Return>", self._on_editor_completion_accept)
            listbox.bind("<Escape>", lambda _event: self._close_editor_completion())

            self._editor_completion_popup = popup
            self._editor_completion_listbox = listbox

        if self._editor_completion_listbox is None:
            return

        self._editor_completion_items = list(suggestions)
        width_chars = max((len(item["label"]) for item in self._editor_completion_items), default=40)
        preferences = getattr(self, "user_preferences", {})
        popup_width_mode = str(preferences.get("completion_popup_width_mode", "wide") or "wide")
        if popup_width_mode == "compact":
            min_width = 32
            max_width = 72
        elif popup_width_mode == "normal":
            min_width = 40
            max_width = 90
        else:
            min_width = 46
            max_width = 110
        self._editor_completion_listbox.configure(width=min(max_width, max(min_width, width_chars + 2)))
        self._editor_completion_listbox.configure(height=min(8, len(self._editor_completion_items)))
        self._editor_completion_listbox.delete(0, "end")
        for item in self._editor_completion_items:
            self._editor_completion_listbox.insert("end", item["label"])

        self._editor_completion_listbox.selection_clear(0, "end")
        self._editor_completion_listbox.selection_set(0)
        self._editor_completion_listbox.activate(0)

        caret_box = self.editor_widget.bbox("insert")
        if caret_box is None:
            self._close_editor_completion()
            return

        x = self.editor_widget.winfo_rootx() + caret_box[0]
        y = self.editor_widget.winfo_rooty() + caret_box[1] + caret_box[3] + 2
        self._editor_completion_popup.geometry(f"+{x}+{y}")
        self._editor_completion_popup.deiconify()
        self._editor_completion_popup.lift()

    def _collect_editor_completion_context(self, auto: bool):
        """Derives completion candidates from current line and cursor context."""

        if self.editor_widget is None:
            return None

        preferences = getattr(self, "user_preferences", {})
        completion_context_mode = str(preferences.get("completion_context_sources", "smart") or "smart")
        if auto and completion_context_mode == "manual_only":
            return None

        insert_index = self.editor_widget.index("insert")
        line_no_text, col_text = insert_index.split(".")
        line_no = int(line_no_text)
        cursor_col = int(col_text)
        line_text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
        left_text = line_text[:cursor_col]
        left_stripped = left_text.lstrip()
        line_indent = len(left_text) - len(left_stripped)
        stripped_line = line_text.strip()
        is_block_header_line = bool(re.match(r"^\s*:::", line_text))
        is_closing_only_line = stripped_line == ":::"
        is_opening_header_line = is_block_header_line and not is_closing_only_line

        if left_stripped.startswith(":::"):
            after_fence = left_stripped[3:]
            if " " not in after_fence:
                block_prefix = after_fence
                # Avoid auto popup on likely closing marker lines inside an open block.
                if auto and block_prefix == "" and stripped_line == ":::" and self._editor_get_enclosing_block_type(line_no):
                    return None

                suggestions = [
                    {
                        "label": block_type,
                        "insert_text": block_type,
                        "kind": "block_type",
                        "block_type": block_type,
                    }
                    for block_type in get_completion_block_types()
                    if block_type.startswith(block_prefix)
                ]
                if auto and not suggestions:
                    return None

                replace_start = f"{line_no}.{line_indent + 3}"
                replace_end = f"{line_no}.{line_indent + 3 + len(block_prefix)}"
                return {
                    "suggestions": suggestions,
                    "replace_start": replace_start,
                    "replace_end": replace_end,
                    "kind": "block_type",
                }

            block_token = after_fence.split(" ", 1)[0]
            block_allowed_options = get_completion_options_for_block(block_token)
            if block_allowed_options:
                option_value_match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]*)$", left_text)
                if option_value_match:
                    option_key = option_value_match.group(1)
                    value_prefix = option_value_match.group(2) or ""
                    suggestions = self._build_option_value_suggestions(
                        block_type=block_token,
                        option_key=option_key,
                        value_prefix=value_prefix,
                    )
                    if suggestions:
                        value_start = option_value_match.start(2)
                        value_end = option_value_match.end(2)
                        return {
                            "suggestions": suggestions,
                            "replace_start": f"{line_no}.{value_start}",
                            "replace_end": f"{line_no}.{value_end}",
                            "kind": "option_value",
                            "meta": {
                                "block_type": block_token,
                                "option_key": option_key.lower(),
                            },
                        }

                if after_fence == f"{block_token} ":
                    suggestions = [
                        {
                            "label": option,
                            "insert_text": option,
                            "kind": "block_option",
                        }
                        for option in block_allowed_options
                    ]
                    if auto and not suggestions:
                        return None

                    return {
                        "suggestions": suggestions,
                        "replace_start": f"{line_no}.{cursor_col}",
                        "replace_end": f"{line_no}.{cursor_col}",
                        "kind": "block_option",
                    }

                if left_text.endswith(" "):
                    used_option_keys = {
                        match.group(1).strip().lower()
                        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)=", left_text)
                    }
                    suggestions = [
                        {
                            "label": option,
                            "insert_text": option,
                            "kind": "block_option",
                        }
                        for option in block_allowed_options
                        if option.lower() not in used_option_keys
                    ]
                    if not suggestions:
                        suggestions = [
                            {
                                "label": option,
                                "insert_text": option,
                                "kind": "block_option",
                            }
                            for option in block_allowed_options
                        ]

                    if auto and not suggestions:
                        return None

                    return {
                        "suggestions": suggestions,
                        "replace_start": f"{line_no}.{cursor_col}",
                        "replace_end": f"{line_no}.{cursor_col}",
                        "kind": "block_option",
                    }

                key_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)$", left_text)
                if key_match and "=" not in left_text[key_match.start(1):]:
                    key_prefix = key_match.group(1)
                    if auto and len(key_prefix) < 1:
                        return None

                    suggestions = [
                        {
                            "label": option,
                            "insert_text": option,
                            "kind": "block_option",
                        }
                        for option in block_allowed_options
                        if option.startswith(key_prefix)
                    ]
                    return {
                        "suggestions": suggestions,
                        "replace_start": f"{line_no}.{key_match.start(1)}",
                        "replace_end": f"{line_no}.{key_match.end(1)}",
                        "kind": "block_option",
                    }

        if self._editor_cursor_in_frontmatter(line_no):
            frontmatter_match = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_\-]*)?$", left_text)
            if frontmatter_match:
                key_prefix = frontmatter_match.group(2) or ""
                if auto and len(key_prefix) < 1:
                    return None

                suggestions = [
                    {
                        "label": field_name,
                        "insert_text": field_name,
                        "kind": "frontmatter_key",
                    }
                    for field_name in _EDITOR_FRONTMATTER_KEYS
                    if field_name.lower().startswith(key_prefix.lower())
                ]
                key_start = len(frontmatter_match.group(1))
                return {
                    "suggestions": suggestions,
                    "replace_start": f"{line_no}.{key_start}",
                    "replace_end": f"{line_no}.{key_start + len(key_prefix)}",
                    "kind": "frontmatter_key",
                }

        return None

    def _editor_get_enclosing_block_type(self, target_line_no: int) -> str | None:
        """Returns the currently open block type for a given line number, if any."""

        if self.editor_widget is None:
            return None

        line_count = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        upper_bound = max(1, min(target_line_no, line_count))

        block_stack = []
        self_closing_pattern = re.compile(r"^\s*:::(\w+)(.*?):::\s*$")
        block_open_pattern = re.compile(r"^\s*:::(\w+)(.*)$")

        for line_no in range(1, upper_bound + 1):
            text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
            stripped = text.strip()

            if not stripped:
                continue

            if self_closing_pattern.match(stripped):
                continue

            if stripped == ":::":
                if block_stack:
                    block_stack.pop()
                continue

            block_open_match = block_open_pattern.match(stripped)
            if block_open_match:
                block_stack.append(block_open_match.group(1).lower())

        if not block_stack:
            return None
        return block_stack[-1]

    def _editor_cursor_in_frontmatter(self, line_no: int) -> bool:
        """Returns true when the given line index is inside frontmatter section."""

        if self.editor_widget is None:
            return False

        frontmatter_delim_count = 0
        for current_line in range(1, max(1, line_no) + 1):
            text = self.editor_widget.get(f"{current_line}.0", f"{current_line}.end").strip()
            if text == "---":
                frontmatter_delim_count += 1

        return frontmatter_delim_count == 1

    def _on_editor_completion_accept(self, _event=None):
        """Applies currently selected completion entry to the editor text."""

        if self.editor_widget is None or self._editor_completion_listbox is None:
            return "break"

        selection = self._editor_completion_listbox.curselection()
        if not selection:
            return "break"

        candidate = self._editor_completion_items[selection[0]]
        if not candidate:
            return "break"

        self._record_editor_completion_usage(candidate)

        insert_text, cursor_offset = self._resolve_completion_insert(candidate)
        if insert_text is None or cursor_offset is None:
            return "break"

        replace_start = self._editor_completion_replace_start or self.editor_widget.index("insert")
        replace_end = self._editor_completion_replace_end or self.editor_widget.index("insert")
        self.editor_widget.delete(replace_start, replace_end)
        self.editor_widget.insert(replace_start, insert_text)
        self.editor_widget.mark_set("insert", f"{replace_start}+{cursor_offset}c")
        self.editor_widget.focus_set()
        self._queue_editor_highlighting(immediate=True)
        self._queue_editor_diagnostics(immediate=True)
        self._queue_editor_outline(immediate=True)
        self._close_editor_completion()
        return "break"

    def _record_editor_completion_usage(self, candidate) -> None:
        """Records block-type usage for completion ranking when candidate implies one."""

        if not isinstance(candidate, dict):
            return

        block_type = candidate.get("block_type")
        kind = str(candidate.get("kind") or "").strip().lower()
        if not block_type and kind == "block_type":
            block_type = candidate.get("insert_text")
        if not block_type:
            insert_text = str(candidate.get("insert_text") or "")
            first_line = insert_text.splitlines()[0] if insert_text else ""
            match = re.match(r"^\s*:::(\w+)", first_line)
            if match:
                block_type = match.group(1)

        normalized = str(block_type or "").strip().lower()
        kind = str(candidate.get("kind") or "").strip().lower()
        if kind == "option_value":
            option_key = str(candidate.get("option_key") or self._editor_completion_context_meta.get("option_key") or "").strip().lower()
            value = str(candidate.get("insert_text") or "").strip().lower()
            block_type_for_value = str(candidate.get("block_type") or self._editor_completion_context_meta.get("block_type") or "").strip().lower()
            if block_type_for_value and option_key and value:
                try:
                    record_option_value_usage(block_type_for_value, option_key, value)
                except Exception:
                    pass

        if normalized:
            try:
                record_block_type_usage(normalized)
            except Exception:
                pass

    def _rank_block_type_suggestions(self, suggestions):
        """Ranks block-type suggestions by local decay score, then core order."""

        try:
            scores = get_block_type_decay_scores()
        except Exception:
            scores = {}

        order_index = {block_type: index for index, block_type in enumerate(get_completion_block_types())}

        def _sort_key(item):
            block_type = str(item.get("block_type") or item.get("insert_text") or "").strip().lower()
            score = float(scores.get(block_type, 0.0))
            return (
                -score,
                order_index.get(block_type, 10_000),
                str(item.get("label") or "").lower(),
            )

        return sorted(list(suggestions), key=_sort_key)

    def _rank_option_value_suggestions(self, suggestions, *, block_type: str, option_key: str):
        """Ranks option value suggestions with same local decay mechanism as block types."""

        block_type_norm = str(block_type or "").strip().lower()
        option_key_norm = str(option_key or "").strip().lower()
        try:
            scores = get_option_value_decay_scores(block_type_norm, option_key_norm)
        except Exception:
            scores = {}

        def _sort_key(item):
            value = str(item.get("insert_text") or "").strip().lower()
            score = float(scores.get(value, 0.0))
            return (-score, str(item.get("label") or "").lower())

        return sorted(list(suggestions), key=_sort_key)

    def _build_option_value_suggestions(self, *, block_type: str, option_key: str, value_prefix: str):
        """Builds option value candidates with optional learned ranking data."""

        block_type_norm = str(block_type or "").strip().lower()
        option_key_norm = str(option_key or "").strip().lower()
        prefix_norm = str(value_prefix or "").strip().lower()

        defaults = list(get_completion_option_values(block_type_norm, option_key_norm))

        learned = []
        try:
            learned_scores = get_option_value_decay_scores(block_type_norm, option_key_norm)
            learned = sorted(learned_scores.keys())
        except Exception:
            learned = []

        seen = set()
        merged: list[str] = []
        for value in defaults + learned:
            key = str(value).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(str(value).strip())

        filtered = [value for value in merged if value.lower().startswith(prefix_norm)]
        return [
            {
                "label": value,
                "insert_text": value,
                "kind": "option_value",
                "block_type": block_type_norm,
                "option_key": option_key_norm,
            }
            for value in filtered
        ]

    @staticmethod
    def _collect_editor_block_type_counts(markdown_text: str) -> dict[str, int]:
        """Collects per-block-type counts from opening or self-closing block headers."""

        counts: dict[str, int] = {}
        self_closing_pattern = re.compile(r"^\s*:::(\w+)(.*?):::\s*$")
        opening_pattern = re.compile(r"^\s*:::(\w+)(.*)$")

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped == ":::":
                continue

            self_closing_match = self_closing_pattern.match(stripped)
            if self_closing_match:
                block_type = self_closing_match.group(1).lower()
                counts[block_type] = counts.get(block_type, 0) + 1
                continue

            opening_match = opening_pattern.match(stripped)
            if opening_match:
                block_type = opening_match.group(1).lower()
                counts[block_type] = counts.get(block_type, 0) + 1

        return counts

    def _record_editor_manual_block_type_usage(self, markdown_text: str) -> None:
        """Records block-type usage deltas from manually edited document content on save."""

        current_counts = self._collect_editor_block_type_counts(markdown_text)
        previous_counts = dict(getattr(self, "_editor_last_saved_block_type_counts", {}) or {})
        increments: dict[str, int] = {}

        for block_type, current_count in current_counts.items():
            previous_count = int(previous_counts.get(block_type, 0))
            delta = int(current_count) - previous_count
            if delta > 0:
                increments[block_type] = delta

        if increments:
            try:
                record_block_type_usage_batch(increments)
            except Exception:
                pass

        self._editor_last_saved_block_type_counts = current_counts

    @staticmethod
    def _resolve_completion_insert(candidate):
        """Returns insert text plus target cursor offset after insertion."""

        if not isinstance(candidate, dict):
            return None, None

        raw_insert_text = candidate.get("insert_text")
        if raw_insert_text is None:
            return None, None

        placeholder_pattern = re.compile(r"\[\[(\d+):([^\]]*)\]\]")
        occurrences = []
        output_parts = []
        scan_index = 0

        for match in placeholder_pattern.finditer(raw_insert_text):
            output_parts.append(raw_insert_text[scan_index:match.start()])
            replacement_text = match.group(2)
            output_offset = len("".join(output_parts))
            output_parts.append(replacement_text)
            occurrences.append(
                {
                    "order": int(match.group(1)),
                    "start": output_offset,
                    "end": output_offset + len(replacement_text),
                }
            )
            scan_index = match.end()

        output_parts.append(raw_insert_text[scan_index:])
        parsed_insert_text = "".join(output_parts)

        if occurrences:
            ordered = sorted(occurrences, key=lambda item: (item["order"], item["start"]))
            return parsed_insert_text, ordered[0]["start"]

        cursor_marker = "[[CURSOR]]"
        marker_index = parsed_insert_text.find(cursor_marker)
        if marker_index >= 0:
            insert_text = parsed_insert_text.replace(cursor_marker, "", 1)
            return insert_text, marker_index

        return parsed_insert_text, len(parsed_insert_text)

    def _editor_document_has_frontmatter(self) -> bool:
        """Detects whether the current editor buffer already contains frontmatter."""

        if self.editor_widget is None:
            return False

        line_count = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        delimiter_lines = []
        for line_no in range(1, max(1, line_count) + 1):
            text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end").strip()
            if text == "---":
                delimiter_lines.append(line_no)
                if len(delimiter_lines) >= 2:
                    return True

            if text and not delimiter_lines:
                return False

        return False

    def _close_editor_completion(self):
        """Hides and clears completion popup state."""

        if self._editor_completion_popup is not None and self._editor_completion_popup.winfo_exists():
            self._editor_completion_popup.withdraw()

        self._editor_completion_items = []
        self._editor_completion_replace_start = None
        self._editor_completion_replace_end = None
        self._editor_completion_context_kind = None
        self._editor_completion_context_meta = {}

    def _is_editor_completion_visible(self) -> bool:
        """Returns true if completion popup exists and is currently visible."""

        if self._editor_completion_popup is None:
            return False
        if not self._editor_completion_popup.winfo_exists():
            return False
        return self._editor_completion_popup.state() != "withdrawn"

    def _queue_editor_outline(self, immediate: bool = False):
        """Schedules an outline refresh to keep section navigation current."""

        if self.editor_widget is None:
            return

        if self._editor_outline_after_id is not None:
            self.root.after_cancel(self._editor_outline_after_id)
            self._editor_outline_after_id = None

        if immediate:
            self._refresh_editor_outline()
            return

        self._editor_outline_after_id = self.root.after(
            self._editor_outline_delay_ms,
            self._refresh_editor_outline,
        )

    def _refresh_editor_outline(self):
        """Builds editor outline from frontmatter and Blattwerk block headers."""

        self._editor_outline_after_id = None
        if self.editor_widget is None:
            return

        line_count = int(self.editor_widget.index("end-1c").split(".")[0] or 1)
        items = []
        frontmatter_count = 0
        block_stack = []
        self_closing_pattern = re.compile(r"^:::(\w+)(.*?):::$")
        opening_pattern = re.compile(r"^:::(\w+)(.*)$")

        for line_no in range(1, max(1, line_count) + 1):
            line_text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
            stripped = line_text.strip()

            if stripped == "---":
                frontmatter_count += 1
                if frontmatter_count == 1:
                    items.append(
                        {
                            "line": line_no,
                            "label": f"{line_no:>4}  Frontmatter",
                        }
                    )
                continue

            if not stripped:
                continue

            if self_closing_pattern.match(stripped):
                continue

            opening_match = opening_pattern.match(stripped)
            if opening_match:
                block_type = opening_match.group(1)
                rest = (opening_match.group(2) or "").strip()
                indent = "  " * len(block_stack)
                suffix = f" {rest}" if rest else ""
                items.append(
                    {
                        "line": line_no,
                        "label": f"{line_no:>4}  {indent}{block_type}{suffix}",
                    }
                )
                block_stack.append(block_type.lower())
                continue

            if stripped.startswith(":::") and block_stack:
                block_stack.pop()
                continue

        self._set_editor_outline(items)

    def _set_editor_outline(self, items):
        """Renders outline items in structure list for quick line navigation."""

        self._editor_outline_items = list(items)
        if self.editor_outline_listbox is None:
            return

        self.editor_outline_listbox.delete(0, "end")
        if not self._editor_outline_items:
            self.editor_outline_listbox.insert("end", "Keine Struktur erkannt")
            return

        for item in self._editor_outline_items:
            self.editor_outline_listbox.insert("end", item["label"])

    def _on_editor_outline_selected(self, _event=None):
        """Jumps to selected structure entry in editor."""

        if self.editor_widget is None or self.editor_outline_listbox is None:
            return

        selection = self.editor_outline_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self._editor_outline_items):
            return

        line = self._editor_outline_items[index]["line"]
        line_index = f"{max(1, int(line))}.0"
        self.editor_widget.mark_set("insert", line_index)
        self.editor_widget.see(line_index)
        self.editor_widget.focus_set()
        self._refresh_editor_block_pair_highlight()

    def _on_editor_outline_click(self, _event=None):
        """Ensures click on already selected outline entry still triggers jump."""

        if hasattr(self, "root"):
            self.root.after_idle(self._on_editor_outline_selected)

    def _refresh_editor_block_pair_highlight(self):
        """Highlights opening/closing marker pair for block at current cursor line."""

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

    def _set_editor_view_mode(self, mode: str):
        """Updates the selected editor/preview view mode and applies layout."""

        if mode != self.editor_view_mode_var.get():
            self.editor_view_mode_var.set(mode)
        self._apply_editor_view_mode()
        self._load_editor_for_current_input_if_needed()
        self._save_ui_settings()

    def _load_editor_for_current_input_if_needed(self):
        """Loads current input file into editor when editor pane is visible."""

        mode = self.editor_view_mode_var.get()
        if mode == EDITOR_VIEW_PREVIEW_ONLY:
            return

        input_path = self._get_input_path_if_exists()
        if input_path is None:
            return

        if self._editor_last_loaded_path == input_path:
            return

        self._load_editor_content(input_path)

    def _apply_editor_view_mode(self):
        """Shows preview area, editor area, or both depending on selected mode."""

        if self.editor_preview_paned is None or self.editor_container is None or self.preview_container is None:
            return

        mode = self.editor_view_mode_var.get()

        for pane in (self.editor_container, self.preview_container):
            try:
                self.editor_preview_paned.forget(pane)
            except Exception:
                pass

        if mode == EDITOR_VIEW_EDITOR_ONLY:
            self.editor_preview_paned.add(self.editor_container)
        elif mode == EDITOR_VIEW_BOTH:
            self.editor_preview_paned.add(self.editor_container)
            self.editor_preview_paned.add(self.preview_container)
            self._schedule_equal_split()
            if hasattr(self, "_reflow_responsive_sections"):
                self.root.after_idle(self._reflow_responsive_sections)
        else:
            self._close_editor_completion()
            self.editor_preview_paned.add(self.preview_container)
            if hasattr(self, "_reflow_responsive_sections"):
                self.root.after_idle(self._reflow_responsive_sections)

    def _schedule_equal_split(self):
        """Starts a guarded retry cycle to place the splitter in the middle."""

        self._equal_split_attempts = 0
        if bool(getattr(self, "_reduce_motion", False)):
            self._set_equal_split()
            return
        self.root.after_idle(self._set_equal_split)

    def _set_equal_split(self):
        """Sets a 50/50 split when both panes are visible."""

        if self.editor_preview_paned is None:
            return

        panes = self.editor_preview_paned.panes()
        if len(panes) != 2:
            return

        total_width = self.editor_preview_paned.winfo_width()
        if total_width <= 80:
            if bool(getattr(self, "_reduce_motion", False)):
                return
            if self._equal_split_attempts < 10:
                self._equal_split_attempts += 1
                self.root.after(30, self._set_equal_split)
            return

        try:
            preferences = getattr(self, "user_preferences", {})
            split_ratio = float(preferences.get("startup_split_ratio", 0.5) or 0.5)
            split_ratio = max(0.2, min(0.8, split_ratio))
            split_x = max(1, int(total_width * split_ratio))
            if hasattr(self.editor_preview_paned, "sashpos"):
                self.editor_preview_paned.sashpos(0, split_x)
            else:
                self.editor_preview_paned.sash_place(0, split_x, 1)
            self._equal_split_attempts = 0
        except tk.TclError:
            if bool(getattr(self, "_reduce_motion", False)):
                return
            if self._equal_split_attempts < 10:
                self._equal_split_attempts += 1
                self.root.after(30, self._set_equal_split)
