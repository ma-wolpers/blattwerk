"""Editor completion mixin: usage-based ranking and local usage tracking.

Ausgelagert aus `blatt_ui_editor.py` (300-Zeilen-Konvention, reiner
Struktur-Refactor ohne Verhaltensänderung), drittes von drei
Completion-Modulen. Sortiert Vorschläge nach lokal gelernten
Nutzungs-Scores (`local_config_store`) und protokolliert
Blocktyp-/Optionswert-Nutzung -- sowohl aus dem Completion-Popup heraus
als auch aus manuell getipptem Text beim Speichern.
"""

from __future__ import annotations

import re

from ..core.completion_catalogs import get_completion_block_types
from ..storage.local_config_store import (
    get_block_type_decay_scores,
    get_option_value_decay_scores,
    record_block_type_usage,
    record_block_type_usage_batch,
    record_option_value_usage,
)


class BlattwerkAppEditorCompletionRankingMixin:
    """Rankt Completion-Vorschläge und protokolliert Nutzungsdaten für spätere Rankings."""

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
