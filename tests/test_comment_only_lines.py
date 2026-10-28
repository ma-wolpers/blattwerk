"""Reine Kommentarzeilen (`%%…%%` allein in einer Zeile) zählen gar nicht.

Weder als Leerzeile (Absatzgrenze im Arbeitsblatt) noch als leere Zeile
(`<br>` bzw. leerer „S:innen“-Eintrag im Kurzentwurf). Einzige Regel:
`inline_markup.spans.drop_comment_only_lines`.
"""

from __future__ import annotations

import re

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.inline_markup.spans import drop_comment_only_lines, strip_comments
from app.core.kurzentwurf_runtime.build import render_html_from_source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("eins\n%%notiz%%\nzwei", "eins\nzwei"),
        ("eins\n   %%notiz%%  \nzwei", "eins\nzwei"),
        ("eins\n%%a%% %%b%%\nzwei", "eins\nzwei"),
        ("eins\n%%mehr\nzeilig%%\nzwei", "eins\nzwei"),
        ("eins\n%%notiz%%", "eins\n"),
        ("eins %%mitten%% drei\nzwei", "eins %%mitten%% drei\nzwei"),
        ("eins\n%%a%% Text %%b%%\nzwei", "eins\n%%a%% Text %%b%%\nzwei"),
        ("eins\n\\%%kein Kommentar%%\nzwei", "eins\n\\%%kein Kommentar%%\nzwei"),
        ("ohne Kommentar", "ohne Kommentar"),
    ],
)
def test_drop_comment_only_lines(source, expected):
    assert drop_comment_only_lines(source) == expected


def test_strip_comments_removes_comment_lines_with_their_line_break():
    text, diagnostics = strip_comments("eins\n%%notiz%%\nzwei %%x%% drei")

    assert text == "eins\nzwei  drei"
    assert diagnostics == []


def test_worksheet_comment_line_does_not_split_the_paragraph():
    html = render_html({"Titel": "T", "Fach": "M", "Thema": "X"}, [("info", {}, "Zeile eins\n%%notiz%%\nZeile zwei")])

    between = re.search(r"Zeile eins(.*?)Zeile zwei", html, re.S).group(1)
    assert "</p>" not in between


def _kurzentwurf_cell(body, css_class):
    source = "---\nStundenthema: T\nLerngruppe: X\nstart: 08:00\n---\n#einstieg t=10\n" + body + "\n"
    html, _ = render_html_from_source(source)
    return re.search(rf'class="[^"]*{css_class}[^"]*"[^>]*><div class="cell-content">(.*?)</div></td>', html).group(1)


def test_kurzentwurf_comment_line_leaves_no_empty_line():
    cell = _kurzentwurf_cell("S> eins\n%%notiz%%\nzwei\nA>\ns< a\nant< b\nU> u", "schritte-cell")

    assert cell == '<p class="cell-paragraph">eins<br>zwei</p>'


def test_kurzentwurf_comment_line_is_no_empty_activity_entry():
    cell = _kurzentwurf_cell("S> x\nA>\ns< a\n%%notiz%%\ns< b\nant< c\nU> u", "aktivitaeten-cell")

    assert "<strong>S:innen</strong> a<br><strong>S:innen</strong> b" in cell


def test_kurzentwurf_multi_line_comment_disappears():
    cell = _kurzentwurf_cell("S> eins\n%%a\nb%%\nzwei\nA>\ns< a\nant< b\nU> u", "schritte-cell")

    assert cell == '<p class="cell-paragraph">eins<br>zwei</p>'
