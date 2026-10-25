"""Editor completion mixin: Erwartungstypen in der Punktklammer eines Klausur-Lösungspunkts.

Steht der Cursor in einer `.kbw` in der Kopfzeile eines Lösungspunkts
(`1. …`) innerhalb von `:::solution` direkt nach `(0,5P ` (bzw. mitten im
schon begonnenen Typ-Wort), schlägt die Completion die Erwartungstypen vor.
Übernommen wird immer der volle Name (`Ansatz`), auch wenn ein Kürzel
getippt wurde -- Entscheidung der Nutzerin (2026-10-25).

Bewusst ein eigenes Modul neben den drei bestehenden Completion-Modulen
(Kontext, Popup, Ranking): `blatt_ui_editor_completion_context.py` liegt
schon über dem 300-Zeilen-Limit, jede Berührung würde den Guardrail
auslösen. Das Popup fragt diesen Kontext deshalb *vor*
`_collect_editor_completion_context` ab (`_open_editor_completion`).

Fachwissen kommt nur aus dem Core: die Grammatik der Typ-Stelle aus
`points_suffix.find_kind_slot`, die Kopfzeilen-Regel aus
`solution_structure.ITEM_HEAD_RE`, Typen und Detailtexte aus
`completion_catalogs`.

GRENZE: Der Dokumenttyp wird über den Pfad des aktiven Tabs bestimmt (wie
bei Diagnostik und Klausur-Übersicht); ein Tab ohne Pfad bekommt keine
Erwartungstyp-Vorschläge.
"""

from __future__ import annotations

import re

from ..core.completion_catalogs import (
    get_completion_expectation_kind_detail,
    get_completion_expectation_kinds,
)
from ..core.document_type_registry import DOCUMENT_TYPE_EXAM
from ..core.points_suffix import find_kind_slot
from ..core.solution_structure import ITEM_HEAD_RE

_RIGHT_OF_SLOT_RE = re.compile(r"^\s*\)?\s*$")
"""Rechts vom Cursor darf höchstens noch die schließende Klammer stehen."""


class BlattwerkAppEditorCompletionPointsMixin:
    """Schlägt Erwartungstypen nach `(Zahl P ` in Klausur-Lösungspunkten vor."""

    def _collect_expectation_kind_completion_context(self, auto: bool):
        """Returns a completion context for expectation kinds at the cursor, else ``None``.

        Alle Bedingungen müssen gelten, geprüft von billig nach teuer (die
        Funktion läuft bei jedem auslösenden Tastendruck):

        1. Der Text links vom Cursor endet in der Typ-Stelle eines
           Punkt-Suffixes (`find_kind_slot`), rechts steht höchstens `)`.
        2. Die Zeile ist eine Lösungspunkt-Kopfzeile (`ITEM_HEAD_RE`).
        3. Der umschließende Block ist `:::solution`.
        4. Der aktive Tab ist eine Klausur (`.kbw`).

        Der Rückgabewert hat dieselbe Form wie bei
        `_collect_editor_completion_context` (`suggestions`,
        `replace_start`/`replace_end`, `kind`), ersetzt wird nur das schon
        getippte Typ-Präfix. Kein Popup, wenn kein Typ passt oder genau ein
        Typ übrig ist, dessen voller Name schon dasteht.

        Args:
            auto: ``True`` beim automatischen Öffnen während des Tippens,
                ``False`` bei `Strg+Leertaste`. Respektiert wie der
                allgemeine Kontext die Einstellung `manual_only`.
        """
        if self.editor_widget is None:
            return None
        preferences = getattr(self, "user_preferences", {})
        if auto and str(preferences.get("completion_context_sources", "smart") or "smart") == "manual_only":
            return None

        line_no_text, col_text = self.editor_widget.index("insert").split(".")
        line_no, cursor_col = int(line_no_text), int(col_text)
        line_text = self.editor_widget.get(f"{line_no}.0", f"{line_no}.end")
        slot = find_kind_slot(line_text[:cursor_col])
        if slot is None or not _RIGHT_OF_SLOT_RE.match(line_text[cursor_col:]):
            return None
        if not ITEM_HEAD_RE.match(line_text):
            return None
        if self._editor_get_enclosing_block_type(line_no) != "solution":
            return None
        if self._editor_active_document_type() != DOCUMENT_TYPE_EXAM:
            return None

        start_col, prefix = slot
        suggestions = self._build_expectation_kind_suggestions(prefix)
        if not suggestions:
            return None
        if len(suggestions) == 1 and suggestions[0]["insert_text"].casefold() == prefix.casefold():
            return None
        return {
            "suggestions": suggestions,
            "replace_start": f"{line_no}.{start_col}",
            "replace_end": f"{line_no}.{cursor_col}",
            "kind": "expectation_kind",
        }

    @staticmethod
    def _build_expectation_kind_suggestions(prefix: str) -> list[dict]:
        """Builds the popup rows for all expectation kinds matching `prefix`.

        Label `💡 Ansatz (An)` zeigt Symbol und Kürzel zur Orientierung,
        eingefügt wird der volle Name (`insert_text = kind.label`). Das
        Detailfeld zeigt den Legendensatz (`get_completion_expectation_kind_detail`).
        Reihenfolge = Katalog/Legende, kein nutzungsbasiertes Ranking.
        """
        return [
            {
                "label": f"{kind.symbol} {kind.label} ({kind.abbreviation})",
                "insert_text": kind.label,
                "kind": "expectation_kind",
                "detail": get_completion_expectation_kind_detail(kind),
            }
            for kind in get_completion_expectation_kinds(prefix)
        ]

    def _editor_active_document_type(self) -> str | None:
        """Returns the document type of the active tab via its path, or ``None`` without a path.

        Gleiche Herleitung wie `_refresh_editor_diagnostics`: Pfad aus
        `_active_document_tab_state()`, Typ über `_read_document_type`
        (Endung bzw. temporäre Markdown-Interpretation).
        """
        try:
            tab_state = self._active_document_tab_state()
        except Exception:
            return None
        raw_path = str(tab_state.get("path", "") or "").strip() if isinstance(tab_state, dict) else ""
        return self._read_document_type(raw_path) if raw_path else None
