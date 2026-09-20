"""Tests für `app/core/block_insert_snippets.py` -- die einzige Quelle der Vorlagen
des Editor-Menüs "Einfügen".

Ein Snippet ist ein minimales, bequemes Beispiel (kein vollständige
Grammatikspezifikation) -- diese Tests beweisen deshalb nur zwei konkrete
Eigenschaften: (1) jedes Snippet ist syntaktisch gültiges Blattwerk-Markdown,
und (2) der Editor und der Doku-Generator können nicht auseinanderlaufen,
weil beide aus derselben Quelle lesen.

Die Menü-Familien-Zuordnung selbst (`BLOCK_INSERT_FAMILIES`/
`BLOCK_INSERT_STANDALONE`) wird in `test_block_insert_menu.py` geprüft --
dort ebenfalls gegen `BLOCK_INSERT_SNIPPETS` als Quelle der Wahrheit.
"""

from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.core.blatt_validator import inspect_markdown_text
from app.core.markdown_conventions import collect_markdown_conventions


def test_every_block_insert_snippet_is_valid_markdown():
    """Beweist nur syntaktische Gültigkeit -- nicht, dass das Snippet das in der
    Prosa behauptete Verhalten tatsächlich demonstriert.

    Prüft auf `error`-freie Diagnosen, nicht auf komplett leere Diagnoseliste:
    einige Antwortfeld-Blöcke (`dots`/`grid`/`lines`/`space`) sind im
    Einfüge-Template bewusst inhaltsleer (sie werden von Schüler:innen
    ausgefüllt, nicht von Autor:innen vorbefüllt) und lösen dafür berechtigterweise
    die nicht-blockierende Best-Practice-Warnung `AN005` aus -- das ist kein
    Snippet-Fehler.

    `OP002` (ungültiger Options-Wert) ist zusätzlich explizit verboten, obwohl
    es nur `severity="warning"` ist: ein Snippet mit ungültigem Options-Wert
    (z. B. ein nicht existierender `type=`) ist immer ein Snippet-Fehler, nie
    eine akzeptable Best-Practice-Warnung wie `AN005`.
    """
    for block_type, snippet in BLOCK_INSERT_SNIPPETS.items():
        cleaned = snippet.replace("\x01", "")
        document = "---\nTitel: T\nFach: M\nThema: X\n---\n" + cleaned + "\n"
        diagnostics = inspect_markdown_text(document).diagnostics
        error_diagnostics = [d for d in diagnostics if d.severity == "error"]
        assert error_diagnostics == [], f"Snippet für {block_type!r} validiert nicht sauber: {error_diagnostics}"
        op002_diagnostics = [d for d in diagnostics if d.code == "OP002"]
        assert op002_diagnostics == [], f"Snippet für {block_type!r} enthält ungültigen Options-Wert: {op002_diagnostics}"


def test_catalog_block_spec_insert_snippet_matches_source_dict():
    catalog = collect_markdown_conventions()
    for block in catalog.blocks:
        expected = BLOCK_INSERT_SNIPPETS.get(block.name)
        assert block.insert_snippet == expected
