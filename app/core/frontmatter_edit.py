"""Die eine strukturierte Edit-Engine für Frontmatter (Invariante I6).

Migration (`app/core/migration/`), die Marker-Quick-Fixes (FM007/FM008/
FM010) und Speichern-unter mit Typwechsel ändern Frontmatter-Schlüssel. Alle
drei nutzen ausschließlich diese Engine, damit sie sich bei BOM, Kommentaren,
Block-Scalars, Quotes und Zeilenenden nie unterschiedlich verhalten.

Arbeitsweise -- bewusst kein YAML-Round-Trip (der würde Kommentare,
Quotes und Formatierung verlieren):

1. Grenzen über `frontmatter.frontmatter_bounds`.
2. Den Rumpf zeilenweise in *Top-Level-Einträge* zerlegen: eine Zeile in
   Spalte 0 der Form `key:` plus ihre Fortsetzungszeilen (eingerückt, oder
   Leerzeilen, auf die noch eingerückte Zeilen folgen -- z. B. in einem
   `|`/`>`-Block-Scalar). Kommentar- und Leerzeilen in Spalte 0 zwischen
   Einträgen gehören zu keinem Eintrag.
3. Nur ganze Eintrags-Zeilenbereiche ersetzen, entfernen oder einfügen.
4. Verifizieren: (a) die neue YAML-Semantik entspricht genau der erwarteten
   Änderung, (b) alle Zeichen außerhalb der editierten Bereiche sind
   unverändert, (c) doppelte Schlüssel, Flow-Mappings oder YAML-Fehler
   machen den Edit unsicher (`EditUnsafe`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import yaml

from .frontmatter import (
    BOM,
    frontmatter_bounds,
    iter_lines_with_offsets,
    load_frontmatter_yaml,
    split_line_ending,
)

_KEY_LINE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*:(?:\s|$)")
_SIMPLE_SCALAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")


class EditUnsafe(Exception):
    """Der gewünschte Frontmatter-Edit lässt sich nicht sicher ausführen."""


@dataclass(frozen=True)
class _Entry:
    """Ein Top-Level-Eintrag als Zeichenbereich `[start, end)` im Gesamttext."""

    key: str
    start: int
    end: int
    first_line_ending: str


def _parse_entries(text: str, body_start: int, body_end: int) -> list[_Entry]:
    """Zerlegt den Frontmatter-Rumpf in Top-Level-Einträge (siehe Moduldoku).

    Raises:
        EditUnsafe: bei Spalte-0-Zeilen, die weder Schlüssel, Kommentar noch
            leer sind (Flow-Mapping, Listen, komplexe Keys), bei eingerückten
            Zeilen vor dem ersten Schlüssel oder bei doppelten Schlüsseln.
    """
    lines = [
        (offset, line)
        for offset, line in iter_lines_with_offsets(text[:body_end], body_start)
    ]
    entries: list[_Entry] = []
    seen: set[str] = set()
    index = 0
    while index < len(lines):
        offset, line = lines[index]
        content, ending = split_line_ending(line)
        if not content.strip() or content.startswith("#"):
            index += 1
            continue
        if content[0] in " \t":
            raise EditUnsafe("Eingerückte Zeile ohne vorangehenden Top-Level-Schlüssel.")
        match = _KEY_LINE_RE.match(content)
        if match is None:
            raise EditUnsafe(f"Nicht unterstützte Frontmatter-Zeile: {content[:40]!r}")
        key = match.group("key")
        if key in seen:
            raise EditUnsafe(f"Doppelter Frontmatter-Schlüssel: {key}")
        seen.add(key)
        end_index = index + 1
        while end_index < len(lines):
            candidate, _ = split_line_ending(lines[end_index][1])
            if candidate[:1] in (" ", "\t") and candidate.strip():
                end_index += 1
                continue
            if not candidate.strip() and _next_content_is_indented(lines, end_index):
                end_index += 1
                continue
            break
        end_offset = lines[end_index - 1][0] + len(lines[end_index - 1][1])
        entries.append(_Entry(key=key, start=offset, end=end_offset, first_line_ending=ending))
        index = end_index
    return entries


def _next_content_is_indented(lines: list[tuple[int, str]], index: int) -> bool:
    """Prüft, ob die nächste nicht-leere Zeile ab `index` eingerückt ist."""
    for _offset, line in lines[index:]:
        content, _ = split_line_ending(line)
        if content.strip():
            return content[:1] in (" ", "\t")
    return False


def _load_strict(body: str) -> dict:
    """Lädt einen Rumpf strikt (Duplikate verboten) und verlangt ein Mapping."""
    try:
        loaded = load_frontmatter_yaml(body, reject_duplicates=True)
    except yaml.YAMLError as error:
        raise EditUnsafe(f"Frontmatter ist kein eindeutiges YAML: {error}") from error
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise EditUnsafe("Frontmatter ist kein Mapping.")
    return loaded


def _dominant_line_ending(text: str) -> str:
    """Zeilenende-Stil des Dokuments (das der ersten Zeile; Standard `\\n`)."""
    newline = text.find("\n")
    if newline > 0 and text[newline - 1] == "\r":
        return "\r\n"
    return "\n"


class FrontmatterEditor:
    """Sammelt Frontmatter-Edits auf einem Dokumenttext und liefert das verifizierte Ergebnis.

    Usage::

        editor = FrontmatterEditor(text)
        editor.remove_key("mode", when=lambda value: True)
        editor.set_scalar("document_type", "exam")
        new_text = editor.result()   # wirft EditUnsafe, falls nicht sicher

    Alle Operationen arbeiten auf dem *aktuellen* Zwischenstand, `result()`
    verifiziert gegen den Ursprungstext.
    """

    def __init__(self, text: str) -> None:
        self._original = text or ""
        self._text = self._original
        self._expected_removed: set[str] = set()
        self._expected_set: dict[str, str] = {}

    def _bounds_or_raise(self):
        bounds = frontmatter_bounds(self._text)
        if bounds is None:
            raise EditUnsafe("Dokument hat kein Frontmatter.")
        return bounds

    def _entries(self):
        bounds = self._bounds_or_raise()
        return bounds, _parse_entries(self._text, bounds.body_start, bounds.close_line_start)

    def has_frontmatter(self) -> bool:
        """Ob der aktuelle Zwischenstand ein Frontmatter besitzt."""
        return frontmatter_bounds(self._text) is not None

    def ensure_frontmatter(self) -> None:
        """Legt ein leeres Frontmatter an, falls keines existiert.

        Raises:
            EditUnsafe: wenn der Text nach Leerzeilen mit `---` beginnt. Das
                ist mehrdeutig (z. B. ein toleranter Kurzentwurf-Kopf), und
                ein zweiter Block davor würde das Dokument zerstören.
        """
        if self.has_frontmatter():
            return
        has_bom = self._text.startswith(BOM)
        head = self._text[1:] if has_bom else self._text
        if head.lstrip(" \t\r\n").startswith("---"):
            raise EditUnsafe("Mehrdeutiger Dokumentanfang (Leerzeilen vor ---).")
        ending = _dominant_line_ending(head)
        prefix = BOM if has_bom else ""
        self._text = f"{prefix}---{ending}---{ending}{head}"

    def remove_key(self, name: str, when: Callable[[object], bool] = lambda _value: True) -> bool:
        """Entfernt den Top-Level-Eintrag `name`, wenn `when(wert)` zutrifft.

        Returns:
            ``True``, wenn etwas entfernt wurde.
        """
        bounds, entries = self._entries()
        for entry in entries:
            if entry.key != name:
                continue
            value = _load_strict(self._text[entry.start : entry.end]).get(name)
            if not when(value):
                return False
            self._text = self._text[: entry.start] + self._text[entry.end :]
            self._expected_removed.add(name)
            self._expected_set.pop(name, None)
            return True
        return False

    def set_scalar(self, name: str, value: str) -> None:
        """Setzt `name: value` (ersetzt den Eintrag oder fügt ihn als erste Zeile ein).

        Nur einfache Bezeichner als Wert (z. B. kanonische `document_type`-
        Werte), damit kein YAML-Quoting nötig ist.
        """
        if not _SIMPLE_SCALAR_RE.match(value or ""):
            raise ValueError(f"Nur einfache Bezeichner erlaubt, nicht {value!r}")
        bounds, entries = self._entries()
        for entry in entries:
            if entry.key == name:
                ending = entry.first_line_ending or bounds.open_line_ending
                self._text = f"{self._text[: entry.start]}{name}: {value}{ending}{self._text[entry.end :]}"
                break
        else:
            line = f"{name}: {value}{bounds.open_line_ending}"
            self._text = self._text[: bounds.body_start] + line + self._text[bounds.body_start :]
        self._expected_set[name] = value
        self._expected_removed.discard(name)

    def result(self) -> str:
        """Liefert den editierten Text nach vollständiger Verifikation.

        Raises:
            EditUnsafe: wenn Semantik oder Rest-Zeichen nicht exakt stimmen.
        """
        if self._text == self._original:
            return self._text
        new_bounds = frontmatter_bounds(self._text)
        if new_bounds is None:
            raise EditUnsafe("Frontmatter nach dem Edit nicht mehr erkennbar.")
        new_meta = _load_strict(new_bounds.body(self._text))
        old_bounds = frontmatter_bounds(self._original)
        old_meta = _load_strict(old_bounds.body(self._original)) if old_bounds else {}
        expected = {k: v for k, v in old_meta.items() if k not in self._expected_removed}
        expected.update(self._expected_set)
        if new_meta != expected:
            raise EditUnsafe("YAML-Semantik nach dem Edit weicht von der erwarteten ab.")
        if old_bounds is None:
            # ensure_frontmatter: BOM bleibt vorn, alles Bisherige folgt unverändert.
            had_bom = self._original.startswith(BOM)
            original_head = self._original[1:] if had_bom else self._original
            if self._text.startswith(BOM) != had_bom or self._text[new_bounds.end :] != original_head:
                raise EditUnsafe("Dokumenttext beim Anlegen des Frontmatters verändert.")
        elif self._text[new_bounds.close_line_start :] != self._original[old_bounds.close_line_start :]:
            raise EditUnsafe("Text hinter dem Frontmatter wurde verändert.")
        if old_bounds and self._text[: new_bounds.body_start] != self._original[: old_bounds.body_start]:
            raise EditUnsafe("Text vor dem Frontmatter-Rumpf wurde verändert.")
        touched = self._expected_removed | set(self._expected_set)
        old_untouched = (
            _untouched_body_text(self._original, old_bounds, touched) if old_bounds else ""
        )
        if _untouched_body_text(self._text, new_bounds, touched) != old_untouched:
            raise EditUnsafe("Nicht editierte Frontmatter-Zeilen wurden verändert.")
        return self._text


def _untouched_body_text(text: str, bounds, touched_keys: set[str]) -> str:
    """Rumpftext ohne die Einträge der editierten Schlüssel (für Verifikation b)."""
    entries = _parse_entries(text, bounds.body_start, bounds.close_line_start)
    pieces = []
    cursor = bounds.body_start
    for entry in entries:
        if entry.key in touched_keys:
            pieces.append(text[cursor : entry.start])
            cursor = entry.end
    pieces.append(text[cursor : bounds.close_line_start])
    return "".join(pieces)
