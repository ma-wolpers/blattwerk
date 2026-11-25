"""Tests für Zeilenumbrüche/Absätze und `$...$`-Formeln in Kurzentwurf-Zellen.

End-to-end über `render_html_from_source` bzw. `inspect_kurzentwerfer_text`,
damit Parser (`dsl_segments`), Label-Logik (`cell_text`), Zellen-HTML
(`cell_html`, `activity_cell`) und Renderer (`render_html`) gemeinsam
geprüft werden.
"""

import re

from app.core.diagnostic_identity import compute_diagnostic_identity
from app.core.kurzentwurf_runtime.build import render_html_from_source
from app.core.kurzentwurf_runtime.activity_cell import Utterance, line_has_quotes, split_utterance
from app.core.kurzentwurf_runtime.cell_text import label_entries, strip_hard_break
from app.core.kurzentwurf_runtime.validator import inspect_kurzentwerfer_text


def _document(body: str) -> str:
    return "---\nStundenthema: T\nLerngruppe: X\nstart: 08:00\n---\n#einstieg t=10\n" + body + "\n"


def _cell(html: str, css_class: str) -> str:
    match = re.search(rf'class="[^"]*{css_class}[^"]*"[^>]*><div class="cell-content">(.*?)</div></td>', html)
    assert match, f"Zelle {css_class} nicht gefunden"
    return match.group(1)


def test_single_line_break_renders_br_within_one_paragraph():
    html, _ = render_html_from_source(_document("S> eins\nzwei\nA>\ns< a\nant< b\nU> u"))
    assert _cell(html, "schritte-cell") == '<p class="cell-paragraph">eins<br>zwei</p>'


def test_blank_line_inside_cell_starts_new_paragraph_with_visible_gap():
    html, _ = render_html_from_source(_document("S> eins\n\nzwei\nA>\ns< a\nant< b\nU> u"))
    assert _cell(html, "schritte-cell") == (
        '<p class="cell-paragraph">eins</p><p class="cell-paragraph cell-gap">zwei</p>'
    )
    assert ".cell-gap {" in html


def test_list_after_paragraph_without_blank_line_gets_no_gap():
    html, _ = render_html_from_source(_document("S> eins\n- zwei\n\n- drei\nA>\ns< a\nant< b\nU> u"))
    assert _cell(html, "schritte-cell") == (
        '<p class="cell-paragraph">eins</p><ul class="cell-list"><li>zwei</li></ul>'
        '<ul class="cell-list cell-gap"><li>drei</li></ul>'
    )


def test_blank_line_before_next_marker_adds_no_empty_paragraph():
    html, _ = render_html_from_source(_document("S> eins\n\nA>\n\ns< a\n\nant< b\n\nU> u\n"))
    assert _cell(html, "schritte-cell") == '<p class="cell-paragraph">eins</p>'
    assert _cell(html, "umgebung-cell") == '<p class="cell-paragraph">u</p>'


def test_s_marker_lines_stay_separate_entries_without_backslash():
    assert label_entries("a\nb", "S:innen") == "**S:innen** a\n**S:innen** b"


def test_trailing_backslash_continues_same_s_entry():
    html, _ = render_html_from_source(_document("S> x\nA>\ns< a \\\nweiter\nneu\nant< b\nU> u"))
    cell = _cell(html, "aktivitaeten-cell")
    assert "<strong>S:innen</strong> a<br>weiter<br><strong>S:innen</strong> neu" in cell
    assert "\\" not in cell


def test_trailing_backslash_is_removed_in_other_columns():
    html, _ = render_html_from_source(_document("S> eins \\\nzwei\nA>\ns< a\nant< b\nU> u"))
    assert _cell(html, "schritte-cell") == '<p class="cell-paragraph">eins<br>zwei</p>'


def test_double_backslash_is_not_a_hard_break():
    assert strip_hard_break("a \\\\") == "a \\\\"
    assert strip_hard_break("a \\") == "a"


def test_each_anticipation_stays_below_its_own_s_entry():
    html, _ = render_html_from_source(
        _document("S> x\nA>\ns< eins\nant< - a1\n      - a2\ns< zwei\nant< b\nU> LSG")
    )
    cell = _cell(html, "aktivitaeten-cell")
    order = [cell.index(text) for text in ("eins", "„a1“", "„a2“", "zwei", "„b“")]
    assert order == sorted(order), cell
    assert cell.count("<strong>Antizipiert:</strong>") == 2


def test_anticipation_gets_quotes_and_grey_trailing_note():
    html, inspection = render_html_from_source(
        _document("S> x\nA>\ns< a\nant< - Das sind Zehntel. (Fehlvorstellung)\n      - Hundertstel\nU> LSG")
    )
    cell = _cell(html, "aktivitaeten-cell")
    assert (
        '<p class="cell-paragraph"><strong>Antizipiert:</strong></p><ul class="cell-list">'
        '<li>„Das sind Zehntel.“ <span class="ant-note">(Fehlvorstellung)</span></li>'
        "<li>„Hundertstel“</li></ul>"
    ) in cell
    assert ".ant-note {" in html
    assert not [d for d in inspection.diagnostics if d.code == "KZF155"]


def test_single_anticipation_stands_next_to_its_label():
    html, _ = render_html_from_source(_document("S> x\nA>\ns< a\nant< Weiß ich nicht.\nU> LSG"))
    assert '<p class="cell-paragraph"><strong>Antizipiert:</strong> „Weiß ich nicht.“</p>' in _cell(
        html, "aktivitaeten-cell"
    )


def test_quoted_anticipations_warn_once_per_block_and_render_without_own_quotes():
    source = _document(
        "S> x\nA>\ns< a\nant< - „Eins.\" (x)\n      - \"Zwei.\"\ns< b\nant< 'Drei'\nU> LSG"
    )
    html, inspection = render_html_from_source(source)
    cell = _cell(html, "aktivitaeten-cell")
    assert '„Eins.“ <span class="ant-note">(x)</span>' in cell
    assert "„Zwei.“" in cell and "„Drei“" in cell
    warnings = [d for d in inspection.diagnostics if d.code == "KZF155"]
    assert [d.line for d in warnings] == [10, 13]
    compute_diagnostic_identity(warnings[0])  # abhakbar: region_id gesetzt


def test_apostrophe_at_end_is_not_a_quote():
    assert not line_has_quotes("- Das ist Moritz'")
    assert split_utterance("„Hallo“ (gut)") == Utterance("Hallo", "(gut)", True)


def test_segment_with_only_anticipation_still_inherits_previous_s_entry():
    html, _ = render_html_from_source(_document("S> x\nA>\ns< eins\nant< a\nU> LSG\n---\nA>\nant< b"))
    cells = re.findall(r'aktivitaeten-cell[^"]*"[^>]*><div class="cell-content">(.*?)</div></td>', html)
    assert len(cells) == 2
    assert "eins" in cells[1] and "„b“" in cells[1] and "„a“" not in cells[1]


def test_inline_math_loads_mathjax_without_display_math():
    html, inspection = render_html_from_source(_document("S> $x^2$\nA>\ns< a\nant< b\nU> u"))
    assert "/tex-svg.js" in html
    assert "displayMath: []" in html
    assert "$x^2$" in _cell(html, "schritte-cell")
    assert [d.code for d in inspection.diagnostics] == ["KZF160"]


def test_math_notice_only_once_per_document():
    result = inspect_kurzentwerfer_text(_document("S> $a$\n$b$\nA>\ns< $c$\nant< d\nU> u"))
    notices = [d for d in result.diagnostics if d.code == "KZF160"]
    assert len(notices) == 1
    assert notices[0].line == 7
    compute_diagnostic_identity(notices[0])  # ackbar: region_id gesetzt


def test_double_dollar_math_is_inline_math():
    html, inspection = render_html_from_source(_document("S> $$x$$\nA>\ns< a\nant< b\nU> u"))
    assert "inlineMath: [['$$', '$$'], ['$', '$']]" in html
    assert "$$x$$" in _cell(html, "schritte-cell")
    assert [d.code for d in inspection.diagnostics] == ["KZF161", "KZF160"]
    hint = inspection.diagnostics[0]
    assert hint.anchor == "$$x$$"
    compute_diagnostic_identity(hint)  # ackbar: region_id gesetzt


def test_currency_dollar_is_not_math():
    result = inspect_kurzentwerfer_text(_document("S> kostet $5 und $10\nA>\ns< a\nant< b\nU> u"))
    assert not [d for d in result.diagnostics if d.code == "KZF160"]


def test_long_words_wrap_inside_narrow_cells_instead_of_being_clipped():
    """Regression: bei `table-layout: fixed` ragten lange Wörter (z. B. "Variationsprogression")
    in der schmalen Lernumgebung-Spalte über den Zellrand und wurden in Vorschau/PDF
    abgeschnitten. Zellen trennen jetzt deutsch (`hyphens: auto`) und brechen notfalls
    mitten im Wort um (`overflow-wrap: anywhere`, falls kein Trennwörterbuch vorhanden ist)."""
    html, _ = render_html_from_source(_document("S> x\nA>\ns< a\nant< b\nU> Tafelbild Variationsprogression"))
    cell_rule = re.search(r"table\.kurzentwurf th,\s*table\.kurzentwurf td \{\{?([^}]*)\}", html)
    assert cell_rule, "Zellen-CSS-Regel nicht gefunden"
    assert "hyphens: auto" in cell_rule.group(1)
    assert "overflow-wrap: anywhere" in cell_rule.group(1)
    assert 'lang="de"' in html
    assert "Lern&shy;umgebung" in html
