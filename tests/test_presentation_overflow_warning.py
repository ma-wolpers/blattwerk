from pathlib import Path

import fitz

from app.core import blatt_kern_io_build as io_build


def _presentation_doc() -> str:
    return (
        "---\n"
        "Titel: Overflow Test\n"
        "Fach: Informatik\n"
        "Thema: Warnung\n"
        "mode: presentation\n"
        "presentation_layout: presentation_16_9\n"
        "---\n"
        "## Slide\n"
        "Kurzer Inhalt\n"
    )


def _write_pdf_with_pages(path: Path, page_count: int) -> Path:
    doc = fitz.open()
    try:
        for _ in range(max(1, int(page_count))):
            doc.new_page(width=1280, height=720)
        doc.save(path)
    finally:
        doc.close()
    return path


def test_presentation_pdf_overflow_emits_pt002_warning(tmp_path, monkeypatch):
    md_path = tmp_path / "doc.md"
    out_path = tmp_path / "out.pdf"
    md_path.write_text(_presentation_doc(), encoding="utf-8")

    monkeypatch.setattr(
        io_build,
        "write_pdf_from_html",
        lambda html, target: _write_pdf_with_pages(Path(target), page_count=2),
    )

    diagnostics = []
    io_build.build_worksheet(
        md_path,
        out_path,
        page_format="presentation_16_9",
        diagnostics_out=diagnostics,
    )

    codes = [diag.code for diag in diagnostics]
    assert "PT002" in codes


def test_presentation_pdf_without_overflow_has_no_pt002(tmp_path, monkeypatch):
    md_path = tmp_path / "doc.md"
    out_path = tmp_path / "out.pdf"
    md_path.write_text(_presentation_doc(), encoding="utf-8")

    monkeypatch.setattr(
        io_build,
        "write_pdf_from_html",
        lambda html, target: _write_pdf_with_pages(Path(target), page_count=1),
    )

    diagnostics = []
    io_build.build_worksheet(
        md_path,
        out_path,
        page_format="presentation_16_9",
        diagnostics_out=diagnostics,
    )

    codes = [diag.code for diag in diagnostics]
    assert "PT002" not in codes