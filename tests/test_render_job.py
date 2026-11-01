"""Der Render-Beobachter (`render_job`) und das gemeinsame Rastern (`pdf_raster`)."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.core.pdf_raster import rasterize_pdf, temp_pdf_path
from app.core.render_job import RenderObserver, note_file_dependency, run_observed, stage
from app.core.render_stages import STAGE_PRINT, STAGE_RASTER, STAGE_STAMP


class _Recorder(RenderObserver):
    def __init__(self):
        self.events = []

    def stage_entered(self, key):
        self.events.append(("in", key))

    def stage_left(self, key):
        self.events.append(("out", key))

    def file_dependency(self, path):
        self.events.append(("file", path))


def test_without_an_observer_everything_is_a_no_op():
    note_file_dependency(Path("x.png"))
    with stage(STAGE_PRINT):
        pass


def test_unknown_stage_fails_even_without_an_observer():
    with pytest.raises(KeyError):
        with stage("gibt-es-nicht"):
            pass


def test_observer_is_unbound_after_an_exception():
    recorder = _Recorder()

    def fail():
        raise ValueError

    with pytest.raises(ValueError):
        run_observed(fail, recorder)
    with stage(STAGE_PRINT):
        pass
    assert recorder.events == []


def test_nested_stages_are_reported_in_order_and_left_on_error():
    recorder = _Recorder()

    def work():
        with stage(STAGE_STAMP):
            with stage(STAGE_PRINT):
                note_file_dependency(Path("x.png"))
                raise ValueError

    with pytest.raises(ValueError):
        run_observed(work, recorder)
    assert recorder.events == [
        ("in", STAGE_STAMP),
        ("in", STAGE_PRINT),
        ("file", Path("x.png")),
        ("out", STAGE_PRINT),
        ("out", STAGE_STAMP),
    ]


def test_rasterize_pdf_returns_all_pages_inside_its_stage(tmp_path):
    pdf = tmp_path / "x.pdf"
    document = fitz.open()
    for _ in range(3):
        document.new_page(width=100, height=100)
    document.save(pdf)
    document.close()

    recorder = _Recorder()
    pages = run_observed(lambda: rasterize_pdf(pdf, dpi=72), recorder)
    assert [page.size for page in pages] == [(100, 100)] * 3
    assert recorder.events == [("in", STAGE_RASTER), ("out", STAGE_RASTER)]


def test_temp_pdf_path_is_removed_after_an_exception():
    with pytest.raises(ValueError):
        with temp_pdf_path() as path:
            assert path.exists()
            raise ValueError
    assert not path.exists()
