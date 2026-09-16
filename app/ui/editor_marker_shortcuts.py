"""Reine Editor-Logik für die Marker-Tasten (`*`/`_`/`=`/`~`/`^`/`` ` ``/`|`/`$`).

Kein Tkinter-Import -- testbar ohne GUI. Beantwortet ausschließlich "welche
Operation soll dieser Tastendruck auf diese Selektion anwenden": die
Marker-Templates (welche Zeichenfolge bedeutet welche Stufe) kommen aus
`app.core.inline_markup.syntax` (Single-Source-of-Truth), die
Randlauf-Messung ist eine kleine, in sich geschlossene Hilfsfunktion, die
absichtlich NICHT den vollständigen Dokument-Parser
(`app.core.inline_markup.parse_inline_markup`) missbraucht -- der ist für
ganze Dokumente gedacht, nicht für "was steht direkt links/rechts der
Selektion".

`blatt_ui_editor.py` liest `before`/`after` als kurzen Zeichen-Kontext
(z. B. 40 Zeichen) links/rechts der Selektion aus dem Editor-Widget, ruft
eine der `apply_*_marker`-Funktionen auf und wendet das zurückgelieferte
`MarkerEdit` an (Text ersetzen, neue Selektion setzen).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.inline_markup.syntax import marker_spec_by_name
from ..core.math_span_protection import find_math_span_ranges

_STAR_SPEC = marker_spec_by_name("emphasis_star")
_UNDERSCORE_SPEC = marker_spec_by_name("emphasis_underscore")
_HIGHLIGHT_DELIMITER = marker_spec_by_name("highlight").levels[0].delimiter
_SPOILER_DELIMITER = marker_spec_by_name("spoiler").levels[0].delimiter
_SUBSCRIPT_CHAR = marker_spec_by_name("subscript").key
_STRIKE_DELIMITER = marker_spec_by_name("strike").levels[0].delimiter
_SUPERSCRIPT_CHAR = marker_spec_by_name("superscript").key
_CODE_DELIMITER = marker_spec_by_name("code").levels[0].delimiter
_FENCED_CODE_DELIMITER = marker_spec_by_name("fenced_code").levels[0].delimiter
_MATH_DELIMITER = "$"
"""Delimiter-Zeichen/Stufenzahlen kommen ausschließlich aus `syntax.py`s
`MARKER_SPECS` -- dieses Modul definiert keine eigene Kopie der
Marker-Semantik, nur die davon unabhängige UX-Frage ("welche Operation löst
ein Tastendruck aus"). Ausnahme `_MATH_DELIMITER`: `$...$`-Formel-Markup ist
bewusst kein `MARKER_SPECS`-Eintrag (eigene Pipeline-Stufe, siehe
`math_span_protection.py`), daher hier als eigenständiges Literal geführt."""


@dataclass(frozen=True)
class MarkerEdit:
    """Beschreibt, wie eine Marker-Aktion den Text um die Selektion herum verändert.

    `strip_left`/`strip_right` sind Zeichenzahlen, die aus `before`
    (von dessen Ende) bzw. `after` (von dessen Anfang) entfernt und durch
    `replacement` ersetzt werden -- der Aufrufer ersetzt also den Bereich
    `before[-strip_left:] + selected + after[:strip_right]` durch
    `replacement`. `select_start`/`select_end` sind Offsets innerhalb von
    `replacement`, auf die die neue Selektion gesetzt werden soll (übliche
    Editor-Ergonomie: der "innere" Inhalt bleibt nach der Aktion markiert).
    """

    strip_left: int
    strip_right: int
    replacement: str
    select_start: int
    select_end: int


def selection_crosses_math_boundary(full_text: str, selection_start: int, selection_end: int) -> bool:
    """True, wenn `[selection_start, selection_end)` eine `$...$`/`$$...$$`-Formelgrenze überschneidet.

    Vollständig innerhalb oder vollständig außerhalb einer Formel ist ok;
    nur wenn genau ein Ende der Selektion strikt innerhalb einer Formel
    liegt und das andere nicht, würde die Marker-Aktion die Formel
    zerreißen -- das ist die konkrete Umsetzung der vom Nutzer verlangten
    Absicherung gegen Formatierungsfehler durch falsche Reihenfolge: die
    Aktion wird in diesem Fall verweigert statt etwas potenziell Kaputtes
    einzufügen (siehe `_on_editor_marker_key` in `blatt_ui_editor.py`).
    """
    for start, end in find_math_span_ranges(full_text):
        start_inside = start < selection_start < end
        end_inside = start < selection_end < end
        if start_inside != end_inside:
            return True
    return False


def _measure_left_run(before: str, char: str) -> int:
    count = 0
    index = len(before) - 1
    while index >= 0 and before[index] == char:
        count += 1
        index -= 1
    return count


def _measure_right_run(after: str, char: str) -> int:
    count = 0
    index = 0
    while index < len(after) and after[index] == char:
        count += 1
        index += 1
    return count


def _escalate_symmetric(before: str, selected: str, after: str, char: str, max_level: int) -> MarkerEdit:
    """Generische Eskalationslogik für `*`/`_`: Stufe = min(linker Lauf, rechter Lauf).

    Stufe `max_level` erreicht -> nächster Druck entfernt alles (Stufe 0).
    Asymmetrische Läufe (z. B. bei `**so*etwas***`, wenn nur ein Teil davon
    ausgewählt ist) werden bewusst NICHT geraten/repariert -- nur das
    Minimum beider Seiten wird als bestehende Stufe gewertet und entfernt,
    der Rest bleibt unangetastet stehen.
    """
    left = _measure_left_run(before, char)
    right = _measure_right_run(after, char)
    level = min(left, right, max_level)

    next_level = 0 if level >= max_level else level + 1
    marker = char * next_level
    replacement = f"{marker}{selected}{marker}"
    return MarkerEdit(
        strip_left=level,
        strip_right=level,
        replacement=replacement,
        select_start=len(marker),
        select_end=len(marker) + len(selected),
    )


def apply_star_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`*` -> kursiv -> `**` fett -> `***` fett+kursiv -> 4. Druck entfernt alles."""
    return _escalate_symmetric(before, selected, after, _STAR_SPEC.key, max_level=len(_STAR_SPEC.levels))


def apply_underscore_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`_` -> kursiv -> `__` unterstrichen -> 3. Druck entfernt alles."""
    return _escalate_symmetric(before, selected, after, _UNDERSCORE_SPEC.key, max_level=len(_UNDERSCORE_SPEC.levels))


def _toggle_pair(before: str, selected: str, after: str, delimiter: str) -> MarkerEdit:
    """`=`/`\\|`-Mechanik: erster Druck fügt das volle Paar (`==`/`\\|\\|`) direkt ein, zweiter entfernt es wieder."""
    length = len(delimiter)
    already_wrapped = before.endswith(delimiter) and after.startswith(delimiter)
    if already_wrapped:
        return MarkerEdit(
            strip_left=length,
            strip_right=length,
            replacement=selected,
            select_start=0,
            select_end=len(selected),
        )
    replacement = f"{delimiter}{selected}{delimiter}"
    return MarkerEdit(
        strip_left=0,
        strip_right=0,
        replacement=replacement,
        select_start=length,
        select_end=length + len(selected),
    )


def apply_highlight_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`=` -> `==Hervorhebung==` direkt beim ersten Druck; zweiter Druck entfernt wieder."""
    return _toggle_pair(before, selected, after, _HIGHLIGHT_DELIMITER)


def apply_pipe_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`|` -> `||Spoiler||` direkt beim ersten Druck; zweiter Druck entfernt wieder."""
    return _toggle_pair(before, selected, after, _SPOILER_DELIMITER)


def apply_dollar_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`$` -> `$Formel$` direkt beim ersten Druck; zweiter Druck entfernt wieder."""
    return _toggle_pair(before, selected, after, _MATH_DELIMITER)


def _prefix_wrapped(before: str, selected: str, after: str, char: str) -> tuple[bool, int, int]:
    """Prüft, ob die Selektion bereits von der Präfix-Mechanik (`~x` oder `~{x}`) umschlossen ist.

    Liefert `(ist_umschlossen, strip_left, strip_right)`.
    """
    if before.endswith(char + "{") and after.startswith("}"):
        return True, 2, 1
    if before.endswith(char) and not before.endswith(char * 2) and len(selected) == 1:
        return True, 1, 0
    return False, 0, 0


def apply_tilde_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`~`-Taste: Präfix-Tiefstellung (Stufe 1) -> `~~durchgestrichen~~` (Stufe 2, symmetrisch, ohne Klammern)."""
    if before.endswith(_STRIKE_DELIMITER) and after.startswith(_STRIKE_DELIMITER):
        return MarkerEdit(strip_left=2, strip_right=2, replacement=selected, select_start=0, select_end=len(selected))

    wrapped, strip_left, strip_right = _prefix_wrapped(before, selected, after, _SUBSCRIPT_CHAR)
    if wrapped:
        replacement = f"{_STRIKE_DELIMITER}{selected}{_STRIKE_DELIMITER}"
        return MarkerEdit(
            strip_left=strip_left,
            strip_right=strip_right,
            replacement=replacement,
            select_start=len(_STRIKE_DELIMITER),
            select_end=len(_STRIKE_DELIMITER) + len(selected),
        )

    if len(selected) == 1:
        replacement = f"{_SUBSCRIPT_CHAR}{selected}"
    else:
        replacement = f"{_SUBSCRIPT_CHAR}{{{selected}}}"
    return MarkerEdit(strip_left=0, strip_right=0, replacement=replacement, select_start=0, select_end=len(replacement))


def apply_caret_marker(before: str, selected: str, after: str) -> MarkerEdit:
    """`^`-Taste: Präfix-Hochstellung, einzige Stufe -- erneuter Druck entfernt sie wieder."""
    wrapped, strip_left, strip_right = _prefix_wrapped(before, selected, after, _SUPERSCRIPT_CHAR)
    if wrapped:
        return MarkerEdit(
            strip_left=strip_left,
            strip_right=strip_right,
            replacement=selected,
            select_start=0,
            select_end=len(selected),
        )

    if len(selected) == 1:
        replacement = f"{_SUPERSCRIPT_CHAR}{selected}"
    else:
        replacement = f"{_SUPERSCRIPT_CHAR}{{{selected}}}"
    return MarkerEdit(strip_left=0, strip_right=0, replacement=replacement, select_start=0, select_end=len(replacement))


def apply_backtick_marker(before: str, selected: str, after: str, is_multiline: bool) -> MarkerEdit:
    """`` ` ``-Taste: Inline-Code-Toggle bei einzeiliger Auswahl, Fenced-Block-Einfügung bei mehrzeiliger.

    Mehrzeilig wird nur EINGEFÜGT (kein Entfernen eines bestehenden Blocks
    in dieser ersten Version -- siehe Plan).
    """
    if is_multiline:
        replacement = f"{_FENCED_CODE_DELIMITER}\n{selected}\n{_FENCED_CODE_DELIMITER}"
        inner_start = len(_FENCED_CODE_DELIMITER) + 1
        return MarkerEdit(
            strip_left=0,
            strip_right=0,
            replacement=replacement,
            select_start=inner_start,
            select_end=inner_start + len(selected),
        )

    if before.endswith(_CODE_DELIMITER) and after.startswith(_CODE_DELIMITER):
        return MarkerEdit(strip_left=1, strip_right=1, replacement=selected, select_start=0, select_end=len(selected))

    replacement = f"{_CODE_DELIMITER}{selected}{_CODE_DELIMITER}"
    return MarkerEdit(strip_left=0, strip_right=0, replacement=replacement, select_start=1, select_end=1 + len(selected))
