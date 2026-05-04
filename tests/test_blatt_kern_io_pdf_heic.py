from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from PIL import Image

from app.core.blatt_kern_io_pdf import _rewrite_heic_sources_for_browser_pdf


def _uri_to_path(uri_text: str) -> Path:
    parsed = urlparse(uri_text)
    local_text = url2pathname(parsed.path)
    if len(local_text) >= 3 and local_text[0] in {"/", "\\"} and local_text[2] == ":":
        local_text = local_text[1:]
    return Path(local_text)


def _write_fake_heic(path: Path):
    temp_png = path.with_suffix(".png")
    Image.new("RGB", (4, 4), color=(200, 80, 20)).save(temp_png, format="PNG")
    path.write_bytes(temp_png.read_bytes())
    temp_png.unlink(missing_ok=True)


def test_rewrite_heic_sources_for_browser_pdf_converts_local_heic_uri(tmp_path):
    source_heic = tmp_path / "sample.HEIC"
    _write_fake_heic(source_heic)

    html = f'<p><img src="{source_heic.resolve().as_uri()}" alt="A"></p>'
    rewritten = _rewrite_heic_sources_for_browser_pdf(html, tmp_path)

    assert "sample.HEIC" not in rewritten
    assert "heic_fallback_001.png" in rewritten

    src_start = rewritten.find('src="') + len('src="')
    src_end = rewritten.find('"', src_start)
    converted_uri = rewritten[src_start:src_end]
    converted_path = _uri_to_path(converted_uri)
    assert converted_path.exists()
    assert converted_path.suffix.lower() == ".png"


def test_rewrite_heic_sources_for_browser_pdf_leaves_non_heic_untouched(tmp_path):
    source_png = tmp_path / "sample.png"
    Image.new("RGB", (4, 4), color=(20, 80, 200)).save(source_png, format="PNG")

    html = f'<p><img src="{source_png.resolve().as_uri()}" alt="A"></p>'
    rewritten = _rewrite_heic_sources_for_browser_pdf(html, tmp_path)

    assert rewritten == html
    assert not list(tmp_path.glob("heic_fallback_*.png"))
