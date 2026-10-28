"""Lernhilfen-Anhang hinter den Arbeitsblattseiten (Vertrag, Anhängen, Durchreichung)."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

import app.core.document_preview_build as preview_module
from app.core.build_requests import WorksheetBuildRequest
from app.core.document_type_registry import (
    DOCUMENT_TYPE_EXAM,
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
)
from app.core.help_cards_appendix import (
    HELP_APPENDIX_MODES,
    HELP_APPENDIX_NONE,
    HELP_APPENDIX_SHEET,
    HELP_APPENDIX_SINGLE,
    append_help_cards_appendix,
    coerce_help_appendix,
    ensure_help_appendix_request,
    help_appendix_label,
    help_appendix_supported,
)
from help_card_fakes import fake_help_card_render

META = {"Titel": "T"}
TWO_CARDS = [("task", {}, "Aufgabe"), ("help", {"title": "A"}, "Eins"), ("help", {"title": "B"}, "Zwei")]
DESIGN = {"print_profile": "standard", "color_profile": "indigo", "font_profile": "segoe", "font_size_profile": "normal"}


def _worksheet_pdf(path: Path, pages: int = 2) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=595, height=842)
    doc.save(path)
    doc.close()
    return path


def test_supported_only_for_worksheet_pipeline_without_slides():
    assert help_appendix_supported(DOCUMENT_TYPE_WORKSHEET)
    assert help_appendix_supported(DOCUMENT_TYPE_EXAM)
    assert not help_appendix_supported(DOCUMENT_TYPE_PRESENTATION)
    assert not help_appendix_supported(DOCUMENT_TYPE_KURZENTWURF)
    assert not help_appendix_supported("unbekannt")
    assert not help_appendix_supported(None)


@pytest.mark.parametrize(
    ("mode", "document_type", "suffix"),
    [
        ("grid", DOCUMENT_TYPE_WORKSHEET, ".pdf"),
        (HELP_APPENDIX_SHEET, DOCUMENT_TYPE_WORKSHEET, ".html"),
        (HELP_APPENDIX_SINGLE, DOCUMENT_TYPE_PRESENTATION, ".pdf"),
    ],
)
def test_contract_rejects_invalid_combinations(mode, document_type, suffix):
    with pytest.raises(ValueError):
        ensure_help_appendix_request(mode, document_type=document_type, output_suffix=suffix)


def test_contract_accepts_none_everywhere():
    ensure_help_appendix_request(HELP_APPENDIX_NONE, document_type=DOCUMENT_TYPE_PRESENTATION, output_suffix=".html")


def test_labels_and_coercion():
    assert all(help_appendix_label(mode, short=True) for mode in HELP_APPENDIX_MODES)
    assert help_appendix_label(HELP_APPENDIX_SHEET, short=False) == "Alle Lernhilfen auf einer Seite"
    assert help_appendix_label(HELP_APPENDIX_SINGLE, short=False) == "Jede Lernhilfe auf eigener Seite"
    assert coerce_help_appendix("kaputt") == HELP_APPENDIX_NONE
    assert coerce_help_appendix(HELP_APPENDIX_SINGLE) == HELP_APPENDIX_SINGLE


def test_sheet_appendix_adds_pages_in_worksheet_format(tmp_path):
    pdf = _worksheet_pdf(tmp_path / "blatt.pdf")

    added = append_help_cards_appendix(
        pdf, mode=HELP_APPENDIX_SHEET, md_dir=tmp_path, meta=META, blocks=TWO_CARDS,
        include_solutions=False, page_format="a4_portrait", render=fake_help_card_render(), **DESIGN,
    )

    assert added == 2  # Fake druckt eine Seite je Karte
    with fitz.open(pdf) as doc:
        assert doc.page_count == 4
        assert doc[2].rect.width == pytest.approx(595)


def test_single_appendix_uses_small_formats_after_worksheet(tmp_path):
    pdf = _worksheet_pdf(tmp_path / "blatt.pdf")

    append_help_cards_appendix(
        pdf, mode=HELP_APPENDIX_SINGLE, md_dir=tmp_path, meta=META, blocks=TWO_CARDS,
        include_solutions=False, page_format="a4_portrait",
        render=fake_help_card_render({2: {"a6_portrait": 2}}), **DESIGN,
    )

    with fitz.open(pdf) as doc:
        assert [round(page.rect.width) for page in doc] == [595, 595, 298, 420]
        text = "".join(page.get_text() for page in doc)
        assert text.index("Kartentext 1") < text.index("Kartentext 2")
        assert "BWHC-" not in text


def test_no_visible_cards_leaves_pdf_untouched(tmp_path):
    pdf = _worksheet_pdf(tmp_path / "blatt.pdf")
    before = pdf.read_bytes()

    added = append_help_cards_appendix(
        pdf, mode=HELP_APPENDIX_SINGLE, md_dir=tmp_path, meta=META, blocks=[("task", {}, "Aufgabe")],
        include_solutions=False, page_format="a4_portrait", render=fake_help_card_render(), **DESIGN,
    )

    assert added == 0
    assert pdf.read_bytes() == before


def test_request_default_is_none():
    assert WorksheetBuildRequest(input_path=Path("a"), output_path=Path("b")).help_appendix == HELP_APPENDIX_NONE


def test_preview_build_passes_appendix_to_worksheet_request(monkeypatch, tmp_path):
    seen = {}

    def _fake_build(request):
        seen["help_appendix"] = request.help_appendix
        _worksheet_pdf(Path(request.output_path), pages=1)

    monkeypatch.setattr(preview_module, "build_worksheet_from_request", _fake_build)
    from app.core.build_requests import WorksheetDesignOptions

    images, _diagnostics = preview_module.build_preview_images_for_document(
        tmp_path / "blatt.abw", document_type=DOCUMENT_TYPE_WORKSHEET, include_solutions=False,
        page_format="a4_portrait", contrast_profile="standard",
        worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"), help_appendix=HELP_APPENDIX_SINGLE,
    )

    assert seen["help_appendix"] == HELP_APPENDIX_SINGLE
    assert len(images) == 1


def test_build_worksheet_rejects_appendix_for_html(tmp_path):
    from app.core.blatt_kern_io_build import build_worksheet

    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: T\n---\n:::help\nx\n:::\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_worksheet(source, tmp_path / "blatt.html", help_appendix=HELP_APPENDIX_SHEET)


def test_real_worksheet_pdf_gets_a6_appendix_after_a4_pages(tmp_path):
    """End-to-end mit Chromium: A4-Arbeitsblatt, danach eine A6-Lernhilfe."""
    from app.core.blatt_kern_io_build import build_worksheet
    from app.core.blatt_kern_io_pdf import find_chromium_executable

    if find_chromium_executable() is None:
        pytest.skip("kein Chromium-Browser fuer den PDF-Druck")
    source = tmp_path / "blatt.abw"
    source.write_text(
        "---\nTitel: Anhang\nFach: M\nThema: T\n---\n:::task\nAufgabe\n:::\n:::help title=\"Tipp\"\nKurz.\n:::\n",
        encoding="utf-8",
    )
    out = tmp_path / "blatt.pdf"

    build_worksheet(source, out, block_on_critical=False, help_appendix=HELP_APPENDIX_SINGLE)

    with fitz.open(out) as doc:
        assert doc[0].rect.width == pytest.approx(595, abs=2)
        assert doc[doc.page_count - 1].rect.width == pytest.approx(298, abs=2)
        assert "Tipp" in doc[doc.page_count - 1].get_text()
