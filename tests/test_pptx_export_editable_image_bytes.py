"""Tests for B2: preferring a real `<img>`'s original asset bytes over a
screenshot (`_fetch_image_src`/`_resolve_image_bytes`,
`blatt_kern_pptx_export_editable.py`). All Playwright interaction is
faked -- these test the byte-source branching logic itself, not real
browser I/O (covered separately by the real-browser integration test).
"""

import base64

import pytest

from app.core.blatt_kern_pptx_export_editable import _fetch_image_src, _resolve_image_bytes

_ONE_PX_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


class _FakeResponse:
    def __init__(self, body: bytes, ok: bool = True):
        self._body = body
        self.ok = ok

    def body(self) -> bytes:
        return self._body


class _FakeAPIRequestContext:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.requested_urls: list[str] = []

    def get(self, url: str):
        self.requested_urls.append(url)
        return self._response


class _FakePage:
    def __init__(self, *, http_response: _FakeResponse | None = None, screenshot_bytes: bytes | None = None):
        self.request = _FakeAPIRequestContext(http_response or _FakeResponse(_ONE_PX_PNG))
        self._screenshot_bytes = screenshot_bytes
        self.selectors_queried: list[str] = []

    def query_selector(self, selector: str):
        self.selectors_queried.append(selector)
        if self._screenshot_bytes is None:
            return None
        return _FakeElementHandle(self._screenshot_bytes)


class _FakeElementHandle:
    def __init__(self, screenshot_bytes: bytes):
        self._screenshot_bytes = screenshot_bytes

    def screenshot(self) -> bytes:
        return self._screenshot_bytes


def test_fetch_image_src_reads_data_uri_directly():
    data_uri = "data:image/png;base64," + base64.b64encode(_ONE_PX_PNG).decode("ascii")

    result = _fetch_image_src(data_uri, page=_FakePage())

    assert result == _ONE_PX_PNG


def test_fetch_image_src_reads_file_uri_directly(tmp_path):
    image_path = tmp_path / "original.png"
    image_path.write_bytes(_ONE_PX_PNG)

    result = _fetch_image_src(image_path.resolve().as_uri(), page=_FakePage())

    assert result == _ONE_PX_PNG


def test_fetch_image_src_fetches_http_via_playwright_request_context():
    page = _FakePage(http_response=_FakeResponse(_ONE_PX_PNG))

    result = _fetch_image_src("https://example.org/bild.png", page=page)

    assert result == _ONE_PX_PNG
    assert page.request.requested_urls == ["https://example.org/bild.png"]


def test_fetch_image_src_returns_none_for_failed_http_response():
    page = _FakePage(http_response=_FakeResponse(b"", ok=False))

    result = _fetch_image_src("https://example.org/missing.png", page=page)

    assert result is None


def test_fetch_image_src_returns_none_for_unrecognised_scheme():
    assert _fetch_image_src("blob:something", page=_FakePage()) is None


def test_fetch_image_src_raises_oserror_for_missing_file():
    with pytest.raises(OSError):
        _fetch_image_src("file:///this/path/does/not/exist.png", page=_FakePage())


def test_resolve_image_bytes_prefers_original_asset_when_src_present():
    data_uri = "data:image/png;base64," + base64.b64encode(_ONE_PX_PNG).decode("ascii")
    page = _FakePage(screenshot_bytes=b"SCREENSHOT-FALLBACK-BYTES")
    built = {"index": 0, "src": data_uri}

    result = _resolve_image_bytes(built, page)

    assert result == _ONE_PX_PNG
    assert page.selectors_queried == []  # never needed the screenshot path


def test_resolve_image_bytes_falls_back_to_screenshot_without_src():
    page = _FakePage(screenshot_bytes=b"SCREENSHOT-FALLBACK-BYTES")
    built = {"index": 5}  # e.g. MathJax/SVG/chrome/table -- no `src` at all

    result = _resolve_image_bytes(built, page)

    assert result == b"SCREENSHOT-FALLBACK-BYTES"
    assert page.selectors_queried == ['[data-pptx-index="5"]']


def test_resolve_image_bytes_falls_back_to_screenshot_when_original_fetch_fails():
    # An expected, infrastructure-level failure (missing local file) must
    # degrade to the screenshot fallback for just this image, not raise.
    page = _FakePage(screenshot_bytes=b"SCREENSHOT-FALLBACK-BYTES")
    built = {"index": 2, "src": "file:///this/path/does/not/exist.png"}

    result = _resolve_image_bytes(built, page)

    assert result == b"SCREENSHOT-FALLBACK-BYTES"


def test_resolve_image_bytes_returns_none_when_neither_source_available():
    page = _FakePage(screenshot_bytes=None)
    built = {"index": 9}

    assert _resolve_image_bytes(built, page) is None
