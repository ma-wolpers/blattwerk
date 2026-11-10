"""MathJax an einer Stelle (`mathjax_support`): Druckvorbereitung und Setzen ohne Internet."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.core import pdf_printers, print_service
from app.core.blatt_kern_io_build import build_worksheet
from app.core.blatt_kern_io_pdf import find_chromium_executable, write_pdf_from_html
from app.core.mathjax_support import (
    ASSET_DIR,
    MATHJAX_VERSION,
    PROFILE_DOCUMENT,
    PROFILE_KURZENTWURF,
    PROFILE_PLAIN,
    body_contains_math,
    mathjax_head,
    prepare_html_for_print,
)

needs_chromium = pytest.mark.skipif(find_chromium_executable() is None, reason="kein Chromium installiert")

CDN_URL = f"https://cdn.jsdelivr.net/npm/mathjax@{MATHJAX_VERSION}/tex-svg.js"


def _page(body: str, profile: str = PROFILE_DOCUMENT) -> str:
    return f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">{mathjax_head(profile)}</head><body>{body}</body></html>'


@pytest.mark.parametrize("profile", [PROFILE_DOCUMENT, PROFILE_PLAIN, PROFILE_KURZENTWURF])
def test_every_profile_links_the_pinned_version(profile):
    assert CDN_URL in mathjax_head(profile)


def test_unknown_profile_fails():
    with pytest.raises(KeyError):
        mathjax_head("gibt-es-nicht")


@pytest.mark.parametrize(
    "body",
    ["$x$", "$$x$$", "Preis 5 $", r"\begin{align}x\end{align}", r"\ref{a}", r"\eqref{a}"],
)
def test_math_tokens_in_the_body_count(body):
    assert body_contains_math(_page(body))


def test_head_alone_is_no_math():
    assert "$" in mathjax_head(PROFILE_DOCUMENT)
    assert not body_contains_math(_page("Nur Text."))


def test_print_without_math_drops_the_script():
    printed = prepare_html_for_print(_page("Nur Text."))
    assert "tex-svg.js" not in printed


def test_print_with_math_uses_the_local_package_with_local_fonts():
    printed = prepare_html_for_print(_page("$x$"))
    assert CDN_URL not in printed
    assert (ASSET_DIR / "mathjax" / "tex-svg.js").as_uri() in printed
    assert (ASSET_DIR / "@mathjax").as_uri() in printed


def test_print_falls_back_to_the_cdn_without_local_package(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.mathjax_support._LOCAL_SCRIPT", tmp_path / "fehlt.js")
    assert CDN_URL in prepare_html_for_print(_page("$x$"))


def test_page_without_tag_stays_unchanged():
    html = "<html><head></head><body>$x$</body></html>"
    assert prepare_html_for_print(html) == html


def test_html_export_keeps_the_portable_cdn_link(tmp_path):
    source = tmp_path / "blatt.abw"
    source.write_text("---\nTitel: T\nFach: M\nThema: X\n---\n:::task\n$x^2$\n:::\n", encoding="utf-8")
    html = Path(build_worksheet(source, tmp_path / "blatt.html")).read_text(encoding="utf-8")
    assert CDN_URL in html
    assert "file:" not in html.split("<style>", 1)[0]


def test_vendored_package_matches_the_pinned_version():
    assert (ASSET_DIR / "VERSION.txt").read_text(encoding="utf-8").strip() == MATHJAX_VERSION
    assert (ASSET_DIR / "mathjax" / "LICENSE").exists()
    assert (ASSET_DIR / "@mathjax" / "mathjax-newcm-font" / "LICENSE").exists()
    assert (ASSET_DIR / "@mathjax" / "mathjax-newcm-font" / "svg" / "dynamic" / "double-struck.js").exists()


FORMULAS = [
    r"$x^2 + \frac{1}{2}$",
    r"$\boldsymbol{v} = \vec{a}$",
    r"$\begin{pmatrix}1&2\\3&4\end{pmatrix}$",
    r"$\mathbb{R}\cup\emptyset$",
    r"$\mathcal{L}$",
    r"$\overline{AB}\perp\angle\alpha$",
]


@needs_chromium
@pytest.mark.parametrize("profile", [PROFILE_DOCUMENT, PROFILE_PLAIN, PROFILE_KURZENTWURF])
def test_formulas_are_typeset_without_internet(monkeypatch, tmp_path, profile):
    """Regression: `\\mathbb` holte Schriftteile vom CDN und ließ die ganze Seite roh."""
    original = pdf_printers.browser_flags

    def offline(profile_dir):
        return [*original(profile_dir), "--host-resolver-rules=MAP * ~NOTFOUND"]

    monkeypatch.setattr(pdf_printers, "browser_flags", offline)
    # Ein frischer Dienst, damit der Dauerbrowser mit den Offline-Schaltern startet.
    previous = print_service.replace_default_print_service(None)
    try:
        pdf = write_pdf_from_html(_page(" ".join(FORMULAS), profile), tmp_path / "out.pdf")
    finally:
        print_service.shutdown_default_print_service()
        print_service.replace_default_print_service(previous)
    with fitz.open(pdf) as document:
        text = "".join(page.get_text() for page in document)
    assert "$" not in text and "\\" not in text
