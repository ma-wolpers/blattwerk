"""Real-browser integration test for `extract_slide_elements()`.

Unlike the other editable-PPTX tests (which mock Playwright/the browser
entirely), this one drives an actual installed Chromium-family browser
via Playwright, end to end, against a real Blattwerk-rendered presentation
document -- the only test in the suite that proves the DOM-extraction
mechanism itself (not just the surrounding orchestration/conversion
logic) actually works.

Skips cleanly (not a failure) when either `playwright` isn't installed or
no supported browser is found -- both expected, since Playwright is an
optional dependency (`requirements-editable-pptx.txt`), not something
every dev/CI environment is guaranteed to have. Manually verified once
against real Chrome during implementation (`find_chromium_executable()`
resolved to an installed Chrome, Playwright launched it via
`executable_path`, correctly extracted text -- including text split
around an inline MathJax formula -- and screenshotted a table/QR-style
image block).
"""

from pathlib import Path

import pytest

from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_kern_pptx_export import _slide_size_emu
from app.core.build_requests import WorksheetDesignOptions

try:
    import playwright  # noqa: F401

    _PLAYWRIGHT_INSTALLED = True
except ImportError:
    _PLAYWRIGHT_INSTALLED = False


def _browser_available() -> bool:
    from app.core.blatt_kern_io_pdf import find_chromium_executable

    return bool(find_chromium_executable())


pytestmark = pytest.mark.skipif(
    not _PLAYWRIGHT_INSTALLED,
    reason="playwright nicht installiert (siehe requirements-editable-pptx.txt) -- optionale Abhaengigkeit",
)

_SAMPLE_MARKDOWN = """---
Titel: Testfolien
Fach: Mathematik
Thema: PPTX-Extraktion
mode: presentation
---

# Erste Folie

:::task title="Kernaussage"
Formuliere eine klare Aussage in **einem** Satz zur Funktion $f(x) = x^2$.
:::

:::info type=note
Ein kurzer Hinweistext zum Nachdenken.
:::

-+

:::table
cells:
  - ["A", "B"]
  - ["1", "2"]
:::
"""


@pytest.fixture
def rendered_presentation_html(tmp_path) -> Path:
    if not _browser_available():
        pytest.skip("kein installierter Chromium-Browser gefunden (find_chromium_executable())")

    md_path = tmp_path / "praesentation.md"
    md_path.write_text(_SAMPLE_MARKDOWN, encoding="utf-8")
    html_path = tmp_path / "praesentation.html"
    build_worksheet(
        str(md_path), str(html_path), page_format="presentation_16_9",
        **WorksheetDesignOptions("indigo", "segoe", "normal").as_kwargs(),
    )
    return html_path


def test_extract_slide_elements_finds_two_slides(rendered_presentation_html):
    from app.core.blatt_kern_pptx_export_editable import extract_slide_elements

    width_emu, height_emu = _slide_size_emu("presentation_16_9")
    results = extract_slide_elements(rendered_presentation_html, width_emu, height_emu, mathjax_wait_ms=3000)

    assert len(results) == 2
    assert all(r.elements is not None for r in results)  # Stage A, no fallback needed


def test_extract_slide_elements_captures_full_sentence_around_inline_formula(rendered_presentation_html):
    # Regression for the mixed-content gap found during implementation:
    # plain text nodes sitting next to an <mjx-container> formula inside
    # the same paragraph must not silently vanish.
    from app.core.blatt_kern_pptx_export_editable import extract_slide_elements

    width_emu, height_emu = _slide_size_emu("presentation_16_9")
    results = extract_slide_elements(rendered_presentation_html, width_emu, height_emu, mathjax_wait_ms=3000)

    all_text = " ".join(
        element.text for result in results for element in (result.elements or []) if element.kind == "text"
    )
    assert "Formuliere eine klare Aussage in" in all_text
    assert "einem" in all_text
    assert "Satz zur Funktion" in all_text


def test_extract_slide_elements_table_block_becomes_a_single_image(rendered_presentation_html):
    from app.core.blatt_kern_pptx_export_editable import extract_slide_elements

    width_emu, height_emu = _slide_size_emu("presentation_16_9")
    results = extract_slide_elements(rendered_presentation_html, width_emu, height_emu, mathjax_wait_ms=3000)

    second_slide_images = [el for el in (results[1].elements or []) if el.kind == "image"]
    # Border-bar decoration + the table block itself -- at least one
    # image with non-trivial size (the table), not zero.
    assert any(img.width_emu > 0 and img.height_emu > 0 and img.image_bytes for img in second_slide_images)


def test_extract_slide_elements_positions_stay_within_slide_bounds(rendered_presentation_html):
    from app.core.blatt_kern_pptx_export_editable import extract_slide_elements

    width_emu, height_emu = _slide_size_emu("presentation_16_9")
    results = extract_slide_elements(rendered_presentation_html, width_emu, height_emu, mathjax_wait_ms=3000)

    for result in results:
        for element in result.elements or []:
            assert 0 <= element.left_emu <= width_emu
            assert 0 <= element.top_emu <= height_emu
