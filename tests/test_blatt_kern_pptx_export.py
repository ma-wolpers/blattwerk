from pathlib import Path

import pytest

from app.core.blatt_kern_pptx_export import build_presentation_pptx
from app.core.build_requests import WorksheetDesignOptions


class _StopAfterRequestBuilt(Exception):
    """Bricht den PPTX-Aufbau gezielt ab, sobald die WorksheetBuildRequest erzeugt wurde."""


def test_build_presentation_pptx_forwards_presentation_ignore_framebreaks(monkeypatch, tmp_path):
    input_path = tmp_path / "praesentation.md"
    input_path.write_text("---\nTitel: T\nmode: presentation\n---\n", encoding="utf-8")

    captured_requests = []

    def _fake_build_worksheet_from_request(request):
        captured_requests.append(request)
        raise _StopAfterRequestBuilt()

    monkeypatch.setattr(
        "app.core.blatt_kern_pptx_export.build_worksheet_from_request",
        _fake_build_worksheet_from_request,
    )

    for flag in (True, False):
        captured_requests.clear()
        with pytest.raises(_StopAfterRequestBuilt):
            build_presentation_pptx(
                input_path,
                tmp_path / "out.pptx",
                page_format="presentation_16_9",
                design=WorksheetDesignOptions("indigo", "segoe", "normal"),
                presentation_ignore_framebreaks=flag,
            )
        assert captured_requests[0].presentation_ignore_framebreaks is flag
