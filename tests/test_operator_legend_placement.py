"""Operatorenliste am Seitenende (`operator_legend_placement`).

Zwei Ebenen:

* Logik mit synthetischen PDFs (PyMuPDF, deterministisch): Messung, „allein auf
  der Seite“, mehrseitige/fehlende/doppelte Marken, Pass-2-Absicherung,
  Entfernen nur der eigenen Messlinks.
* Integration mit echtem Chromium (übersprungen, wenn keiner installiert ist):
  Liste passt -> unten; passt nicht -> nächste Seite oben; Seitengrenze; Klausur
  mit `--hm` (Liste A unten auf der letzten Seite von Teil A).
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.core.blatt_kern_io_pdf import find_chromium_executable
from app.core.operator_legend_blocks import legend_probe_uri
from app.core.operator_legend_placement import (
    SAFETY_PT,
    compute_shifts,
    content_area,
    measure_legends,
    strip_probe_links,
    write_pdf_with_bottom_legends,
)

A4 = (595.0, 842.0)


def _doc_with(pages, links, texts=()):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=A4[0], height=A4[1])
    for page_number, y, text in texts:
        doc[page_number].insert_text((60, y), text)
    for page_number, uri, y in links:
        doc[page_number].insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(43, y, 552, y + 0.75), "uri": uri})
    return doc


def _legend_links(index, top_page, top_y, bottom_page, bottom_y):
    return [(top_page, legend_probe_uri(index, "top"), top_y), (bottom_page, legend_probe_uri(index, "bottom"), bottom_y)]


# -- Logik (synthetisch) ---------------------------------------------------------------


def test_legend_below_content_is_shifted_to_content_bottom():
    doc = _doc_with(1, _legend_links(0, 0, 300, 0, 380), texts=[(0, 120, "Aufgabe 1")])
    area = content_area(doc[0].rect, "a4_portrait", False)
    shifts = compute_shifts(doc, "a4_portrait", False)
    assert shifts[0] == pytest.approx(area.bottom - 380.75 - SAFETY_PT, abs=0.05)


def test_legend_alone_on_page_stays_on_top():
    doc = _doc_with(2, _legend_links(0, 1, 60, 1, 140), texts=[(0, 120, "Aufgabe 1")])
    assert compute_shifts(doc, "a4_portrait", False) == {}


def test_content_only_in_page_margin_does_not_count():
    doc = _doc_with(1, _legend_links(0, 0, 60, 0, 140))
    doc[0].draw_rect(fitz.Rect(5, 10, 20, 40), color=(0, 0, 0))  # z. B. Lochmarke im Rand
    assert compute_shifts(doc, "a4_portrait", False) == {}


def test_multi_page_legend_is_never_shifted():
    doc = _doc_with(2, _legend_links(0, 0, 700, 1, 120), texts=[(0, 120, "Aufgabe 1")])
    assert measure_legends(doc) == {0: None}
    assert compute_shifts(doc, "a4_portrait", False) == {}


@pytest.mark.parametrize(
    "links",
    [
        [(0, legend_probe_uri(0, "top"), 300)],
        _legend_links(0, 0, 300, 0, 380) + [(0, legend_probe_uri(0, "top"), 500)],
    ],
)
def test_missing_or_duplicate_probe_means_no_shift(links):
    doc = _doc_with(1, links, texts=[(0, 120, "Aufgabe 1")])
    assert measure_legends(doc) == {0: None}
    assert compute_shifts(doc, "a4_portrait", False) == {}


def test_strip_removes_only_own_probe_links(tmp_path):
    doc = _doc_with(1, _legend_links(0, 0, 300, 0, 380) + [(0, "https://example.org/", 500)])
    path = tmp_path / "x.pdf"
    doc.save(path)
    strip_probe_links(path)
    with fitz.open(path) as result:
        assert [link["uri"] for link in result[0].get_links()] == ["https://example.org/"]


def _fake_render(first_doc, second_doc):
    calls = []

    def render(html, out):
        calls.append(html)
        (first_doc if len(calls) == 1 else second_doc).save(out)
        return Path(out)

    return render, calls


def test_pass2_with_changed_page_count_keeps_pass1(tmp_path):
    first = _doc_with(1, _legend_links(0, 0, 300, 0, 380), texts=[(0, 120, "PASS1")])
    second = _doc_with(2, _legend_links(0, 1, 60, 1, 140), texts=[(0, 120, "PASS2")])
    render, calls = _fake_render(first, second)
    out = write_pdf_with_bottom_legends("<html><head></head><body>" + legend_probe_uri(0, "top") + "</body></html>", tmp_path / "o.pdf",
                                        page_format="a4_portrait", hole_punch_enabled=False, render=render)
    assert len(calls) == 2 and "padding-top" in calls[1]
    with fitz.open(out) as result:
        assert result.page_count == 1 and "PASS1" in result[0].get_text()
        assert result[0].get_links() == []
    assert not list(tmp_path.glob("*.legend-pass2.pdf"))


def test_measurement_error_keeps_pass1_without_user_error(tmp_path):
    def render(html, out):
        Path(out).write_bytes(b"kein pdf")
        return Path(out)

    out = write_pdf_with_bottom_legends("<html><head></head><body>" + legend_probe_uri(0, "top") + "</body></html>", tmp_path / "o.pdf",
                                        page_format="a4_portrait", hole_punch_enabled=False, render=render)
    assert out.read_bytes() == b"kein pdf"


def test_without_legend_only_one_print():
    calls = []

    def render(html, out):
        calls.append(html)
        return Path(out)

    write_pdf_with_bottom_legends("<html>ohne Liste</html>", "x.pdf", page_format="a4_portrait", hole_punch_enabled=False, render=render)
    assert len(calls) == 1


# -- Integration (echtes Chromium) -----------------------------------------------------

needs_chromium = pytest.mark.skipif(find_chromium_executable() is None, reason="kein Chromium-Browser installiert")
HEAD = "---\ndocument_type: {dt}\nTitel: T\nFach: Informatik\nThema: X\n---\n"
LEGEND_WORD = "Angeben"  # nur im Schlüssel „Nennen/Angeben“, nicht im Aufgabentext


def _build(tmp_path, body, document_type="worksheet", name="doc"):
    from app.core.blatt_kern_io_build import build_worksheet

    suffix = ".kbw" if document_type == "exam" else ".abw"
    md = tmp_path / f"{name}{suffix}"
    md.write_text(HEAD.format(dt=document_type) + body, encoding="utf-8")
    return Path(build_worksheet(str(md), str(tmp_path / f"{name}.pdf"), include_solutions=False, document_type=document_type))


def _legend_box(pdf_path):
    """(Seite, Oberkante Schlüsselzeile, Unterkante Tabelle) der Liste mit „Nennen/Angeben“."""
    with fitz.open(pdf_path) as doc:
        hits = [(number, rect) for number, page in enumerate(doc) for rect in page.search_for(LEGEND_WORD)]
        assert len(hits) == 1, hits
        number, rect = hits[0]
        page = doc[number]
        area = content_area(page.rect, "a4_portrait", False)
        bottoms = [d["rect"].y1 for d in page.get_drawings() if d["rect"].y1 >= rect.y0]
        texts_above = [b for b in page.get_text("blocks") if b[3] < rect.y0 - 20 and fitz.Rect(b[:4]).intersects(fitz.Rect(area.left, area.top, area.right, area.bottom))]
        assert doc[number].get_links() == []
        return number, rect.y0, max(bottoms), area, bool(texts_above), doc.page_count


def _build_and_box(tmp_path, body, document_type="worksheet", name="doc"):
    return _legend_box(_build(tmp_path, body, document_type, name))


@needs_chromium
def test_fitting_legend_ends_at_content_bottom(tmp_path):
    page, _top, bottom, area, _above, pages = _build_and_box(tmp_path, ":::task\n!!Nenne!! zwei Beispiele.\n:::\n:::operators:::\n")
    assert pages == 1 and page == 0
    assert area.bottom - 6 <= bottom <= area.bottom + 0.5


@needs_chromium
def test_legend_that_does_not_fit_goes_to_next_page_top(tmp_path):
    page, top, _bottom, area, above, pages = _build_and_box(tmp_path, ":::task\n!!Nenne!! zwei Beispiele.\n:::\n-=21.5cm\n:::operators:::\n")
    assert pages == 2 and page == 1 and not above
    assert top < area.top + 40


@needs_chromium
@pytest.mark.parametrize("height_cm", [20.5, 21.0, 21.5, 22.0, 22.5])
def test_page_boundary_is_either_bottom_aligned_or_alone_on_top(tmp_path, height_cm):
    """Grenzfall Seitenumbruch (inkl. 1-px-Messmarken): nie aufgeteilt, nie halb verschoben."""
    _page, top, bottom, area, above, _pages = _build_and_box(
        tmp_path, f":::task\n!!Nenne!! zwei Beispiele.\n:::\n-={height_cm}cm\n:::operators:::\n", name=f"b{height_cm}"
    )
    bottom_aligned = area.bottom - 6 <= bottom <= area.bottom + 0.5
    alone_on_top = not above and top < area.top + 40
    assert bottom_aligned or alone_on_top


@needs_chromium
def test_block_before_pagebreak_goes_to_bottom_of_its_page(tmp_path):
    body = ":::task\n!!Nenne!! zwei Beispiele.\n:::\n:::operators:::\n--!\n:::task\nWeiter ohne Operator.\n:::\n"
    page, _top, bottom, area, _above, pages = _build_and_box(tmp_path, body)
    assert pages == 2 and page == 0
    assert area.bottom - 6 <= bottom <= area.bottom + 0.5


@needs_chromium
def test_block_first_on_page_stays_on_top(tmp_path):
    body = ":::task\n!!Nenne!! zwei Beispiele.\n:::\n--!\n:::operators scope=all:::\n:::task\nWeiter ohne Operator.\n:::\n"
    page, top, _bottom, area, above, pages = _build_and_box(tmp_path, body)
    assert pages == 2 and page == 1 and not above
    assert top < area.top + 40


@needs_chromium
def test_exam_legend_a_at_bottom_of_last_page_of_part_a(tmp_path):
    body = ":::task points=2 afb=1\n!!Nenne!! zwei Beispiele.\n:::\n:::operators:::\n--hm\n:::task points=3 afb=2\n!!Beschreibe!! den Ablauf.\n:::\n:::operators:::\n"
    page, _top, bottom, area, _above, pages = _build_and_box(tmp_path, body, document_type="exam")
    assert pages == 2 and page == 0
    assert area.bottom - 6 <= bottom <= area.bottom + 0.5
