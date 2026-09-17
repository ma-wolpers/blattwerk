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

from ..core.blatt_kern_shared_parsing import split_front_matter
from ..core.completion_catalogs import (
    get_completion_block_option_detail,
    get_completion_block_type_detail,
    get_completion_block_types,
    get_completion_frontmatter_field_detail,
    get_completion_frontmatter_field_values,
    get_completion_frontmatter_value_detail,
    get_completion_operator_details,
    get_completion_operator_forms,
    get_completion_option_value_abbreviation_hints,
    get_completion_option_value_detail,
    get_completion_option_values,
    get_completion_options_for_block,
    get_self_closing_block_types,
)
from ..storage.local_config_store import get_option_value_decay_scores

_FRONTMATTER_SCAN_LINE_LIMIT = 60
"""Sicherheitsnetz für `_editor_read_frontmatter_meta`: grosszügig über jeder
realistischen Frontmatter-Grösse, verhindert bei einem Dokument ohne
schliessendes `---` (kaputtes/fehlendes Frontmatter), dass der Scan
versehentlich das gesamte (potenziell sehr lange) Dokument liest."""

_EDITOR_FRONTMATTER_KEYS = (
    "Titel",
    "Fach",
    "Thema",
    "show_student_header",
    "show_document_header",
    "mode",
    "lochen",
    "copyright",
    "Stufe",
)


def _format_option_value_label(value: str, abbreviation_hints: dict[str, str]) -> str:
    """Appends a curated abbreviation hint to a completion label, e.g. `gruppe (ga)`.

    Display-only: the abbreviation shown here is never the text this
    completion path inserts (`insert_text` always stays the canonical
    long value), regardless of whether the abbreviation is itself a
    separately valid, accepted value.
    """

    abbreviation = abbreviation_hints.get(value.lower())
    if not abbreviation:
        return value
    return f"{value} ({abbreviation})"


class BlattwerkAppEditorCompletionContextMixin:
    """Erkennt, welche Art Vervollständigung an der aktuellen Cursorposition passt."""

    @staticmethod
    def _is_single_exact_completion_match(prefix: str, suggestions: list[dict]) -> bool:
        """Returns True when exactly one suggestion remains and it already equals the typed prefix exactly.

        Verhindert ein Popup mit einem einzigen, bereits fertig getippten
        Vorschlag (z. B. Cursor direkt nach `:::lines`, wenn `lines` der
        einzige Blocktyp ist, der mit `lines` beginnt) -- kein sinnvoller
        weiterer Vorschlag mehr nötig. Vergleicht bewusst gegen `label`
        (der getippte Name selbst), nicht `insert_text`: bei selbstschließenden
        Blocktypen enthält `insert_text` zusätzlich das automatisch
        mitgelieferte schließende `:::` (siehe `get_self_closing_block_types`)
        und würde sonst nie exakt zum getippten Präfix passen.
        """
        if not prefix or len(suggestions) != 1:
            return False
        sole = suggestions[0]
        candidate_text = str(sole.get("label") or sole.get("insert_text") or "")
        return candidate_text.strip().lower() == prefix.strip().lower()

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

                self_closing_block_types = get_self_closing_block_types()
                suggestions = [
                    {
                        "label": block_type,
                        "insert_text": (
                            f"{block_type} :::" if block_type in self_closing_block_types else block_type
                        ),
                        "kind": "block_type",
                        "block_type": block_type,
                        "detail": get_completion_block_type_detail(block_type),
                    }
                    for block_type in get_completion_block_types()
                    if block_type.startswith(block_prefix)
                ]
                if self._is_single_exact_completion_match(block_prefix, suggestions):
                    return None
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
                    suggestions = self._build_block_option_key_suggestions(block_token, block_allowed_options)
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
                    suggestions = self._build_block_option_key_suggestions(
                        block_token, block_allowed_options, exclude=used_option_keys
                    )
                    if not suggestions:
                        # Every option is already used on this line -- re-offer
                        # all of them rather than an empty popup.
                        suggestions = self._build_block_option_key_suggestions(block_token, block_allowed_options)

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

                    suggestions = self._build_block_option_key_suggestions(
                        block_token, block_allowed_options, prefix=key_prefix
                    )
                    if self._is_single_exact_completion_match(key_prefix, suggestions):
                        return None
                    return {
                        "suggestions": suggestions,
                        "replace_start": f"{line_no}.{key_match.start(1)}",
                        "replace_end": f"{line_no}.{key_match.end(1)}",
                        "kind": "block_option",
                    }

        if self._editor_cursor_in_frontmatter(line_no):
            field_value_match = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_\-]*):\s*([^\s]*)$", left_text)
            if field_value_match:
                field_name = field_value_match.group(2)
                value_prefix = field_value_match.group(3) or ""
                suggestions = self._build_frontmatter_value_suggestions(
                    field_name=field_name, value_prefix=value_prefix
                )
                if suggestions:
                    value_start = field_value_match.start(3)
                    value_end = field_value_match.end(3)
                    return {
                        "suggestions": suggestions,
                        "replace_start": f"{line_no}.{value_start}",
                        "replace_end": f"{line_no}.{value_end}",
                        "kind": "frontmatter_value",
                        "meta": {"field_name": field_name},
                    }

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
                        "detail": get_completion_frontmatter_field_detail(field_name),
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

        operator_delimiters = list(re.finditer(r"!!", left_text))
        if len(operator_delimiters) % 2 == 1 and not self._editor_cursor_in_frontmatter(line_no):
            # Odd count = the last `!!` opened a marker that's still open at
            # the cursor. An even count means every `!!` on this line
            # before the cursor is already paired off (e.g. cursor sits
            # right after a closed "!!Bestimmen!! ") -- a naive
            # "last !! to end of line" regex would wrongly treat the
            # trailing plain text as an open marker's partial content.
            partial_start = operator_delimiters[-1].end()
            partial = left_text[partial_start:]
            meta = self._editor_read_frontmatter_meta()
            suggestions = self._build_operator_suggestions(
                fach=meta.get("Fach"), stufe=meta.get("Stufe"), value_prefix=partial
            )
            if suggestions:
                return {
                    "suggestions": suggestions,
                    "replace_start": f"{line_no}.{partial_start}",
                    "replace_end": f"{line_no}.{cursor_col}",
                    "kind": "operator_value",
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

    def _editor_read_frontmatter_meta(self):
        """Reads and parses ONLY the frontmatter block (line 1 up to the second `---`),
        not the whole buffer -- the single place in the completion layer that
        extracts actual frontmatter VALUES (`Fach`, `Stufe`, ...), as opposed
        to `_editor_cursor_in_frontmatter`/`_editor_document_has_frontmatter`
        above, which only answer boundary questions and never read values. A
        future need for another frontmatter value should go through this
        method, not a fifth scan function.

        Cost scales with frontmatter size (typically <15 lines), not
        document length -- deliberately NOT `split_front_matter(self.editor_widget.get("1.0", "end-1c"))`
        on the full buffer, which would scale with a growing task body
        below it for no reason. `_FRONTMATTER_SCAN_LINE_LIMIT` is a safety
        net for a document with no closing `---` (broken/missing
        frontmatter) -- the scan gives up and returns `{}` rather than
        reading the rest of a potentially very long document.

        No debounce, no extra caching: this method is only reached from the
        already-narrow "cursor sits inside an open `!!...!!`" branch, and a
        bounded scan of a handful of lines is cheap enough on every
        keystroke without either -- the same "make it cheap by
        construction" standard the rest of completion already relies on.
        """
        if self.editor_widget is None:
            return {}

        lines = []
        delimiter_count = 0
        for line_no in range(1, _FRONTMATTER_SCAN_LINE_LIMIT + 1):
            if self.editor_widget.compare(f"{line_no}.0", ">=", "end-1c"):
                break  # reached end of document before a second `---`
            text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
            lines.append(text)
            if text.strip() == "---":
                delimiter_count += 1
                if delimiter_count == 2:
                    break

        if delimiter_count < 2:
            return {}
        meta, _rest = split_front_matter("\n".join(lines))
        return meta or {}

    def _build_block_option_key_suggestions(self, block_type: str, options, *, prefix: str = "", exclude=()):
        """Builds `key=` completion candidates for block option KEYS.

        Shared by all three block-option trigger points in
        `_collect_editor_completion_context` (right after `:::block `, a
        partially-typed key, or after a trailing space with already-used
        keys excluded) -- previously three near-identical list
        comprehensions, now one place that also attaches `"detail"`.
        `prefix` matching is deliberately case-sensitive (option keys are
        always declared lowercase in `BLOCK_OPTION_SPECS`, unlike
        frontmatter field names); `exclude` is compared case-insensitively
        against already-used keys on the line.
        """

        exclude_norm = {str(key).strip().lower() for key in exclude}
        return [
            {
                "label": option,
                "insert_text": f"{option}=",
                "kind": "block_option",
                "detail": get_completion_block_option_detail(block_type, option),
            }
            for option in options
            if option.startswith(prefix) and option.lower() not in exclude_norm
        ]

    def _build_option_value_suggestions(self, *, block_type: str, option_key: str, value_prefix: str):
        """Builds option value candidates with optional learned ranking data."""

        block_type_norm = str(block_type or "").strip().lower()
        option_key_norm = str(option_key or "").strip().lower()
        prefix_norm = str(value_prefix or "").strip().lower()

        preferences = getattr(self, "user_preferences", {})
        value_style = str(preferences.get("option_value_language_style", "german") or "german")
        show_abbreviations = bool(preferences.get("option_value_show_abbreviations", False))

        defaults = list(
            get_completion_option_values(block_type_norm, option_key_norm, value_style=value_style)
        )
        abbreviation_hints = (
            get_completion_option_value_abbreviation_hints(
                block_type_norm, option_key_norm, value_style
            )
            if show_abbreviations
            else {}
        )

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
                "label": _format_option_value_label(value, abbreviation_hints),
                "insert_text": value,
                "kind": "option_value",
                "block_type": block_type_norm,
                "option_key": option_key_norm,
                "detail": get_completion_option_value_detail(block_type_norm, option_key_norm, value),
            }
            for value in filtered
        ]

    def _build_frontmatter_value_suggestions(self, *, field_name: str, value_prefix: str):
        """Builds value candidates for an enum-kind frontmatter field (`Stufe:`, `mode:`, `document_type:`, ...).

        Mirrors `_build_option_value_suggestions`'s shape one level up, but
        deliberately simpler -- no learned-ranking/abbreviation-style
        catalog lookup, since those are specific to block options'
        German/English concept catalogs (`work`/`action`/`align`/`hint`),
        which frontmatter fields don't have. Any field the validator
        doesn't know as `kind="enum"` (or an unknown field name) yields no
        suggestions, matching `get_completion_frontmatter_field_values`'s
        contract.
        """

        prefix_norm = str(value_prefix or "").strip().lower()
        values = get_completion_frontmatter_field_values(field_name)
        filtered = [value for value in values if value.lower().startswith(prefix_norm)]
        return [
            {
                "label": value,
                "insert_text": value,
                "kind": "frontmatter_value",
                "field_name": field_name,
                "detail": get_completion_frontmatter_value_detail(field_name, value),
            }
            for value in filtered
        ]

    def _build_operator_suggestions(self, *, fach, stufe, value_prefix: str):
        """Builds `!!...!!`-operator suggestion candidates for the document's `Fach`/`Stufe`.

        Mirrors `_build_frontmatter_value_suggestions`'s shape and
        simplicity -- no learned-ranking, no abbreviation catalog. Reads
        `get_completion_operator_forms` (the official `vorschlag` labels,
        never the full `formen` conjugation list -- see
        `operator_legend.py`), filtered by the already-typed prefix.
        """

        prefix_norm = str(value_prefix or "").strip().lower()
        suggestions = get_completion_operator_forms(fach, stufe)
        filtered = [value for value in suggestions if value.lower().startswith(prefix_norm)]
        details = get_completion_operator_details(fach, stufe)
        return [
            {
                "label": value,
                "insert_text": value,
                "kind": "operator_value",
                "detail": details.get(value),
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
