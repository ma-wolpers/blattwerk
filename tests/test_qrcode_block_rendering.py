from app.core.blatt_kern_io_html import apply_image_size_options
from app.core.blatt_kern_task_render import render_block


def test_qrcode_block_renders_clickable_anchor_with_href():
    html = render_block(
        "qrcode",
        {"url": "https://example.org"},
        "",
        include_solutions=False,
        document_mode="ws",
    )

    assert "class='qrcode-link'" in html
    assert "href='https://example.org'" in html
    assert "<img" in html


def test_qrcode_block_size_options_are_mapped_via_image_post_processing():
    html = render_block(
        "qrcode",
        {
            "url": "https://example.org",
            "w": "3cm",
            "h": "2cm",
            "maxw": "45%",
        },
        "",
        include_solutions=False,
        document_mode="ws",
    )

    styled_html = apply_image_size_options(html)

    assert "title=" not in styled_html
    assert "style=\"" in styled_html
    assert "width:3cm" in styled_html
    assert "height:2cm" in styled_html
    assert "max-width:45%" in styled_html


def test_qrcode_block_rejects_invalid_url_in_renderer_output():
    html = render_block(
        "qrcode",
        {"url": "javascript:alert(1)"},
        "",
        include_solutions=False,
        document_mode="ws",
    )

    assert "qrcode-invalid" in html
    assert "qrcode-link" not in html


def test_qrcode_block_supports_object_align_wrapper():
    html = render_block(
        "qrcode",
        {"url": "https://example.org", "align": "right"},
        "",
        include_solutions=False,
        document_mode="ws",
    )

    assert "bw-object-align bw-object-align-right" in html


def test_qrcode_block_supports_alignment_alias_wrapper():
    html = render_block(
        "qrcode",
        {"url": "https://example.org", "alignment": "center"},
        "",
        include_solutions=False,
        document_mode="ws",
    )

    assert "bw-object-align bw-object-align-center" in html
