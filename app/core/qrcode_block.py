"""QR code block rendering helpers."""

from __future__ import annotations

import base64
import io
import re
from html import escape
from urllib.parse import urlparse


_CSS_SIZE_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?(?:px|%|cm|mm|in|pt|em|rem|vw|vh|vmin|vmax)?|auto)",
    flags=re.IGNORECASE,
)


def _is_valid_css_size(value):
    text = str(value or "").strip()
    if not text:
        return False
    return bool(_CSS_SIZE_PATTERN.fullmatch(text))


def _is_valid_qrcode_url(url):
    text = str(url or "").strip()
    if not text or any(character.isspace() for character in text):
        return False

    parsed = urlparse(text)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)

    if parsed.scheme:
        return False

    return not text.startswith("//")


def _pick_size_value(options, primary_key, alias_key):
    value = str((options or {}).get(primary_key, "")).strip()
    if value:
        return value
    return str((options or {}).get(alias_key, "")).strip()


def _build_image_title_options(options):
    width = _pick_size_value(options, "w", "width")
    height = _pick_size_value(options, "h", "height")
    max_width = _pick_size_value(options, "maxw", "max-width")

    title_tokens = []
    if width and _is_valid_css_size(width):
        title_tokens.append(f"w={width}")
    if height and _is_valid_css_size(height):
        title_tokens.append(f"h={height}")
    if max_width and _is_valid_css_size(max_width):
        title_tokens.append(f"maxw={max_width}")

    return " ".join(title_tokens)


def _build_qrcode_data_uri(url):
    try:
        import qrcode
    except Exception:
        return ""

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_qrcode_block(options):
    """Render a clickable QR code block as HTML."""
    url = str((options or {}).get("url", "")).strip()
    if not _is_valid_qrcode_url(url):
        return "<div class='qrcode qrcode-invalid'>Ungueltiger QR-Link.</div>"

    image_src = _build_qrcode_data_uri(url)
    if not image_src:
        return "<div class='qrcode qrcode-invalid'>QR-Bibliothek nicht verfuegbar.</div>"

    href = escape(url, quote=True)
    title_options = _build_image_title_options(options)
    title_attr = ""
    if title_options:
        title_attr = f' title="{escape(title_options, quote=True)}"'

    return (
        "<div class='qrcode'>"
        f"<a class='qrcode-link' href='{href}' target='_blank' rel='noopener noreferrer'>"
        f"<img alt='QR-Code' src='{image_src}'{title_attr}></a>"
        "</div>"
    )
