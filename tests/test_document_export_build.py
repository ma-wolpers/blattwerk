from pathlib import Path

from PIL import Image

from app.core.blatt_validator import BuildDiagnostic
from app.core.build_requests import WorksheetBuildRequest, WorksheetDesignOptions
from app.core.document_export_build import (
    export_document_html,
    export_document_pdf,
    export_document_png,
    export_document_png_zip,
)
from app.core.document_types import DOCUMENT_TYPE_KURZENTWURF, DOCUMENT_TYPE_WORKSHEET


def _worksheet_request(tmp_path, diagnostics_out=None):
    source = tmp_path / "source.md"
    source.write_text("---\nTitel: T\nFach: M\nThema: X\n---\n", encoding="utf-8")
    return WorksheetBuildRequest(
        input_path=source,
        output_path=tmp_path / "out.pdf",
        design=WorksheetDesignOptions("indigo", "segoe", "normal"),
        diagnostics_out=diagnostics_out,
    )


def test_export_document_pdf_uses_kurzentwurf_builder(monkeypatch, tmp_path):
    request = _worksheet_request(tmp_path, diagnostics_out=[])
    seen = {}

    class _Diag:
        code = "KZF001"
        severity = "warning"
        message = "Hinweis"
        line = 3

    class _Inspection:
        diagnostics = (_Diag(),)

    monkeypatch.setattr(
        "app.core.document_export_build.export_pdf_from_source",
        lambda source, output_path: (seen.setdefault("path", output_path) or True, _Inspection()),
    )

    out_path = export_document_pdf(
        input_path=request.input_path,
        output_path=tmp_path / "kurzentwurf.pdf",
        document_type=DOCUMENT_TYPE_KURZENTWURF,
        include_solutions=False,
        worksheet_request=request,
    )

    assert out_path.suffix == ".pdf"
    assert Path(seen["path"]) == out_path
    assert request.diagnostics_out[0].code == "KZF001"


def test_export_document_html_writes_kurzentwurf_html(monkeypatch, tmp_path):
    request = _worksheet_request(tmp_path, diagnostics_out=[])

    class _Inspection:
        diagnostics = ()

    monkeypatch.setattr(
        "app.core.document_export_build.render_html_from_source",
        lambda source: ("<html>ok</html>", _Inspection()),
    )

    out_path = export_document_html(
        input_path=request.input_path,
        output_path=tmp_path / "kurzentwurf.html",
        document_type=DOCUMENT_TYPE_KURZENTWURF,
        include_solutions=False,
        worksheet_request=request,
    )

    assert out_path.read_text(encoding="utf-8") == "<html>ok</html>"


def test_export_document_png_creates_numbered_pages(monkeypatch, tmp_path):
    input_path = tmp_path / "source.md"
    input_path.write_text("demo", encoding="utf-8")
    image = Image.new("RGB", (10, 10), color="white")

    monkeypatch.setattr(
        "app.core.document_export_build.build_preview_images_for_document",
        lambda *args, **kwargs: ([image, image.copy()], [BuildDiagnostic(code="PT002", message="warn")]),
    )

    diagnostics = []
    files = export_document_png(
        input_path=input_path,
        output_path=tmp_path / "pages.png",
        document_type=DOCUMENT_TYPE_WORKSHEET,
        include_solutions=False,
        page_format="a4_portrait",
        contrast_profile="standard",
        worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"),
        diagnostics_out=diagnostics,
    )

    assert [path.name for path in files] == ["pages_01.png", "pages_02.png"]
    assert diagnostics[0].code == "PT002"


def test_export_document_png_zip_creates_archive(monkeypatch, tmp_path):
    input_path = tmp_path / "source.md"
    input_path.write_text("demo", encoding="utf-8")
    image = Image.new("RGB", (10, 10), color="white")

    monkeypatch.setattr(
        "app.core.document_export_build.build_preview_images_for_document",
        lambda *args, **kwargs: ([image], []),
    )

    out_path = export_document_png_zip(
        input_path=input_path,
        output_path=tmp_path / "pages.zip",
        document_type=DOCUMENT_TYPE_KURZENTWURF,
        include_solutions=False,
        page_format="a4_portrait",
        contrast_profile="standard",
        worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"),
    )

    assert out_path.exists()
    assert out_path.suffix == ".zip"


def test_export_document_pdf_rejects_kurzentwurf_solution_export(tmp_path):
    request = _worksheet_request(tmp_path)

    try:
        export_document_pdf(
            input_path=request.input_path,
            output_path=tmp_path / "kurzentwurf.pdf",
            document_type=DOCUMENT_TYPE_KURZENTWURF,
            include_solutions=True,
            worksheet_request=request,
        )
    except ValueError as error:
        message = str(error)
    else:
        raise AssertionError("Expected ValueError for kurzentwurf solution export")

    assert "Loesungs" in message