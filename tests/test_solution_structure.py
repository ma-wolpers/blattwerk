"""Lösungsblöcke: bewertete Punkte == gerenderte oberste Listenpunkte (Reihenfolge und Text).

Bewertung (`solution_items`) und Darstellung (`solution_display`) nutzen beide
`solution_structure.classify_solution`. Dieser Test vergleicht für Grenzfälle
die Folge der klassifizierten Kopfzeilen mit der Folge der `<li>` in den
obersten `<ol>` des tatsächlich gerenderten HTML -- nicht nur die Anzahl.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest

from app.core.blatt_kern_task_render import render_block
from app.core.solution_items import parse_solution_items
from app.core.solution_structure import classify_solution


class _TopLevelItems(HTMLParser):
    """Sammelt die erste Textzeile jedes `<li>` direkt unter einer obersten `<ol>`."""

    def __init__(self):
        """Leerer Zustand: Element-Stapel, gesammelte Punkte, aktueller Punkt."""
        super().__init__()
        self.stack, self.items, self.current = [], [], None

    def _lists(self):
        """Offene Listen-Elemente (ol/ul) von außen nach innen."""
        return [tag for tag in self.stack if tag in ("ol", "ul")]

    def handle_starttag(self, tag, attrs):
        """Beginnt einen obersten Punkt oder beendet dessen erste Zeile (Unterliste, Absatz, Umbruch)."""
        if tag == "li" and self._lists() == ["ol"]:
            self.current = {"text": "", "stop": False}
            self.items.append(self.current)
        elif self.current is not None and tag in ("ul", "ol", "p", "br", "pre") and self.current["text"].strip():
            self.current["stop"] = True
        if tag != "br":
            self.stack.append(tag)

    def handle_endtag(self, tag):
        """Schließt Elemente; ein schließendes oberstes `li` beendet den Punkt."""
        if tag == "br":  # leeres Element: HTMLParser meldet `<br />` auch als End-Tag
            return
        while self.stack:
            if self.stack.pop() == tag:
                break
        if tag == "li" and self._lists() == ["ol"]:
            self.current = None

    def handle_data(self, data):
        """Text gehört zum aktuellen Punkt, solange dessen erste Zeile läuft."""
        if self.current is not None and not self.current["stop"]:
            self.current["text"] += data


def _rendered_heads(content):
    """Erste Zeile jedes obersten Listenpunkts im gerenderten Lösungsblock."""
    parser = _TopLevelItems()
    parser.feed(render_block("solution", {}, content, include_solutions=True, document_type="exam"))
    return [re.sub(r"\s+", " ", item["text"]).strip() for item in parser.items]


def _classified_heads(content):
    """Sichtbare Kopfzeilen der klassifizierten Punkte (Leerraum vereinheitlicht)."""
    return [re.sub(r"\s+", " ", entry.visible_lines()[0]).strip() for entry in classify_solution(content).entries]


CASES = {
    "unterliste_2_leer": ("1. A (1P)\n  - x (1P)\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "unterliste_4_leer": ("1. A (1P)\n    - x\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "locker": ("1. A (1P)\n\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "fortsetzung_eingerueckt": ("1. Anfang\n   weiter (1P)\n2. Zwei (1P)", ["Anfang", "Zwei (1P)"]),
    "lazy_continuation": ("1. Anfang\nweiter (1P)\n2. Zwei (1P)", ["Anfang", "Zwei (1P)"]),
    "absatz_nach_leerzeile": ("1. A (1P)\n\nSchluss", ["A (1P)"]),
    "fortsetzung_nach_leerzeile": ("1. A (1P)\n\n    Fortsetzung\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "absatz_davor": ("Hinweis\n1. Punkt (1P)", ["Punkt (1P)"]),
    "zwischentext": ("1. A (1P)\n\nZwischentext\n\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "codezaun": ("```\n1. Code (2P)\n```\n1. echt (1P)", ["echt (1P)"]),
    "kommentar_einzeilig": ("1. A (1P)\n%% 9. weg (5P) %%\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "kommentar_mehrzeilig": ("1. A (1P)\n%% 2. weg (5P)\n3. auch weg (5P) %%\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "kommentar_zeilenende": ("1. A (1P) %%Notiz%%\n2. B (1P)", ["A (1P)", "B (1P)"]),
    "mathe_mehrzeilig": ("$$\n1. x (2P)\n$$\n1. y (1P)", ["y (1P)"]),
    "klammer_marker": ("1) Punkt (1P)\n2) Zwei (1P)", []),
    "ohne_leerzeichen": ("1.A (1P)\n2. B (1P)", ["B (1P)"]),
    "zweistellig": ("10. A (1P)\n11. B (1P)", ["A (1P)", "B (1P)"]),
    "drei_leerzeichen": ("   1. A (1P)\n   2. B (1P)", ["A (1P)", "B (1P)"]),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_classified_items_equal_rendered_top_level_items(name):
    """Reihenfolge und Kopftext der bewerteten Punkte entsprechen exakt der gerenderten Liste."""
    content, expected = CASES[name]
    assert _classified_heads(content) == expected
    assert _rendered_heads(content) == expected


def test_protected_content_is_neither_scored_nor_listed():
    """Zaun-, Kommentar- und Formelinhalt erzeugt keine Punkte und keine Listenpunkte."""
    for content in (CASES["codezaun"][0], CASES["kommentar_mehrzeilig"][0], CASES["mathe_mehrzeilig"][0]):
        items, _misplaced = parse_solution_items(content)
        assert all("weg" not in item.text and "Code" not in item.text for item in items)
    html = render_block("solution", {}, CASES["codezaun"][0], include_solutions=True, document_type="exam")
    assert "<pre><code>" in html and "1. Code (2P)" in html
    assert "weg" not in render_block("solution", {}, CASES["kommentar_mehrzeilig"][0], include_solutions=True)


def test_suffix_before_trailing_comment_counts_and_comment_text_is_not_item_text():
    """`(1P) %%Notiz%%` zählt wie dargestellt; Kommentartext landet nicht im Erwartungstext."""
    items, _misplaced = parse_solution_items(CASES["kommentar_zeilenende"][0])
    assert [(item.text, str(item.points)) for item in items] == [("A", "1"), ("B", "1")]


def test_suffix_in_continuation_line_is_not_scored():
    """Nur die Kopfzeile trägt Punkte; eine Fortsetzung mit `(1P)` bleibt Text (unverändert sichtbar)."""
    items, _misplaced = parse_solution_items(CASES["fortsetzung_eingerueckt"][0])
    assert items[0].points is None and items[0].text == "Anfang weiter (1P)"


@pytest.mark.parametrize("content", ["1. A (1P)\n    - Detail (1P)\n", "1) x (1P)", "- y (1P)"])
def test_points_on_list_lines_that_are_no_item_head_are_misplaced(content):
    """SL004-Grundlage: Suffix an Unter-, Aufzählungs- oder `1)`-Zeilen zählt nicht."""
    assert parse_solution_items(content)[1] is True


def test_loose_group_keeps_paragraphs_tight_group_unwraps():
    """Wie bei Markdown: lockere Liste mit `<p>`, dichte Liste ohne."""
    loose = render_block("solution", {}, CASES["locker"][0], include_solutions=True)
    tight = render_block("solution", {}, "1. A (1P)\n2. B (1P)", include_solutions=True)
    assert "<li><p>A (1P)</p></li>" in loose and "<li>A (1P)</li>" in tight
