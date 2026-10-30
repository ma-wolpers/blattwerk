"""Der gebundene Render-Job (`render_job`) und das gemeinsame Rastern (`pdf_raster`)."""

from __future__ import annotations

from contextlib import nullcontext

import fitz
import pytest

from app.core.pdf_raster import rasterize_pdf, temp_pdf_path
from app.core.render_job import check_cancelled, commit_section, is_cancelled, run_bound, stage, stage_progress
from app.core.render_stages import RENDER_STAGES, STAGE_PRINT, STAGE_RASTER, STAGE_STAMP, stage_label


class _Cancelled(BaseException):
    """Abbruch wie bei bw-gui: keine `Exception`, damit `except Exception` ihn nicht schluckt."""


class _Context:
    def __init__(self, cancelled=False):
        self.cancelled = cancelled
        self.commits = 0

    def report(self, text, *, fraction=None):
        pass

    def check_cancelled(self):
        if self.cancelled:
            raise _Cancelled()

    def commit(self):
        self.commits += 1
        return nullcontext()


class _Sink:
    def __init__(self):
        self.events = []

    def stage_entered(self, key):
        self.events.append(("in", key))

    def stage_progress(self, fraction):
        self.events.append(("progress", fraction))

    def stage_left(self, key):
        self.events.append(("out", key))


def test_without_a_bound_job_everything_is_a_no_op():
    check_cancelled()
    assert is_cancelled() is False
    with commit_section(), stage(STAGE_PRINT):
        stage_progress(1, 2)


def test_unknown_stage_fails_even_without_a_job():
    with pytest.raises(KeyError):
        with stage("gibt-es-nicht"):
            pass


def test_stage_labels_are_unique_and_complete():
    keys = [item.key for item in RENDER_STAGES]
    assert len(keys) == len(set(keys))
    assert all(stage_label(key) for key in keys)


def test_run_bound_restores_the_previous_binding_after_an_exception():
    with pytest.raises(ValueError):
        run_bound(_Context(cancelled=True), lambda: (_ for _ in ()).throw(ValueError()))
    check_cancelled()


def test_nested_stages_are_reported_in_order_and_left_on_error():
    sink = _Sink()

    def work():
        with stage(STAGE_STAMP):
            with stage(STAGE_PRINT):
                stage_progress(1, 4)
                raise ValueError

    with pytest.raises(ValueError):
        run_bound(None, work, sink=sink)
    assert sink.events == [
        ("in", STAGE_STAMP),
        ("in", STAGE_PRINT),
        ("progress", 0.25),
        ("out", STAGE_PRINT),
        ("out", STAGE_STAMP),
    ]


def test_stage_is_a_checkpoint_and_cancellation_passes_except_exception():
    sink = _Sink()

    def work():
        try:
            with stage(STAGE_PRINT):
                pass
        except Exception:  # wie die Komfort-Rückfälle im Core
            return "geschluckt"
        return "durchgelaufen"

    with pytest.raises(_Cancelled):
        run_bound(_Context(cancelled=True), work, sink=sink)
    assert sink.events == []


def test_commit_section_uses_the_context():
    context = _Context()

    def work():
        with commit_section():
            pass

    run_bound(context, work)
    assert context.commits == 1


def test_rasterize_pdf_reports_each_page_and_cancels_between_pages(tmp_path):
    pdf = tmp_path / "x.pdf"
    document = fitz.open()
    for _ in range(3):
        document.new_page(width=100, height=100)
    document.save(pdf)
    document.close()

    sink = _Sink()
    pages = run_bound(None, lambda: rasterize_pdf(pdf, dpi=72), sink=sink)
    assert [page.size for page in pages] == [(100, 100)] * 3
    assert sink.events[0] == ("in", STAGE_RASTER)
    assert sink.events[-1] == ("out", STAGE_RASTER)
    assert [event[1] for event in sink.events if event[0] == "progress"][-1] == 1.0

    with pytest.raises(_Cancelled):
        run_bound(_Context(cancelled=True), lambda: rasterize_pdf(pdf, dpi=72))


def test_temp_pdf_path_is_removed_even_after_cancellation():
    with pytest.raises(_Cancelled):
        with temp_pdf_path() as path:
            assert path.exists()
            raise _Cancelled()
    assert not path.exists()
