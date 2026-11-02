"""Programmatische Änderungen am Editortext, jede genau ein Undo-Schritt.

Alle Stellen, die den Editortext als Ganzes oder einen Bereich ersetzen
(Schriftwahl im Frontmatter, Tabellenumwandlung, Block-Einfügen), gehen hier
durch. Die Undo-Klammer liefert bw-guis `TextSurface.transact`: Separatoren
davor und danach, `autoseparators` immer wiederhergestellt, bei einem Fehler
mittendrin wird der schon angewandte Teil zurückgenommen. Vorher bauten zwei
Stellen das von Hand nach, eine davon setzte `autoseparators` danach fest auf
`True` und ließ den Separator davor weg.
"""

from __future__ import annotations

from bw_libs.shared_gui_core import ensure_bw_gui_on_path

ensure_bw_gui_on_path()
from bw_gui.contracts.multicursor import Edit
from bw_gui.runtime.multicursor_text import TextSurface


def editor_surface(editor) -> TextSurface:
    """Offset-Sicht auf den Editor: `offset(index)` und `index(offset)` zählen Zeichen wie Python.

    Die eine Umrechnung zwischen Tk-Indizes und Zeichen-Offsets (bw-gui misst
    dabei auch Emojis richtig), statt `len(editor.get("1.0", index))` an
    jeder Stelle.
    """
    return TextSurface(editor)


def replace_editor_range(editor, start: int, end: int, text: str) -> TextSurface:
    """Ersetzt die Zeichen-Offsets `[start, end)` durch `text` als einen Undo-Schritt.

    Returns:
        Die `TextSurface` des Editors, damit der Aufrufer Offsets wieder in
        Tk-Indizes umrechnen kann (`surface.index(offset)`).
    """
    surface = TextSurface(editor)
    surface.transact([Edit(start, end, text)])
    return surface


def replace_editor_text(editor, new_text: str) -> None:
    """Ersetzt den ganzen Editorinhalt als einen Undo-Schritt; die Scrollposition bleibt."""
    scroll_fraction = editor.yview()[0]
    surface = TextSurface(editor)
    surface.transact([Edit(0, surface.limit(), new_text)])
    editor.yview_moveto(scroll_fraction)
