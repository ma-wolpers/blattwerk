"""Beide Druckwege liefern dasselbe PDF; der Dauerbrowser ist nach dem ersten Druck schnell."""

from __future__ import annotations

import time

import fitz
import pytest

from app.core.blatt_kern_io_pdf import find_chromium_executable
from app.core.chromium_pipe import pipe_supported
from app.core.mathjax_support import PROFILE_DOCUMENT, mathjax_head, prepare_html_for_print
from app.core.pdf_printers import CommandLinePrinter, DevToolsPrinter

BROWSER = find_chromium_executable()
needs_pipe = pytest.mark.skipif(
    BROWSER is None or not pipe_supported(), reason="kein Chromium oder keine DevTools-Pipe"
)

_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">{head}
<style>
@page {{ size: {size}; margin: 12mm; }}
body {{ font-family: serif; }}
.box {{ background: #cde; border: 2px solid #345; padding: 4mm; }}
.break {{ page-break-after: always; }}
</style></head><body>
<h1>Probe</h1><div class="box">Hintergrund und Rahmen</div>
<p>Formel: $\\mathbb{{R}} \\ni x^2$ und $$\\frac{{a}}{{b}}$$</p><div class="break"></div>
<h2>Zweite Seite</h2><p>Text</p>
</body></html>"""


def _page(tmp_path, size: str) -> str:
    html = prepare_html_for_print(_PAGE.format(head=mathjax_head(PROFILE_DOCUMENT), size=size))
    path = tmp_path / f"probe-{size.replace(' ', '-')}.html"
    path.write_text(html, encoding="utf-8")
    return path.resolve().as_uri()


def _pixels(pdf_path) -> list[tuple[tuple[float, float], bytes]]:
    with fitz.open(pdf_path) as document:
        return [((page.rect.width, page.rect.height), page.get_pixmap(dpi=60).samples) for page in document]


@needs_pipe
@pytest.mark.parametrize("size", ["A4", "A4 landscape"])
def test_devtools_and_command_line_print_identical_pages(tmp_path, size):
    uri = _page(tmp_path, size)
    CommandLinePrinter(BROWSER).print_pdf(uri, str(tmp_path / "cli.pdf"))
    printer = DevToolsPrinter(BROWSER)
    try:
        printer.print_pdf(uri, str(tmp_path / "devtools.pdf"))
    finally:
        printer.close()
    cli_pages, devtools_pages = _pixels(tmp_path / "cli.pdf"), _pixels(tmp_path / "devtools.pdf")
    assert [size for size, _ in devtools_pages] == [size for size, _ in cli_pages]
    assert len(cli_pages) == 2
    for (_, cli), (_, devtools) in zip(cli_pages, devtools_pages):
        assert cli == devtools


@needs_pipe
def test_devtools_printer_is_fast_once_warm(tmp_path):
    """Regression gegen den Grund dieses Wegs: Ohne Formel deutlich unter einer Sekunde."""
    page = tmp_path / "leer.html"
    page.write_text("<!doctype html><p>x</p>", encoding="utf-8")
    printer = DevToolsPrinter(BROWSER)
    try:
        printer.print_pdf(page.as_uri(), str(tmp_path / "warm.pdf"))
        started = time.perf_counter()
        printer.print_pdf(page.as_uri(), str(tmp_path / "out.pdf"))
        elapsed = time.perf_counter() - started
    finally:
        printer.close()
    assert elapsed < 1.0
    with fitz.open(tmp_path / "out.pdf") as document:
        assert "x" in document[0].get_text()


@needs_pipe
def test_closing_ends_the_browser_and_removes_the_profile(tmp_path):
    printer = DevToolsPrinter(BROWSER)
    profile = printer._profile_dir
    process = printer._connection._process
    printer.close()
    assert process.poll() is not None
    assert not profile.exists()
