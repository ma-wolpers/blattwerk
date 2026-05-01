from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin


class _DummyPreview(BlattwerkAppPreviewMixin):
    pass


def test_preview_page_format_memory_is_separate_for_mode_families():
    dummy = _DummyPreview()
    dummy._last_preview_page_format_by_mode = {
        "worksheet": "a4_portrait",
        "presentation": "presentation_16_9",
    }

    assert dummy._resolve_preview_page_format_for_document_mode("a5_landscape", "worksheet") == "a5_landscape"
    assert dummy._resolve_preview_page_format_for_document_mode("presentation_4_3", "presentation") == "presentation_4_3"

    # Invalid candidate for worksheet falls back to remembered worksheet format.
    assert dummy._resolve_preview_page_format_for_document_mode("presentation_16_10", "worksheet") == "a5_landscape"

    # Invalid candidate for presentation falls back to remembered presentation format.
    assert dummy._resolve_preview_page_format_for_document_mode("a4_portrait", "presentation") == "presentation_4_3"


def test_preview_page_format_memory_uses_mode_defaults_when_empty():
    dummy = _DummyPreview()
    dummy._last_preview_page_format_by_mode = {}

    assert dummy._resolve_preview_page_format_for_document_mode("", "worksheet") == "a4_portrait"
    assert dummy._resolve_preview_page_format_for_document_mode("", "presentation") == "presentation_16_9"
