"""Tests für den Dokumenttyp Schilder (`.sbw`): Parser, HTML, Validator, Dispatch, Fit."""

from pathlib import Path

import fitz
import pytest

from app.core.blatt_kern_io_pdf import find_chromium_executable
from app.core.build_requests import WorksheetBuildRequest, WorksheetDesignOptions
from app.core.document_diagnostics import inspect_document_text
from app.core.document_export_build import export_document_html, export_document_pdf
from app.core.document_preview_build import build_preview_images_for_document
from app.core.document_type_registry import DOCUMENT_TYPE_SCHILD
from app.core.document_type_templates import build_new_document_content
from app.core.schild_render import build_schild, parse_schild, render_schild_html
from app.core.schild_validator import inspect_schild_text

HEAD = "---\ndocument_type: schild\n{extra}---\n"


def _doc(body: str, extra: str = "") -> str:
    """Baut ein `.sbw`-Dokument mit Marker und optionalen Frontmatter-Zeilen."""
    return HEAD.format(extra=extra) + body


# -- Parser ------------------------------------------------------------------------


def test_parse_splits_on_separator_and_keeps_inner_line_breaks():
    doc = parse_schild(_doc("\nZweckbindung\n\n---\n\nTreu und\nGlauben\n---\nC\n"))
    assert [s.text for s in doc.schilder] == ["Zweckbindung", "Treu und\nGlauben", "C"]
    assert doc.schilder[0].line_number == 5  # Zeile im Gesamtdokument (4 ist die Leerzeile)
    assert doc.empty_segment_lines == ()


def test_frontmatter_fence_is_not_a_sign_separator():
    doc = parse_schild("---\nTitel: T\n---\nNur eins\n")
    assert [s.text for s in doc.schilder] == ["Nur eins"]


def test_empty_segments_are_skipped_and_reported_by_line():
    doc = parse_schild(_doc("A\n---\n\n---\nB\n---\n"))
    assert [s.text for s in doc.schilder] == ["A", "B"]
    assert doc.empty_segment_lines == (5, 9)


def test_options_defaults_and_values():
    assert parse_schild(_doc("A")).options.ausrichtung == "hoch"
    options = parse_schild(_doc("A", "ausrichtung: quer\nfett: nein\nrand: 7,5\nschriftgroesse: maximal\n")).options
    assert (options.ausrichtung, options.fett, options.rand_mm, options.schriftgroesse) == ("quer", False, 7.5, "maximal")


def test_invalid_options_fall_back_to_defaults():
    options = parse_schild(_doc("A", "ausrichtung: schräg\nfett: vielleicht\nrand: 500\nschriftgroesse: riesig\n")).options
    assert (options.ausrichtung, options.fett, options.rand_mm, options.schriftgroesse) == ("hoch", True, 15.0, "einheitlich")


# -- HTML --------------------------------------------------------------------------


def test_html_has_one_section_per_sign_and_escapes_text():
    html = render_schild_html(_doc("a < b\n---\nZwei\nZeilen\n"))
    assert html.count('<section class="schild">') == 2
    assert "a &lt; b" in html
    assert "Zwei<br>Zeilen" in html


def test_html_page_geometry_and_weight_follow_options():
    portrait = render_schild_html(_doc("A"))
    landscape = render_schild_html(_doc("A", "ausrichtung: quer\nfett: nein\nrand: 20\n"))
    assert "size: A4 portrait" in portrait and "width: 210mm; height: 297mm" in portrait
    assert "font-weight: bold" in portrait
    assert "size: A4 landscape" in landscape and "width: 297mm; height: 210mm" in landscape
    assert "padding: 20mm" in landscape and "font-weight: normal" in landscape


def test_fit_script_mode_follows_schriftgroesse():
    assert "var uniform = true;" in render_schild_html(_doc("A"))
    assert "var uniform = false;" in render_schild_html(_doc("A", "schriftgroesse: maximal\n"))


# -- Validator ---------------------------------------------------------------------


def test_validator_codes():
    assert [d.code for d in inspect_schild_text(_doc("A\n---\nB\n"))] == []
    assert [d.code for d in inspect_schild_text(_doc("\n"))] == ["SBW001"]
    empty = inspect_schild_text(_doc("A\n---\n---\nB\n"))
    assert [(d.code, d.line_number) for d in empty] == [("SBW002", 5)]
    bad = inspect_schild_text(_doc("A", "ausrichtung: schräg\nrand: x\n"))
    assert [d.code for d in bad] == ["SBW003", "SBW003"]


def test_document_diagnostics_dispatches_to_schild_validator():
    result = inspect_document_text(_doc("\n"), document_type=DOCUMENT_TYPE_SCHILD)
    assert "SBW001" in [d.code for d in result.diagnostics]


def test_new_document_template_is_valid():
    text = build_new_document_content(DOCUMENT_TYPE_SCHILD, {})
    assert inspect_document_text(text, document_type=DOCUMENT_TYPE_SCHILD).diagnostics == ()
    assert len(parse_schild(text).schilder) == 2


# -- Dispatch (PDF-Erzeugung gestubbt) ---------------------------------------------


def _fake_pdf_writer(calls):
    """Ersatz für `write_pdf_from_html`: merkt das HTML, schreibt eine 1-Seiten-PDF."""

    def _write(html, target):
        calls.append(html)
        doc = fitz.open()
        doc.new_page()
        doc.save(str(target))
        return Path(target)

    return _write


def _request(tmp_path) -> WorksheetBuildRequest:
    """Minimaler Worksheet-Request; die Schilder-Pipeline darf ihn nicht nutzen."""
    return WorksheetBuildRequest(input_path=tmp_path / "x.sbw", output_path=tmp_path / "x.pdf")


def test_preview_and_exports_use_schild_pipeline(monkeypatch, tmp_path):
    calls: list[str] = []
    monkeypatch.setattr("app.core.schild_render.write_pdf_from_html", _fake_pdf_writer(calls))
    source = tmp_path / "x.sbw"
    source.write_text(_doc("Zweckbindung\n"), encoding="utf-8")

    pages, diagnostics = build_preview_images_for_document(
        source,
        document_type=DOCUMENT_TYPE_SCHILD,
        include_solutions=False,
        page_format="a4_portrait",
        contrast_profile="standard",
        worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"),
    )
    assert len(pages) == 1 and diagnostics == []

    pdf = export_document_pdf(input_path=source, output_path=tmp_path / "out", document_type=DOCUMENT_TYPE_SCHILD,
                              include_solutions=False, worksheet_request=_request(tmp_path))
    html = export_document_html(input_path=source, output_path=tmp_path / "out", document_type=DOCUMENT_TYPE_SCHILD,
                                include_solutions=False, worksheet_request=_request(tmp_path))
    assert pdf.suffix == ".pdf" and pdf.exists()
    assert html.suffix == ".html" and 'class="schild"' in html.read_text(encoding="utf-8")
    assert len(calls) == 2 and all("Zweckbindung" in c for c in calls)


# -- Integration (echtes Chromium) -------------------------------------------------

needs_chromium = pytest.mark.skipif(find_chromium_executable() is None, reason="kein Chromium-Browser installiert")
LONG = "Rechtmäßigkeit, Verarbeitung nach Treu und Glauben, Transparenz"
MM = 72 / 25.4


def _span_sizes(page) -> list[tuple[float, fitz.Rect]]:
    """Alle Text-Spans einer PDF-Seite als (Schriftgröße, Bounding-Box)."""
    return [
        (span["size"], fitz.Rect(span["bbox"]))
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if span["text"].strip()
    ]


def _build_pdf(tmp_path, extra=""):
    """Baut drei Schilder als echte PDF und liefert das geöffnete Dokument."""
    source = tmp_path / "s.sbw"
    source.write_text(_doc(f"Zweckbindung\n---\nRechenschaftspflicht\n---\n{LONG}\n", extra), encoding="utf-8")
    return fitz.open(build_schild(source, tmp_path / "s.pdf"))


@needs_chromium
def test_uniform_signs_share_one_size_and_stay_inside_margins(tmp_path):
    doc = _build_pdf(tmp_path)
    assert len(doc) == 3
    sizes = set()
    for page in doc:
        assert round(page.rect.width) == 595 and round(page.rect.height) == 842
        usable = fitz.Rect(15 * MM, 15 * MM, page.rect.width - 15 * MM, page.rect.height - 15 * MM)
        for size, box in _span_sizes(page):
            sizes.add(round(size, 1))
            assert usable + (-1, -1, 1, 1) & box == box  # 1pt Toleranz für Rundung
    assert len(sizes) == 1
    # Das breiteste Wort bestimmt die Größe und füllt die Nutzbreite fast ganz.
    widest = _span_sizes(doc[1])[0][1].width
    assert widest >= 0.85 * (595 - 30 * MM)


@needs_chromium
def test_maximal_sizes_each_sign_and_landscape_turns_page(tmp_path):
    doc = _build_pdf(tmp_path, "ausrichtung: quer\nschriftgroesse: maximal\n")
    assert round(doc[0].rect.width) == 842
    short = _span_sizes(doc[0])[0][0]
    long = _span_sizes(doc[2])[0][0]
    assert short > long
