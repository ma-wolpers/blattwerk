"""Tests für die Umstellung früherer deutscher Blocknamen (`BL013`, Migrationswerkzeug)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.core.blatt_validator import inspect_markdown_text
from app.core.blatt_validator_constants import KNOWN_BLOCK_TYPES, REMOVED_BLOCK_NAMES

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "migrate_block_names.py"
_spec = importlib.util.spec_from_file_location("migrate_block_names", _TOOL)
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)

HEAD = "---\nTitel: T\nFach: M\nThema: X\n---\n"


def test_removed_names_are_unknown_and_replacements_exist():
    """Die Tabelle zeigt nur von entfernten auf vorhandene Blocknamen."""
    assert not set(REMOVED_BLOCK_NAMES) & KNOWN_BLOCK_TYPES
    assert set(REMOVED_BLOCK_NAMES.values()) <= KNOWN_BLOCK_TYPES


def test_removed_name_reports_error_with_replacement():
    """`:::hilfe` ist ein Fehler, der den neuen Namen nennt, nicht bloß „unbekannt“."""
    diagnostics = inspect_markdown_text(HEAD + ":::hilfe\nText\n:::\n", document_type="worksheet").diagnostics
    found = [d for d in diagnostics if d.code == "BL013"]
    assert len(found) == 1
    assert found[0].severity == "error"
    assert "`help`" in found[0].message
    assert not [d for d in diagnostics if d.code == "BL001"]


def test_rewrite_changes_only_headers_outside_fences():
    """Kopfzeilen werden ersetzt, Fließtext, Code-Zäune und Optionen bleiben."""
    text = (
        ':::hilfe title="Hilfe"\nDie hilfe hilft.\n:::\n'
        ":::struktogramm width=80%\nrückgabe x\n:::\n"
        ":::struktogramm:::\n"
        "```\n:::hilfe\n```\n"
    )
    updated, count = tool.rewrite_content(text)
    assert count == 3
    assert ':::help title="Hilfe"\nDie hilfe hilft.' in updated
    assert ":::structogram width=80%" in updated
    assert ":::structogram:::" in updated
    assert "```\n:::hilfe\n```" in updated


def test_rewrite_keeps_line_endings_and_other_names():
    """CRLF bleibt erhalten; `:::hilfetext` ist kein alter Blockname."""
    updated, count = tool.rewrite_content(":::hilfe\r\n:::\r\n:::hilfetext\r\n")
    assert count == 1
    assert updated == ":::help\r\n:::\r\n:::hilfetext\r\n"


def test_dry_run_writes_nothing_and_write_does(tmp_path):
    """Ohne `write` bleibt die Datei unverändert; andere Endungen werden nie angefasst."""
    document = tmp_path / "a.abw"
    other = tmp_path / "b.txt"
    document.write_text(":::hilfe\nT\n:::\n", encoding="utf-8")
    other.write_text(":::hilfe\n", encoding="utf-8")

    assert tool.migrate(tmp_path, write=False) == [(document, 1)]
    assert ":::hilfe" in document.read_text(encoding="utf-8")

    assert tool.migrate(tmp_path, write=True) == [(document, 1)]
    assert document.read_text(encoding="utf-8") == ":::help\nT\n:::\n"
    assert other.read_text(encoding="utf-8") == ":::hilfe\n"
