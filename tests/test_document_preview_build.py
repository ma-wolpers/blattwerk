from pathlib import Path

from app.core.blatt_validator import BuildDiagnostic
from app.core.build_requests import WorksheetDesignOptions
from app.core.document_preview_build import build_preview_images_for_document
from app.core.document_types import DOCUMENT_TYPE_KURZENTWURF, DOCUMENT_TYPE_WORKSHEET


def test_preview_dispatch_uses_worksheet_builder(monkeypatch, tmp_path):
    input_path = tmp_path / "blatt.md"
    input_path.write_text("---\nTitel: T\nFach: M\nThema: X\n---\n", encoding="utf-8")

    calls = []

    def _fake_worksheet_builder(path, **kwargs):
        calls.append((path, kwargs))
        return (["worksheet-page"], [BuildDiagnostic(code="PT002", message="warn")])

    monkeypatch.setattr("app.core.document_preview_build._build_worksheet_preview_images", _fake_worksheet_builder)

    pages, diagnostics = build_preview_images_for_document(
        input_path,
        document_type=DOCUMENT_TYPE_WORKSHEET,
        include_solutions=False,
        page_format="a4_portrait",
        contrast_profile="standard",
        worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"),
    )

    assert pages == ["worksheet-page"]
    assert diagnostics[0].code == "PT002"
    assert calls and calls[0][0] == input_path


def test_preview_dispatch_uses_kurzentwurf_builder(monkeypatch, tmp_path):
    input_path = tmp_path / "kurzentwurf.md"
    input_path.write_text("---\nStundenthema: T\nLerngruppe: 6a\nstart: 08:00\n---\n", encoding="utf-8")

    calls = []

    def _fake_kurzentwurf_builder(path, **kwargs):
        calls.append((path, kwargs))
        return (["kurzentwurf-page"], [BuildDiagnostic(code="KZF999", message="ok")])

    monkeypatch.setattr("app.core.document_preview_build._build_kurzentwurf_preview_images", _fake_kurzentwurf_builder)

    pages, diagnostics = build_preview_images_for_document(
        input_path,
        document_type=DOCUMENT_TYPE_KURZENTWURF,
        include_solutions=False,
        page_format="a4_portrait",
        contrast_profile="standard",
        worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"),
        kurzentwurf_options={
            "column_widths_text": "1 2 3 2",
            "page_orientation_mode": "horizontal",
        },
    )

    assert pages == ["kurzentwurf-page"]
    assert diagnostics[0].code == "KZF999"
    assert calls and calls[0][0] == input_path
    forwarded = calls[0][1].get("kurzentwurf_options") or {}
    assert forwarded.get("column_widths_text") == "1 2 3 2"
    assert forwarded.get("page_orientation_mode") == "horizontal"


def test_preview_dispatch_raises_readable_kurzentwurf_error(monkeypatch, tmp_path):
    input_path = tmp_path / "kurzentwurf.md"
    input_path.write_text("broken", encoding="utf-8")

    class _Diag:
        code = "KZF010"
        severity = "error"
        message = "Fehlertext"
        line = 4

    class _Inspection:
        diagnostics = (_Diag(),)
        has_errors = True

    monkeypatch.setattr(
        "app.core.document_preview_build.build_kurzentwerfer_preview_images",
        lambda source, **kwargs: ([], _Inspection()),
    )

    try:
        build_preview_images_for_document(
            input_path,
            document_type=DOCUMENT_TYPE_KURZENTWURF,
            include_solutions=False,
            page_format="a4_portrait",
            contrast_profile="standard",
            worksheet_design=WorksheetDesignOptions("indigo", "segoe", "normal"),
        )
    except ValueError as error:
        message = str(error)
    else:
        raise AssertionError("Expected ValueError for invalid kurzentwurf preview")

    assert "KZF010" in message
    assert "Zeile 4" in message
