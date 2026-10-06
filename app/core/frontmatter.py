"""Frontmatter-Kern: die eine Grenzbestimmung und das YAML-Laden des Frontmatters.

Warum es dieses Modul gibt: Blattwerk hatte drei unabhängige Frontmatter-
Erkennungen (`split_front_matter` per `text.split("---", 2)`, die
Validator-Hilfe `_extract_validation_content_and_base_line` und
Ad-hoc-Code). Die `split`-Variante beendete das Frontmatter an *jedem*
`---` -- auch mitten in einer Zeile wie `Titel: a---b` -- und erkannte ein
Dokument mit UTF-8-BOM gar nicht. Migration, Quick-Fixes und Speichern-unter
brauchen exakte Byte-Grenzen (siehe `frontmatter_edit.py`), deshalb gibt es
genau eine zeilenbasierte Definition (Invariante I6 im Architektur-Doc):

* Erste Zeile (nach optionalem BOM) ist exakt `---` (abschließender
  Leerraum erlaubt).
* Das Frontmatter endet an der nächsten Zeile, die exakt `---` oder `...`
  ist (ebenfalls mit optionalem Leerraum).
* Zeilen werden nur an `\\n` getrennt; ein `\\r` davor gehört zum
  Zeilenende. So bleiben CRLF/LF/gemischte Zeilenenden byte-genau
  rekonstruierbar.

Der Kurzentwurf-DSL-Parser (`kurzentwurf_runtime/dsl_frontmatter.py`) ist
bewusst *nicht* hierher umgezogen: Er liest kein YAML, sondern tolerant
einzelne `key: value`-Zeilen (auch nach Leerzeilen), und eine Umstellung
würde bestehende Kurzentwürfe brechen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import yaml

BOM = "﻿"
_FENCE_OPEN = "---"
_FENCE_CLOSE = ("---", "...")


@dataclass(frozen=True)
class FrontmatterBounds:
    """Zeichen-Offsets eines erkannten Frontmatter-Blocks im Gesamttext.

    Attributes:
        has_bom: Ob der Text mit einem UTF-8-BOM-Zeichen (`\\ufeff`) beginnt.
        open_line_start: Offset der öffnenden `---`-Zeile (hinter dem BOM).
        body_start: Offset direkt hinter der öffnenden Zeile inkl. Zeilenende.
        close_line_start: Offset der schließenden `---`/`...`-Zeile.
        end: Offset direkt hinter der schließenden Zeile inkl. Zeilenende.
        open_line_ending: Zeilenende der öffnenden Zeile (`"\\r\\n"`, `"\\n"`
            oder `""`); dient Edit-Operationen als Stilvorlage für neue Zeilen.
        start_line: 1-basierte Zeilennummer der öffnenden Zeile (immer 1).
        content_start_line: 1-basierte Zeilennummer der ersten Zeile nach
            dem Frontmatter.
    """

    has_bom: bool
    open_line_start: int
    body_start: int
    close_line_start: int
    end: int
    open_line_ending: str
    content_start_line: int
    start_line: int = 1

    def body(self, text: str) -> str:
        """Liefert den YAML-Rumpf zwischen öffnender und schließender Zeile."""
        return text[self.body_start : self.close_line_start]


def split_line_ending(line: str) -> tuple[str, str]:
    """Trennt eine Zeile in Inhalt und Zeilenende (`"\\r\\n"`, `"\\n"` oder `""`)."""
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def iter_lines_with_offsets(text: str, start: int = 0) -> Iterator[tuple[int, str]]:
    """Iteriert `(offset, zeile_inkl_zeilenende)` ab `start`, getrennt nur an `\\n`.

    Bewusst nicht `str.splitlines()`: das trennt auch an `\\x0b`, `\\x0c`,
    `\\u2028` usw. und würde Offsets für byte-genaue Edits verfälschen.
    """
    position = start
    length = len(text)
    while position < length:
        newline = text.find("\n", position)
        end = length if newline == -1 else newline + 1
        yield position, text[position:end]
        position = end


def frontmatter_bounds(text: str) -> FrontmatterBounds | None:
    """Bestimmt die Frontmatter-Grenzen nach der einen zeilenbasierten Regel.

    Args:
        text: Vollständiger Dokumenttext (ein BOM-Zeichen am Anfang ist erlaubt).

    Returns:
        Die Grenzen, oder ``None``, wenn das Dokument nicht mit einer
        `---`-Zeile beginnt oder kein Schluss (`---`/`...`) folgt.
    """
    source = text or ""
    has_bom = source.startswith(BOM)
    open_start = 1 if has_bom else 0
    lines = iter_lines_with_offsets(source, open_start)
    first = next(lines, None)
    if first is None:
        return None
    first_offset, first_line = first
    first_content, first_ending = split_line_ending(first_line)
    if first_content.rstrip() != _FENCE_OPEN or not first_ending:
        return None
    body_start = first_offset + len(first_line)
    line_number = 1
    for offset, line in lines:
        line_number += 1
        content, _ending = split_line_ending(line)
        if content.rstrip() in _FENCE_CLOSE:
            return FrontmatterBounds(
                has_bom=has_bom,
                open_line_start=first_offset,
                body_start=body_start,
                close_line_start=offset,
                end=offset + len(line),
                open_line_ending=first_ending,
                content_start_line=line_number + 1,
            )
    return None


class DuplicateKeyError(yaml.YAMLError):
    """Ein Mapping im Frontmatter enthält denselben Schlüssel mehrfach."""


class _DuplicateRejectingLoader(yaml.SafeLoader):
    """`SafeLoader`, der doppelte Mapping-Schlüssel auf jeder Ebene ablehnt.

    `yaml.safe_load` übernimmt bei Duplikaten stillschweigend den letzten
    Wert; für Edits und die Migration ist das nicht ausreichend, weil ein
    Edit sonst den "falschen" der beiden Einträge ändern könnte.
    """


def _construct_mapping_rejecting_duplicates(loader, node, deep=False):
    """Konstruiert ein Mapping und wirft `DuplicateKeyError` bei doppelten Schlüsseln."""
    loader.flatten_mapping(node)
    seen = set()
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in seen
        except TypeError:
            continue  # unhashbarer Schlüssel: construct_mapping meldet das selbst
        if duplicate:
            raise DuplicateKeyError(f"Doppelter Frontmatter-Schlüssel: {key!r}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_DuplicateRejectingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_rejecting_duplicates,
)


def load_frontmatter_yaml(body: str, *, reject_duplicates: bool = False):
    """Lädt einen Frontmatter-Rumpf als YAML.

    Args:
        body: Text zwischen den `---`-Zeilen.
        reject_duplicates: ``True`` für Edit-/Migrationspfade (doppelte
            Schlüssel → `DuplicateKeyError`), ``False`` für die normale
            Laufzeit, die wie bisher den letzten Wert übernimmt.

    Returns:
        Das geladene Objekt (``None`` bei leerem Rumpf).

    Raises:
        yaml.YAMLError: Bei ungültigem YAML (bzw. Duplikaten, s. o.).
    """
    if reject_duplicates:
        return yaml.load(body, Loader=_DuplicateRejectingLoader)  # noqa: S506 - SafeLoader-Subklasse
    return yaml.safe_load(body)


def parse_frontmatter(text: str):
    """Liest Frontmatter und Resttext; Ersatz für das alte `split_front_matter`.

    Semantik wie bisher, nur mit korrekter Grenzbestimmung: Metadaten sind
    das geladene YAML (``{}`` bei leerem Rumpf), der Rest wird ge-`strip()`t.
    Ohne erkennbares Frontmatter: ``({}, text)``.
    """
    source = text or ""
    bounds = frontmatter_bounds(source)
    if bounds is None:
        return {}, source
    meta = load_frontmatter_yaml(bounds.body(source)) or {}
    return meta, source[bounds.end :].strip()


def content_after_frontmatter(text: str) -> tuple[str, int]:
    """Liefert den Text hinter dem Frontmatter und dessen 1-basierte Startzeile.

    Ohne Frontmatter ist das der ganze Text ab Zeile 1. Wird vom Validator
    für zeilengenaue Diagnosen im Originaldokument gebraucht.
    """
    source = text or ""
    bounds = frontmatter_bounds(source)
    if bounds is None:
        return source, 1
    return source[bounds.end :], bounds.content_start_line
