"""Frontmatter-Fragen des Editors: steht der Cursor im Frontmatter, welche Werte stehen darin.

Aus `blatt_ui_editor_completion_context.py` ausgelagert (300-Zeilen-Regel).
Die Grenzen bestimmt ausschließlich der Core (`frontmatter_editing_lines`,
`parse_frontmatter` in `app/core/frontmatter.py`); hier wird nur der nötige
Anfang des Editortextes gelesen. Vorher zählte jede dieser Methoden selbst
`---`-Zeilen und hielt dabei auch eine spätere Trennlinie im Rumpf für eine
Frontmatter-Grenze.
"""

from __future__ import annotations

import yaml

from ..core.frontmatter import frontmatter_editing_lines, parse_frontmatter

FRONTMATTER_SCAN_LINE_LIMIT = 60
"""Sicherheitsnetz für `_editor_read_frontmatter_meta`: großzügig über jeder
realistischen Frontmatter-Größe. Verhindert bei einem Dokument ohne
schließendes `---`, dass das gesamte (potenziell sehr lange) Dokument
gelesen wird."""


class BlattwerkAppEditorFrontmatterMixin:
    """Beantwortet Frontmatter-Fragen der Completion anhand des Editortextes."""

    def _editor_head_text(self, last_line: int) -> str:
        """Editortext von Zeile 1 bis einschließlich `last_line` (ein einziger Widget-Zugriff)."""
        return self.editor_widget.get("1.0", f"{max(1, int(last_line)) + 1}.0")

    def _editor_cursor_in_frontmatter(self, line_no: int) -> bool:
        """True, wenn Zeile `line_no` beim Bearbeiten zum Frontmatter gehört.

        Liest nur bis zur Cursorzeile: Steht die Schlusszeile erst danach,
        gilt das Frontmatter im gelesenen Anfang als noch offen, und die
        Cursorzeile liegt richtig darin (siehe `frontmatter_editing_lines`).
        """
        if self.editor_widget is None:
            return False
        return line_no in frontmatter_editing_lines(self._editor_head_text(line_no))

    def _editor_read_frontmatter_meta(self) -> dict:
        """Liest die Frontmatter-Werte (`Fach`, `Stufe`, …) aus höchstens `FRONTMATTER_SCAN_LINE_LIMIT` Zeilen.

        Die einzige Stelle der Completion, die Frontmatter-WERTE liest.
        Kosten hängen von der Frontmatter-Größe ab, nicht von der
        Dokumentlänge. Ohne Schluss innerhalb der Grenze, oder bei
        ungültigem YAML, gibt es `{}` statt eines Fehlers. Das wird auf
        jedem Tastendruck im `!!…!!`-Zweig aufgerufen, daher ohne Cache,
        aber begrenzt.
        """
        if self.editor_widget is None:
            return {}
        try:
            meta, _rest = parse_frontmatter(self._editor_head_text(FRONTMATTER_SCAN_LINE_LIMIT))
        except yaml.YAMLError:
            return {}
        return meta if isinstance(meta, dict) else {}
