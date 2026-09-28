"""Tests für Zeilenumbrüche/Absätze und `$...$`-Formeln in Kurzentwurf-Zellen.

End-to-end über `render_html_from_source` bzw. `inspect_kurzentwerfer_text`,
damit Parser (`dsl_segments`), Label-Logik (`cell_text`) und Renderer
(`render_html`) gemeinsam geprüft werden.
"""

import re

from app.core.diagnostic_identity import compute_diagnostic_identity
from app.core.kurzentwurf_runtime.build import render_html_from_source
from app.core.kurzentwurf_runtime.cell_text import label_block, label_entries, strip_hard_break
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


def test_blank_line_inside_cell_starts_new_paragraph():
    html, _ = render_html_from_source(_document("S> eins\n\nzwei\nA>\ns< a\nant< b\nU> u"))
    assert _cell(html, "schritte-cell") == (
        '<p class="cell-paragraph">eins</p><p class="cell-paragraph">zwei</p>'
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


def test_ant_block_keeps_blank_line_as_paragraph_boundary():
    assert label_block("a\n\n\nb", "Ant:") == "**Ant:**\na\n\nb"
    assert label_block("a", "Ant:") == "**Ant:** a"


def test_inline_math_loads_mathjax_without_display_math():
    html, inspection = render_html_from_source(_document("S> $x^2$\nA>\ns< a\nant< b\nU> u"))
    assert "mathjax@4/tex-svg.js" in html
    assert "inlineMath: [['$', '$']]" in html
    assert "displayMath: []" in html
    assert "$x^2$" in _cell(html, "schritte-cell")
    assert [d.code for d in inspection.diagnostics] == ["KZF160"]


def test_math_notice_only_once_per_document():
    result = inspect_kurzentwerfer_text(_document("S> $a$\n$b$\nA>\ns< $c$\nant< d\nU> u"))
    notices = [d for d in result.diagnostics if d.code == "KZF160"]
    assert len(notices) == 1
    assert notices[0].line == 7
    compute_diagnostic_identity(notices[0])  # ackbar: region_id gesetzt


def test_display_math_warns_kzf161():
    result = inspect_kurzentwerfer_text(_document("S> $$x$$\nA>\ns< a\nant< b\nU> u"))
    display = [d for d in result.diagnostics if d.code == "KZF161"]
    assert len(display) == 1
    assert display[0].anchor == "$$x$$"
    assert "KZF160" not in [d.code for d in result.diagnostics]
    compute_diagnostic_identity(display[0])


def test_currency_dollar_is_not_math():
    result = inspect_kurzentwerfer_text(_document("S> kostet $5 und $10\nA>\ns< a\nant< b\nU> u"))
    assert not [d for d in result.diagnostics if d.code in {"KZF160", "KZF161"}]
