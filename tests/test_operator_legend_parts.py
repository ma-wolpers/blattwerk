"""Operatorenliste je Teil, Umbruch am Schrägstrich und Messmarken (`operator_legend_parts`)."""

from __future__ import annotations

import re
from pathlib import Path

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.operator_legend import MatchedOperator, render_operator_legend_html
from app.core.operator_legend_parts import (
    PART_END_HTML_KEY,
    build_part_legends,
    legend_probe_uri,
)

META = {"Titel": "T", "Fach": "Informatik"}
TASK_A = ":::task points=2 afb=1\n!!Nenne!! zwei Beispiele.\n:::\n"
TASK_B = ":::task points=3 afb=2\n!!Beschreibe!! den Ablauf.\n:::\n"
TASK_PLAIN = ":::task points=1 afb=1\nOhne Operator.\n:::\n"
COVER = "Hinweise für alle Teile.\n\n"


def _html(body, document_type="exam", include_solutions=False):
    return render_html(META, parse_blocks(body), include_solutions=include_solutions, document_type=document_type)


def _legend_ids(html):
    return re.findall(r"id='operator-legend-(\d+)'", html)


def test_slash_in_operator_key_allows_line_break():
    html = render_operator_legend_html([MatchedOperator("Begründen/Nachweisen/Zeigen", "x")])
    assert "Begründen/<wbr>Nachweisen/<wbr>Zeigen" in html


def test_without_split_one_legend_with_all_operators_and_probes():
    html = _html(TASK_A + TASK_B, document_type="worksheet")
    assert _legend_ids(html) == ["0"]
    assert legend_probe_uri(0, "top") in html and legend_probe_uri(0, "bottom") in html
    assert "Nennen/<wbr>Angeben" in html and "Beschreiben" in html


def test_single_marker_gives_one_legend_per_part():
    html = _html(TASK_A + "--hm\n" + TASK_B)
    assert _legend_ids(html) == ["0", "1"]
    legend_a, legend_b = html.index("id='operator-legend-0'"), html.index("id='operator-legend-1'")
    part_b = html.index("Teil B – mit Hilfsmitteln")
    assert legend_a < part_b < legend_b
    assert "Nennen" in html[legend_a:part_b] and "Beschreiben" not in html[legend_a:part_b]
    assert "Beschreiben" in html[legend_b:] and "Nennen" not in html[legend_b:]


def test_two_markers_cover_operators_belong_to_part_a():
    body = "!!Beschreibe!! kurz, was erlaubt ist.\n\n--hm\n" + TASK_A + "--hm\n" + TASK_PLAIN
    html = _html(body)
    assert _legend_ids(html) == ["0"]
    legend = html.index("id='operator-legend-0'")
    assert legend < html.index("Teil B – mit Hilfsmitteln")
    assert "Beschreiben" in html[legend:] and "Nennen" in html[legend:]


def test_part_without_operators_gets_no_legend():
    html = _html(TASK_PLAIN + "--hm\n" + TASK_B)
    assert _legend_ids(html) == ["0"]
    assert html.index("id='operator-legend-0'") > html.index("Teil B – mit Hilfsmitteln")
    html = _html(TASK_A + "--hm\n" + TASK_PLAIN)
    assert _legend_ids(html) == ["0"] and html.index("id='operator-legend-0'") < html.index("Teil B")


def test_no_operators_no_wrapper():
    html = _html(TASK_PLAIN + "--hm\n" + TASK_PLAIN)
    assert _legend_ids(html) == [] and "class='operator-legend-probe'" not in html


def test_solution_version_has_no_legend():
    blocks, end_html = build_part_legends(parse_blocks(TASK_A + "--hm\n" + TASK_B), META, "exam", include_solutions=True)
    assert end_html == "" and not any(PART_END_HTML_KEY in options for _t, options, _c in blocks)
    assert _legend_ids(_html(TASK_A + "--hm\n" + TASK_B, include_solutions=True)) == []


def test_part_end_key_is_only_set_by_operator_legend_parts():
    """Guard: am A/B-Trenner sammeln sich keine weiteren fachfremden Daten an."""
    app_dir = Path(__file__).resolve().parents[1] / "app"
    writers = [
        path.relative_to(app_dir).as_posix()
        for path in app_dir.rglob("*.py")
        if "PART_END_HTML_KEY" in path.read_text(encoding="utf-8") or "_part_end_html" in path.read_text(encoding="utf-8")
    ]
    assert sorted(writers) == ["core/blatt_kern_task_render.py", "core/operator_legend_parts.py"]
    render_source = (app_dir / "core" / "blatt_kern_task_render.py").read_text(encoding="utf-8")
    assert f"{{**options, PART_END_HTML_KEY" not in render_source
