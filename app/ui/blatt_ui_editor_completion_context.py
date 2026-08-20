"""Editor completion mixin: derives suggestion context from cursor position and buffer text.

Ausgelagert aus `blatt_ui_editor.py` (300-Zeilen-Konvention, reiner
Struktur-Refactor ohne Verhaltensänderung) als erstes von drei
Completion-Modulen. Dieses Modul enthält ausschließlich die
Kontext-Erkennung ("wo steht der Cursor, welche Art Vorschlag passt
hier") -- Popup-Rendering lebt in `blatt_ui_editor_completion_popup.py`,
Nutzungsbasiertes Ranking in `blatt_ui_editor_completion_ranking.py`.
"""

from __future__ import annotations

import re

from ..core.completion_catalogs import (
    get_completion_block_types,
    get_completion_options_for_block,
    get_completion_option_values,
)
from ..storage.local_config_store import get_option_value_decay_scores

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


class BlattwerkAppEditorCompletionContextMixin:
    """Erkennt, welche Art Vervollständigung an der aktuellen Cursorposition passt."""

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
