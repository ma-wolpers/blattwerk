"""Tests für `app/core/block_insert_snippets.py` -- die einzige Quelle der Ctrl+B-Vorlagen.

Ein Snippet ist ein minimales, bequemes Beispiel (kein vollständige
Grammatikspezifikation) -- diese Tests beweisen deshalb nur zwei konkrete
Eigenschaften: (1) jedes Snippet ist syntaktisch gültiges Blattwerk-Markdown,
und (2) der Editor und der Doku-Generator können nicht auseinanderlaufen,
weil beide aus derselben Quelle lesen.
"""

from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.core.blatt_validator import inspect_markdown_text
from app.core.markdown_conventions import collect_markdown_conventions
from app.ui.blatt_ui_editor import _EDITOR_BLOCK_MENU_ITEMS

_LABEL_TO_BLOCK_TYPE = {
    "Auswahlaufgabe (mc)": "mc",
    "Tabelle (table)": "table",
    "Spalten-Layout (columns)": "columns",
    "Punktpapier (dots)": "dots",
    "Koordinatensystem (geometry)": "geometry",
    "Infobox / Hinweis (info)": "info",
    "Gitterpapier (grid)": "grid",
    "Hilfe-Karte (help)": "help",
    "Lückentext (cloze)": "cloze",
    "Linienfeld (lines)": "lines",
    "Material": "material",
    "Zahlengerade (numberline)": "numberline",
    "Freier Platz (space)": "space",
    "QR-Code": "qrcode",
    "Musterlösung (solution)": "solution",
    "Teilaufgabe (subtask)": "subtask",
    "Aufgabe (task)": "task",
    "Wortsuchrätsel (wordsearch)": "wordsearch",
    "Kreuzworträtsel (crossword)": "crossword",
    "Zuordnung (matching)": "matching",
}
_NON_BLOCK_MENU_LABELS = {"Bild (image)"}


def test_editor_menu_and_snippet_catalog_cover_the_same_block_types():
    """Verhindert, dass ein neuer Ctrl+B-Eintrag vergisst, seine Vorlage in
    BLOCK_INSERT_SNIPPETS einzutragen (und damit in der Doku stillschweigend
    ohne Beispiel bleibt) -- oder umgekehrt."""
    menu_labels = {label for _letter, label, _template in _EDITOR_BLOCK_MENU_ITEMS}
    menu_block_types = {
        _LABEL_TO_BLOCK_TYPE[label] for label in menu_labels if label not in _NON_BLOCK_MENU_LABELS
    }
    unmapped_labels = menu_labels - _NON_BLOCK_MENU_LABELS - set(_LABEL_TO_BLOCK_TYPE)
    assert not unmapped_labels, f"Neuer Ctrl+B-Eintrag ohne Block-Typ-Zuordnung im Test: {unmapped_labels}"
    assert menu_block_types == set(BLOCK_INSERT_SNIPPETS)


def test_editor_menu_templates_are_sourced_from_block_insert_snippets():
    for _letter, label, template in _EDITOR_BLOCK_MENU_ITEMS:
        if label in _NON_BLOCK_MENU_LABELS:
            continue
        block_type = _LABEL_TO_BLOCK_TYPE[label]
        assert template == BLOCK_INSERT_SNIPPETS[block_type]


def test_every_block_insert_snippet_is_valid_markdown():
    """Beweist nur syntaktische Gültigkeit -- nicht, dass das Snippet das in der
    Prosa behauptete Verhalten tatsächlich demonstriert.

    Prüft auf `error`-freie Diagnosen, nicht auf komplett leere Diagnoseliste:
    einige Antwortfeld-Blöcke (`dots`/`grid`/`lines`/`space`) sind im Ctrl+B-
    Template bewusst inhaltsleer (sie werden von Schüler:innen ausgefüllt,
    nicht von Autor:innen vorbefüllt) und lösen dafür berechtigterweise die
    nicht-blockierende Best-Practice-Warnung `AN005` aus -- das ist kein
    Snippet-Fehler.
    """
    for block_type, snippet in BLOCK_INSERT_SNIPPETS.items():
        cleaned = snippet.replace("\x01", "")
        document = "---\nTitel: T\nFach: M\nThema: X\n---\n" + cleaned + "\n"
        diagnostics = inspect_markdown_text(document).diagnostics
        error_diagnostics = [d for d in diagnostics if d.severity == "error"]
        assert error_diagnostics == [], f"Snippet für {block_type!r} validiert nicht sauber: {error_diagnostics}"


def test_catalog_block_spec_insert_snippet_matches_source_dict():
    catalog = collect_markdown_conventions()
    for block in catalog.blocks:
        expected = BLOCK_INSERT_SNIPPETS.get(block.name)
        assert block.insert_snippet == expected
