from app.core.blatt_kern_io_html import apply_image_size_options


def test_markdown_image_title_align_center_is_mapped_to_auto_margins():
    html = '<p><img src="x.png" title="w=70% align=center"></p>'

    styled_html = apply_image_size_options(html)

    assert "title=" not in styled_html
    assert "width:70%" in styled_html
    assert "display:block" in styled_html
    assert "margin-left:auto" in styled_html
    assert "margin-right:auto" in styled_html


def test_markdown_image_title_align_right_is_mapped_to_right_alignment():
    html = '<p><img src="x.png" title="w=40% align=right"></p>'

    styled_html = apply_image_size_options(html)

    assert "width:40%" in styled_html
    assert "display:block" in styled_html
    assert "margin-left:auto" in styled_html
    assert "margin-right:0" in styled_html


def test_markdown_image_title_align_block_sets_full_width():
    html = '<p><img src="x.png" title="maxw=50% alignment=block"></p>'

    styled_html = apply_image_size_options(html)

    assert "display:block" in styled_html
    assert "width:100%" in styled_html
    assert "max-width:100%" in styled_html
