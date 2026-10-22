"""Wahlteile `--w[k] Titel` / `--w Titel` in Klausuren (Wunschliste Schritt 6b)."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.blatt_validator import has_blocking_diagnostics, inspect_markdown_text
from app.core.evaluation_table import build_evaluation_table
from app.core.exam_analysis import analyze_exam, format_analysis_lines
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.exam_parts import exam_max_points, resolve_exam_parts
from app.core.points_model import build_points_model

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"


def _task(points, afb=1, name="X"):
    return f":::task points={points} afb={afb}\n{name}\n:::\n:::solution\n1. ok ({points}P)\n:::\n"


TWO_REGIONS = (
    _task(2, name="Pflicht")
    + "--w[1] Analysis\n" + _task(5, 2, "W11")
    + "--w Stochastik\n" + _task(5, 3, "W12")
    + "--hm\n" + _task(3, name="B")
    + "--w[2] X\n" + _task(4, name="W21")
    + "--w\n" + _task(4, name="W22")
    + "--w Y\n" + _task(4, name="W23")
    + "--w Z\n" + _task(4, name="W24")
)
EXPECTED_MAX = Decimal(2 + 5 + 3 + 2 * 4)


def _layout(body, document_type="exam"):
    return resolve_exam_parts(parse_blocks(body), document_type).layout


def _diagnostics(body, document_type="exam"):
    return inspect_markdown_text(HEAD + body, document_type=document_type).diagnostics


def test_two_regions_with_group_identity():
    layout = _layout(TWO_REGIONS)
    assert [p.part_id for p in layout.parts] == ["A", "W1.1", "W1.2", "B", "W2.1", "W2.2", "W2.3", "W2.4"]
    assert [(g.group_id, g.k, g.part_ids) for g in layout.groups] == [
        ("G1", 1, ("W1.1", "W1.2")),
        ("G2", 2, ("W2.1", "W2.2", "W2.3", "W2.4")),
    ]
    assert [p.heading for p in layout.parts if p.group_id == "G1"] == ["Wahlteil 1 – Analysis", "Wahlteil 2 – Stochastik"]
    assert layout.parts[5].heading == "Wahlteil 2"
    assert not [d for d in _diagnostics(TWO_REGIONS) if d.severity == "error"]


def test_sums_identical_in_table_analysis_horizon_and_max_points():
    blocks = parse_blocks(TWO_REGIONS)
    layout = resolve_exam_parts(blocks, "exam").layout
    analysis = analyze_exam(blocks, "exam")
    table = build_evaluation_table(blocks, {}, "exam")
    part_points = {p.part_id: r.points for p, r in zip(layout.parts, analysis.parts)}
    assert exam_max_points(layout, part_points) == analysis.total.points == table.grand_total == EXPECTED_MAX
    assert len(table.groups) == len(layout.parts)  # Wahlteile erzwingen die Gruppierung nach Teilen
    html, _diags = build_expectation_horizon_html(HEAD + TWO_REGIONS)
    assert "Wahlbereich: 2 aus 4" in html and "<td>Gesamt</td><td>18 P</td><td>–</td>" in html


def test_no_total_afb_with_choices():
    lines = format_analysis_lines(analyze_exam(parse_blocks(TWO_REGIONS), "exam"))
    total = lines.index("Gesamt: 18 P")
    assert lines[total + 1] == "  AFB nur je Teil (Wahlteile)" and len(lines) == total + 2


def test_render_each_choice_part_on_new_page_with_checkbox_and_note():
    html = render_html({"Titel": "T"}, parse_blocks(TWO_REGIONS), document_type="exam")
    starts = re.findall(r"ab-pagebreak' aria-hidden='true'></div><(?:p class='exam-choice-note'|h2 class='aid-part')", html)
    assert len(starts) == 7  # W1.1, W1.2, B, W2.1–W2.4 (Teil A steht am Anfang)
    assert html.count("class='exam-choice-check'") == 6
    assert "Bearbeite 1 der 2 Wahlteile." in html and "Bearbeite 2 der 4 Wahlteile." in html


def test_student_header_on_first_page_of_every_choice_part():
    meta = {"Titel": "T", "show_student_header": "ja"}
    assert render_html(meta, parse_blocks(TWO_REGIONS), document_type="exam").count('class="student-header"') == 8


def test_taskless_part_before_region_shares_the_page():
    body = _task(2) + "--hm\nMit Hilfsmitteln.\n\n--w[1] X\n" + _task(3) + "--w Y\n" + _task(3)
    layout = _layout(body)
    assert [(p.part_id, p.page_break) for p in layout.parts] == [("A", False), ("B", True), ("W1.1", False), ("W1.2", True)]


def test_intro_only_required_part_has_no_heading_and_no_table_group():
    body = "Einleitung\n\n--w[1] X\n" + _task(3) + "--w Y\n" + _task(3)
    blocks = parse_blocks(body)
    layout = resolve_exam_parts(blocks, "exam").layout
    assert [(p.part_id, p.heading, p.page_break) for p in layout.parts] == [("P", "", False), ("W1.1", "Wahlteil 1 – X", False), ("W1.2", "Wahlteil 2 – Y", True)]
    html = render_html({"Titel": "T"}, blocks, document_type="exam")
    assert "<h2 class='aid-part'></h2>" not in html
    assert "Pflichtteil" not in format_analysis_lines(analyze_exam(blocks, "exam"))[0]


def test_units_never_cross_a_choice_marker():
    body = _task(2) + "--w[1] X\n:::subtask points=1\nlose\n:::\n" + _task(1) + "--w Y\n" + _task(2)
    assert [u.number for u in build_points_model(parse_blocks(body))] == ["1", "2", "3"]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (_task(1) + "--w X\n" + _task(1), "KL008"),
        (_task(1) + "--w[1] X\n" + _task(1) + "--w[1] Y\n" + _task(1), "KL009"),
        (_task(1) + "--w[2] X\n" + _task(1) + "--w Y\n" + _task(1), "KL010"),
        (_task(1) + "--w[x] X\n" + _task(1) + "--w Y\n" + _task(1), "KL010"),
        (_task(1) + "--w[] X\n" + _task(1) + "--w Y\n" + _task(1), "KL010"),
        (_task(1) + "--w[1] X\n" + _task(2) + "--w Y\n" + _task(3), "KL011"),
        (_task(1) + "--w[1] X\nnur Text\n\n--w Y\n" + _task(1), "KL004"),
        (":::columns\n" + _task(1) + "--w[1] X\n" + _task(1) + ":::endcolumns\n--w Y\n" + _task(1), "KL004"),
        (_task(1) + "--w[1] X\n:::subtask points=1\nx\n:::\n" + _task(1) + "--w Y\n" + _task(1), "KL005"),
    ],
)
def test_structural_errors_block_the_build(body, code):
    diagnostics = _diagnostics(body)
    assert any(d.code == code and d.severity == "error" for d in diagnostics), [d.code for d in diagnostics]
    assert has_blocking_diagnostics(diagnostics)


def test_choice_marker_outside_exam_is_an_error():
    body = _task(1) + "--w[1] X\n" + _task(1) + "--w Y\n" + _task(1)
    diagnostics = _diagnostics(body, "worksheet")
    assert [d.code for d in diagnostics if d.code.startswith("KL")] == ["KL012", "KL012"]
    assert has_blocking_diagnostics(diagnostics) and _layout(body, "worksheet") is None


def test_pdf_puts_each_choice_part_on_its_own_page(tmp_path):
    """End-to-end: jeder Wahlteil beginnt im PDF auf einer eigenen Seite mit Ankreuzfeld."""
    fitz = pytest.importorskip("fitz")
    from app.core.blatt_kern_io_build import build_worksheet
    from app.core.blatt_kern_io_pdf import find_chromium_executable

    if find_chromium_executable() is None:
        pytest.skip("kein Chromium-Browser fuer den PDF-Druck")
    source = tmp_path / "klausur.kbw"
    body = _task(2, name="Pflicht") + "--w[1] Analysis\n" + _task(5, name="Ana") + "--w Stochastik\n" + _task(5, name="Sto")
    source.write_text(HEAD + body, encoding="utf-8")
    out = tmp_path / "klausur.pdf"
    build_worksheet(source, out, document_type="exam", block_on_critical=False)
    with fitz.open(out) as doc:
        pages = [page.get_text() for page in doc]
    first_page = {title: next(i for i, text in enumerate(pages) if title in text) for title in ("Pflicht", "Wahlteil 1 – Analysis", "Wahlteil 2 – Stochastik")}
    assert sorted(first_page.values()) == list(range(3))
    assert all("Diesen Wahlteil bearbeite ich." in pages[first_page[t]] for t in ("Wahlteil 1 – Analysis", "Wahlteil 2 – Stochastik"))
