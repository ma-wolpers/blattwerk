"""Kopfzeile je Klausurteil: jeder Teil auf neuer Seite trägt die Schülerkopfzeile.

Regel (`exam_part_render.part_starts_new_page`): Teil B beginnt immer auf einer
neuen Seite, Teil A nur mit Deckblatt. Die Kopfzeile ist dieselbe wie am
Dokumentanfang (`student_header.render_student_header`) und erscheint nur mit
`show_student_header`.
"""

from __future__ import annotations

from app.core.blatt_kern_layout_render import render_html
from app.core.blatt_kern_shared import parse_blocks
from app.core.exam_expectation_horizon import build_expectation_horizon_html
from app.core.exam_part_render import AID_PART_LABELS

HEADER = "class=\"student-header\""
META_ON = {"Titel": "T", "show_student_header": "ja", "Lerngruppe": "11.6", "Datum": "01.10.2026"}
PART_A = ":::task points=2 afb=1\nA\n:::\n"
PART_B = ":::task points=3 afb=2\nB\n:::\n"
ONE_MARKER = PART_A + "--hm\n" + PART_B
WITH_COVER = "Hinweise zur Klausur.\n\n--hm\n" + PART_A + "--hm\n" + PART_B


def _html(body, meta=META_ON, document_type="exam"):
    """Rendert `body` als Dokument des gegebenen Typs."""
    return render_html(dict(meta), parse_blocks(body), document_type=document_type)


def test_without_cover_header_on_top_and_before_part_b():
    """Ohne Deckblatt: Dokumentanfang (= Teil A) und Teil B."""
    assert _html(ONE_MARKER).count(HEADER) == 2


def test_with_cover_header_on_cover_part_a_and_part_b():
    """Mit Deckblatt beginnt auch Teil A auf einer neuen Seite."""
    assert _html(WITH_COVER).count(HEADER) == 3


def test_no_header_anywhere_when_switched_off():
    """Ohne `show_student_header` ändert sich nichts."""
    assert HEADER not in _html(WITH_COVER, meta={"Titel": "T"})


def test_worksheet_keeps_a_single_header():
    """`--hm` wirkt nur in Klausuren -- im Arbeitsblatt bleibt es bei einer Kopfzeile."""
    assert _html(ONE_MARKER, document_type="worksheet").count(HEADER) == 1


def test_order_pagebreak_then_header_then_heading_and_prefill_repeated():
    """Teil B: Umbruch, Kopfzeile, Überschrift; Vorbefüllung auch im Teil."""
    html = _html(ONE_MARKER)
    start = html.index("class='ab-pagebreak'")
    assert html.index(HEADER) < start  # Dokumentanfang vor dem Umbruch
    header = html.index(HEADER, start)
    heading = html.index(AID_PART_LABELS["B"], start)
    assert start < header < heading
    assert html.count("11.6") == 2 and html.count("01.10.2026") == 2


def test_expectation_horizon_uses_the_shared_part_labels():
    """Der Erwartungshorizont nutzt dieselben Teilbezeichnungen (keine Kopie)."""
    head = "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n"
    html, _diagnostics = build_expectation_horizon_html(head + ONE_MARKER)
    assert f"<h2>{AID_PART_LABELS['A']}</h2>" in html and f"<h2>{AID_PART_LABELS['B']}</h2>" in html


def test_part_b_page_of_the_pdf_starts_with_the_header(tmp_path):
    """Echte PDF: Die Seite von Teil B enthält Name, Lerngruppe und Datum."""
    import fitz

    from app.core.blatt_kern_io_build import build_worksheet

    source = tmp_path / "klausur.kbw"
    source.write_text(
        "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\nshow_student_header: ja\n"
        "Lerngruppe: \"11.6\"\n---\n" + ONE_MARKER,
        encoding="utf-8",
    )
    out = tmp_path / "klausur.pdf"
    build_worksheet(source, out, document_type="exam", block_on_critical=False)
    with fitz.open(out) as doc:
        page_b = next(page.get_text() for page in doc if "Teil B" in page.get_text())
    assert "Name" in page_b and "11.6" in page_b
