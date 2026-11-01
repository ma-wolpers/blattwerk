"""Die Beispieldateien je Kategorie zeigen jeden Block und bleiben fehlerfrei.

Ein neuer Block ohne Beispiel fällt hier auf: Die Zuordnung leitet sich aus den Menüfamilien
ab, die Dateinamen stehen einmal in `EXAMPLE_FILES`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks, split_front_matter
from app.core.blatt_validator import inspect_markdown_text
from app.core.blatt_validator_constants import KNOWN_BLOCK_TYPES
from app.core.block_insert_menu_families import BLOCK_INSERT_FAMILIES, BLOCK_INSERT_STANDALONE
from app.core.blatt_kern_shared_data import CONTROL_MARKERS

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "markdown"
EXAMPLE_FILES = {
    "Boxen/Hinweise": "example-kategorie-boxen.abw",
    "Aufgaben": "example-kategorie-aufgaben.abw",
    "Freies Antwortfeld": "example-kategorie-antwortfelder.abw",
    "Textbasierte Übungen": "example-kategorie-textuebungen.abw",
    "Grafische/räumliche Übungen": "example-kategorie-grafisch.abw",
    "Diagramme": "example-kategorie-diagramme.abw",
    "Offen/Reflexion": "example-kategorie-offen.abw",
}
LAYOUT_FILE = "example-kategorie-layout.abw"
LAYOUT_BLOCKS = {block for _label, block in BLOCK_INSERT_STANDALONE} | {"nextcol", "endcolumns"}
ALL_FILES = [*EXAMPLE_FILES.values(), LAYOUT_FILE]
INFORMATIONAL_CODES = {"MJ001", "AN005"}
"""Kein Mangel des Beispiels: `MJ001` weist auf Formeln im HTML-Export hin, `AN005` auf leere
Antwortfelder, und genau die zeigt die Antwortfeld-Datei."""


def _blocks(name: str) -> tuple[dict, list]:
    """Frontmatter und Blöcke einer Beispieldatei."""
    meta, body = split_front_matter((EXAMPLES / name).read_text(encoding="utf-8"))
    return meta, parse_blocks(body)


def _used_types(name: str) -> set[str]:
    """Blocktypen, die in einer Beispieldatei vorkommen."""
    return {block_type for block_type, _options, _content in _blocks(name)[1]}


def test_every_menu_family_has_an_example_file():
    """Jede Familie des Einfügemenüs ist einer Beispieldatei zugeordnet."""
    assert set(EXAMPLE_FILES) == {family for family, _entries in BLOCK_INSERT_FAMILIES}


@pytest.mark.parametrize(("family", "entries"), BLOCK_INSERT_FAMILIES)
def test_example_file_shows_all_blocks_of_its_family(family, entries):
    """Kein Block einer Familie fehlt in ihrer Datei."""
    expected = {block for _label, block in entries}
    assert not expected - _used_types(EXAMPLE_FILES[family])


def test_layout_file_shows_all_standalone_blocks():
    """Spalten und QR-Codes stehen in der Layout-Datei."""
    assert not LAYOUT_BLOCKS - _used_types(LAYOUT_FILE)


def test_all_known_blocks_appear_somewhere():
    """Alle `:::`-Blöcke außer den Trennmarkern kommen in einer Datei vor."""
    markers = {marker.block_type for marker in CONTROL_MARKERS}
    expected = KNOWN_BLOCK_TYPES - markers - {"raw"}
    used = set().union(*(_used_types(name) for name in ALL_FILES))
    assert not expected - used


@pytest.mark.parametrize("name", ALL_FILES)
def test_example_has_no_errors_or_warnings(name):
    """Die Beispiele sind Vorbilder: weder Fehler noch Warnungen."""
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    diagnostics = inspect_markdown_text(text, document_type="worksheet").diagnostics
    assert [(d.severity, d.code, d.message) for d in diagnostics if d.code not in INFORMATIONAL_CODES] == []


@pytest.mark.parametrize("name", ALL_FILES)
@pytest.mark.parametrize("include_solutions", [False, True])
def test_example_renders_in_both_versions(name, include_solutions):
    """Beide Fassungen rendern."""
    meta, blocks = _blocks(name)
    assert render_html(meta, blocks, include_solutions=include_solutions)


@pytest.mark.parametrize("name", ALL_FILES)
def test_example_shows_more_than_the_minimum(name):
    """Bandbreite: Es gibt mehr Blöcke als Blocktypen, jeder Typ darf mehrfach zeigen, was er kann."""
    _meta, blocks = _blocks(name)
    shown = [block_type for block_type, _options, _content in blocks if block_type not in {"raw", "task", "nextcol"}]
    assert len(shown) > len(set(shown))
