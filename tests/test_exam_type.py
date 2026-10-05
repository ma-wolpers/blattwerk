"""Dokumenttyp Klausur: `--hm`, AFB, Klausur-Diagnosen und Auswertung (Phase 5)."""

from decimal import Decimal

import pytest

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks, split_front_matter
from app.core.blatt_validator import inspect_markdown_text
from app.core.document_semantics import resolve_aid_split
from app.core.document_type_templates import build_new_document_content
from app.core.exam_analysis import analyze_exam, format_analysis_lines

HEAD = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
SPLIT = ":::task points=4 afb=1\nA\n:::\n--hm\n:::task points=6 afb=2\nB\n:::\n"


def _codes(body, document_type="exam"):
    return [d.code for d in inspect_markdown_text(HEAD + body, document_type=document_type).diagnostics]


def test_exam_template_is_valid_and_has_no_mode():
    content = build_new_document_content("exam", {})
    meta, _rest = split_front_matter(content)
    assert meta["document_type"] == "exam" and "mode" not in meta
    diagnostics = inspect_markdown_text(content, document_type="exam").diagnostics
    assert not [d for d in diagnostics if d.severity == "error"]
    assert "KL003" not in [d.code for d in diagnostics]


def test_hm_parses_as_top_level_pseudo_block():
    assert [b[0] for b in parse_blocks(SPLIT)] == ["task", "aidsplit", "task"]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (SPLIT + "--hm\n:::task points=1 afb=3\nC\n:::\n", "KL001"),
        ("--hm\n" + SPLIT.replace("--hm\n", ""), "KL004"),
        (":::task points=1 afb=1\nA\n:::\n--hm\n", "KL004"),
        (":::task points=1 afb=1\nA\n:::\n--hm\n:::solution\n1. x\n:::\n:::task points=1 afb=1\nB\n:::\n", "KL005"),
        (":::task afb=1\nA\n:::\n--hm\n:::subtask points=1\na\n:::\n:::task points=1 afb=1\nB\n:::\n", "KL005"),
        (":::columns\n:::task points=1 afb=1\nA\n:::\n--hm\n:::task points=1 afb=1\nB\n:::\n:::endcolumns\n", "KL004"),
    ],
)
def test_hm_position_errors(body, code):
    diagnostics = inspect_markdown_text(HEAD + body, document_type="exam").diagnostics
    assert any(d.code == code and d.severity == "error" for d in diagnostics)


def test_hm_inside_block_is_bl005():
    assert "BL005" in _codes(":::task points=1 afb=1\nA\n--hm\nB\n:::\n")


@pytest.mark.parametrize("document_type", ["worksheet", "presentation"])
def test_hm_outside_exam_warns_and_has_no_effect(document_type):
    blocks = parse_blocks(SPLIT)
    assert "KL002" in _codes(SPLIT, document_type)
    assert resolve_aid_split(blocks, document_type) is None
    html = render_html({"Titel": "T"}, blocks, document_type=document_type)
    assert "Teil A" not in html and "Teil B" not in html
    assert analyze_exam(blocks, document_type).parts == []


def test_exam_renders_parts_with_continuing_numbers():
    html = render_html({"Titel": "T"}, parse_blocks(SPLIT), document_type="exam")
    assert html.index("Teil A – hilfsmittelfrei") < html.index("Aufgabe 1") < html.index("Teil B – mit Hilfsmitteln") < html.index("Aufgabe 2")
    assert html.count("class='ab-pagebreak'") == 1


def test_exam_hides_work_icons():
    html = render_html({"Titel": "T"}, parse_blocks(":::task work=pair afb=1 points=1\nA\n:::\n"), document_type="exam")
    assert "title='Partnerarbeit'" not in html


def test_afb_inheritance_and_percentages_relative_to_total():
    body = (
        ":::task afb=1\nA\n:::\n:::subtask points=2\na\n:::\n:::subtask points=8 afb=3\nb\n:::\n"
        ":::task points=10 afb=2\nB\n:::\n"
    )
    analysis = analyze_exam(parse_blocks(body), "exam")
    assert analysis.total.points == Decimal(20) and analysis.total.complete
    assert analysis.total.afb_points == {1: Decimal(2), 2: Decimal(10), 3: Decimal(8)}
    assert analysis.percent(analysis.total.afb_points[2]) == Decimal("50.0")
    assert analysis.parts == []
    assert "  AFB II: 10 P · 50 %" in format_analysis_lines(analysis)


def test_parts_use_total_points_as_percent_base():
    analysis = analyze_exam(parse_blocks(SPLIT), "exam")
    part_a, part_b = analysis.parts
    assert (part_a.points, part_b.points) == (Decimal(4), Decimal(6))
    assert analysis.percent(part_a.afb_points[1]) == Decimal("40.0")  # 4 von 10 Gesamtpunkten
    lines = format_analysis_lines(analysis)
    assert lines[0] == "Teil A: 4 P" and "  AFB I: 4 P · 40 %" in lines


def test_incomplete_analysis_has_no_percentages():
    analysis = analyze_exam(parse_blocks(":::task points=4 afb=1\nA\n:::\n:::task points=6\nB\n:::\n"), "exam")
    assert not analysis.total.complete
    assert analysis.percent(Decimal(4)) is None
    lines = format_analysis_lines(analysis)
    assert "%" not in "\n".join(lines) and any("6 P ohne AFB" in line for line in lines)
    assert "KL003" in _codes(":::task points=6\nB\n:::\n")


def test_zero_total_points_gives_no_percentages():
    analysis = analyze_exam(parse_blocks(":::info\nnur Text\n:::\n"), "exam")
    assert analysis.percent(Decimal(0)) is None
    assert "Keine Punkte vergeben." in format_analysis_lines(analysis)


def test_subtask_afb_without_subtask_points_is_kl006():
    assert "KL006" in _codes(":::task points=4 afb=1\nA\n:::\n:::subtask afb=3\na\n:::\n")


def test_afb_value_is_validated():
    assert "OP002" in _codes(":::task points=1 afb=4\nA\n:::\n")


def test_hm_adds_a_page_in_exam_pdf_and_not_in_worksheet_pdf(tmp_path):
    import fitz

    from app.core.blatt_kern_io_build import build_worksheet

    source = tmp_path / "klausur.kbw"
    source.write_text(HEAD + SPLIT, encoding="utf-8")

    def pages(document_type):
        out = tmp_path / f"{document_type}.pdf"
        build_worksheet(source, out, document_type=document_type, block_on_critical=False)
        with fitz.open(out) as doc:
            return len(doc), doc[1].get_text() if len(doc) > 1 else ""

    exam_pages, second_page_text = pages("exam")
    worksheet_pages, _ = pages("worksheet")
    assert exam_pages == worksheet_pages + 1
    assert "Teil B" in second_page_text
