"""Operatorentabelle als Block `:::operators:::` (Bereiche, Sichtbarkeit, Messmarken, OPR004–OPR008)."""

from __future__ import annotations

import re
from pathlib import Path

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_text
from app.core.block_insert_menu_families import BLOCK_INSERT_FAMILIES
from app.core.block_insert_snippets import BLOCK_INSERT_SNIPPETS
from app.core.operator_legend import MatchedOperator, render_operator_legend_html
from app.core.operator_legend_blocks import legend_probe_uri, operator_block_coverages

META = {"Titel": "T", "Fach": "Informatik"}
HEAD = "---\ndocument_type: {dt}\nTitel: T\nFach: Informatik\nThema: X\n---\n"
TASK_A = ":::task points=2 afb=1\n!!Nenne!! zwei Beispiele.\n:::\n"
TASK_B = ":::task points=3 afb=2\n!!Beschreibe!! den Ablauf.\n:::\n"
TASK_PLAIN = ":::task points=1 afb=1\nOhne Operator.\n:::\n"
OPS = ":::operators:::\n"


def _html(body, document_type="exam", include_solutions=False):
    html = render_html(META, parse_blocks(body), include_solutions=include_solutions, document_type=document_type)
    return html.split("</style>")[-1]  # ohne Stylesheet (enthält die CSS-Klassen immer)


def _legend_ids(html):
    return re.findall(r"id='operator-legend-(\d+)'", html)


def _diags(body, document_type="exam"):
    return inspect_markdown_text(HEAD.format(dt=document_type) + body, document_type=document_type).diagnostics


def _codes(body, document_type="exam"):
    return [d.code for d in _diags(body, document_type)]


def test_slash_in_operator_key_allows_line_break():
    html = render_operator_legend_html([MatchedOperator("Begründen/Nachweisen/Zeigen", "x")])
    assert "Begründen/<wbr>Nachweisen/<wbr>Zeigen" in html


def test_no_automatic_legend_without_block():
    html = _html(TASK_A + TASK_B, document_type="worksheet")
    assert _legend_ids(html) == [] and "operator-legend-probe" not in html


def test_block_renders_table_with_probes_at_its_position():
    html = _html(TASK_A + OPS + TASK_B, document_type="worksheet")
    assert _legend_ids(html) == ["0"]
    assert legend_probe_uri(0, "top") in html and legend_probe_uri(0, "bottom") in html
    legend = html.index("id='operator-legend-0'")
    assert html.index("zwei Beispiele") < legend < html.index("den Ablauf")
    assert "Nennen/<wbr>Angeben" in html[legend:] and "Beschreiben" not in html[legend:html.index("den Ablauf")]


def test_scope_previous_starts_after_previous_table():
    html = _html(TASK_A + OPS + TASK_B + OPS)
    first, second = html.index("id='operator-legend-0'"), html.index("id='operator-legend-1'")
    assert "Nennen" in html[first:second] and "Beschreiben" not in html[first:second]
    assert "Beschreiben" in html[second:] and "Nennen" not in html[second:]


def test_scope_all_lists_operators_after_the_table_too():
    html = _html(":::operators scope=all:::\n" + TASK_A + TASK_B)
    legend = html.index("id='operator-legend-0'")
    assert "Nennen" in html[legend:html.index("zwei Beispiele")] and "Beschreiben" in html[legend:html.index("zwei Beispiele")]


def test_scope_part_uses_aid_split_and_cover_belongs_to_part_a():
    body = "!!Beschreibe!! kurz, was erlaubt ist.\n\n--hm\n" + TASK_A + ":::operators scope=part:::\n--hm\n" + TASK_PLAIN
    coverage = operator_block_coverages(parse_blocks(body), "exam")[0]
    assert coverage.scope == "part"
    html = _html(body)
    legend = html.index("id='operator-legend-0'")
    assert legend < html.index("Teil B – mit Hilfsmitteln")
    assert "Beschreiben" in html[legend:] and "Nennen" in html[legend:]


def test_scope_part_without_split_is_whole_document():
    html = _html(":::operators scope=part:::\n" + TASK_A + TASK_B, document_type="worksheet")
    legend = html.index("id='operator-legend-0'")
    assert "Nennen" in html[legend:html.index("zwei Beispiele")] and "Beschreiben" in html[legend:html.index("zwei Beispiele")]


def test_table_before_hm_stays_in_part_a():
    html = _html(TASK_A + OPS + "--hm\n" + TASK_B + OPS)
    assert _legend_ids(html) == ["0", "1"]
    assert html.index("id='operator-legend-0'") < html.index("Teil B – mit Hilfsmitteln") < html.index("id='operator-legend-1'")


def test_top_level_table_is_its_own_print_section_but_not_inside_columns():
    html = _html(TASK_A + OPS)
    assert "<section class='ab-section'><div data-block-type=\"operators\"" in html
    columns = _html(":::columns:::\n" + TASK_A + ":::nextcol:::\n" + OPS + ":::endcolumns:::\n")
    assert "<section class='ab-section'><div data-block-type=\"operators\"" not in columns


def test_title_is_inside_wrapper():
    html = _html(TASK_A + ":::operators title=\"Operatoren\":::\n")
    wrapper = html.index("id='operator-legend-0'")
    assert wrapper < html.index("<div class='operator-legend-title'>Operatoren</div>") < html.index("<table class='operator-legend'>")


def test_default_mode_is_worksheet_only_and_mode_solution_switches():
    assert _legend_ids(_html(TASK_A + OPS, include_solutions=True)) == []
    assert _legend_ids(_html(TASK_A + OPS)) == ["0"]
    assert _legend_ids(_html(TASK_A + ":::operators mode=solution:::\n")) == []
    assert _legend_ids(_html(TASK_A + ":::operators mode=solution:::\n", include_solutions=True)) == ["0"]


def test_empty_table_renders_nothing_and_indices_stay_unique():
    html = _html(":::operators:::\n" + TASK_PLAIN + TASK_A + OPS + TASK_B + OPS)
    assert _legend_ids(html) == ["0", "1"]


def test_presentation_renders_no_table():
    blocks = parse_blocks(TASK_A + OPS)
    html = render_html(META, blocks, document_type="presentation")
    assert "operator-legend-probe' href" not in html


def test_opr004_operators_without_any_table():
    assert "OPR004" in _codes(TASK_A + TASK_B)
    assert "OPR004" not in _codes(TASK_PLAIN)


def test_opr005_operators_after_last_previous_table_but_covered_with_scope_all():
    assert "OPR005" in _codes(TASK_A + OPS + TASK_B)
    assert "OPR005" not in _codes(TASK_A + ":::operators scope=all:::\n" + TASK_B)


def test_opr006_table_without_operators_is_error():
    diagnostics = _diags(OPS + TASK_A + OPS)
    assert any(d.code == "OPR006" and d.severity == "error" for d in diagnostics)
    assert has_blocking_diagnostics(diagnostics)


def test_opr007_table_in_presentation():
    assert "OPR007" in _codes(TASK_A + OPS, document_type="presentation")
    assert "OPR004" not in _codes(TASK_A, document_type="presentation")


def test_opr008_overlap_is_warned_once_per_table_but_allowed():
    diagnostics = _diags(TASK_A + ":::operators scope=all:::\n" + TASK_B + OPS)
    overlaps = [d for d in diagnostics if d.code == "OPR008"]
    assert len(overlaps) == 2 and all(d.severity == "warning" for d in overlaps)
    assert not any(d.code in {"OPR004", "OPR005"} for d in diagnostics)


def test_scope_value_is_validated():
    assert "OP002" in _codes(TASK_A + ":::operators scope=foo:::\n")


def test_insert_menu_and_snippet():
    families = {label: entries for label, entries in BLOCK_INSERT_FAMILIES}
    assert any(block == "operators" for entries in families.values() for _label, block in entries)
    assert BLOCK_INSERT_SNIPPETS["operators"].startswith(":::operators")


def test_operator_legend_html_key_is_only_set_by_operator_legend_blocks():
    """Guard: nur `operator_legend_blocks` schreibt das Tabellen-HTML an den Block."""
    app_dir = Path(__file__).resolve().parents[1] / "app"
    writers = sorted(
        path.relative_to(app_dir).as_posix()
        for path in app_dir.rglob("*.py")
        if "OPERATOR_LEGEND_HTML_KEY" in path.read_text(encoding="utf-8") or "\"_operator_legend_html\"" in path.read_text(encoding="utf-8")
    )
    assert writers == ["core/blatt_kern_task_render.py", "core/operator_legend_blocks.py"]
    render_source = (app_dir / "core" / "blatt_kern_task_render.py").read_text(encoding="utf-8")
    assert "{**options, OPERATOR_LEGEND_HTML_KEY" not in render_source
