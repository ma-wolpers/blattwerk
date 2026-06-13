from app.core.document_types import (
    DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY,
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    build_new_document_content,
    detect_document_type_from_meta,
)
from app.ui.blatt_ui_base import BlattwerkAppBase
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin


def test_detect_document_type_defaults_to_worksheet():
    assert detect_document_type_from_meta({}) == DOCUMENT_TYPE_WORKSHEET


def test_detect_document_type_uses_presentation_mode():
    meta = {"Titel": "T", "Fach": "M", "Thema": "X", "mode": "presentation"}

    assert detect_document_type_from_meta(meta) == DOCUMENT_TYPE_PRESENTATION


def test_detect_document_type_uses_kurzentwurf_yaml_keys_by_default():
    meta = {"Stundenthema": "Algorithmen", "Lerngruppe": "6a", "start": "08:00"}

    assert detect_document_type_from_meta(meta) == DOCUMENT_TYPE_KURZENTWURF


def test_detect_document_type_can_use_explicit_document_type_key():
    meta = {"document_type": "kurzentwurf", "Titel": "Ignoriert"}

    assert (
        detect_document_type_from_meta(
            meta,
            detection_mode=DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY,
        )
        == DOCUMENT_TYPE_KURZENTWURF
    )


def test_build_presentation_template_contains_mode_and_type():
    content = build_new_document_content(DOCUMENT_TYPE_PRESENTATION, {"default_subject": "Mathe"})

    assert "document_type: presentation" in content
    assert "mode: presentation" in content
    assert "Titel: Neue Praesentation" in content


def test_build_kurzentwurf_template_contains_yaml_identity_keys():
    content = build_new_document_content(DOCUMENT_TYPE_KURZENTWURF, {"default_subject": "Informatik"})

    assert "document_type: kurzentwurf" in content
    assert "Stundenthema: Neuer Kurzentwurf" in content
    assert "Lerngruppe: Informatik Klasse eintragen" in content
    assert "#einstieg t=10" in content


class _DummyVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


def test_read_document_type_uses_runtime_detection_mode_setting(tmp_path):
    document = tmp_path / "kurzentwurf.md"
    document.write_text(
        "---\n"
        "Stundenthema: Algorithmen\n"
        "Lerngruppe: 6a\n"
        "start: 08:00\n"
        "---\n",
        encoding="utf-8",
    )

    dummy = type("DummyPreview", (), {"user_preferences": {"document_type_detection_mode": "yaml_keys"}})()

    assert BlattwerkAppPreviewMixin._read_document_type(dummy, document) == DOCUMENT_TYPE_KURZENTWURF


def test_read_document_type_respects_explicit_key_mode(tmp_path):
    document = tmp_path / "kurzentwurf.md"
    document.write_text(
        "---\n"
        "Stundenthema: Algorithmen\n"
        "Lerngruppe: 6a\n"
        "start: 08:00\n"
        "---\n",
        encoding="utf-8",
    )

    dummy = type("DummyPreview", (), {"user_preferences": {"document_type_detection_mode": "document_type_key"}})()

    assert BlattwerkAppPreviewMixin._read_document_type(dummy, document) == DOCUMENT_TYPE_WORKSHEET


def test_build_document_tab_state_forces_worksheet_preview_for_kurzentwurf(tmp_path):
    document = tmp_path / "kurzentwurf.md"
    document.write_text("", encoding="utf-8")

    dummy = type(
        "DummyBase",
        (),
        {
            "_normalize_document_path": staticmethod(BlattwerkAppBase._normalize_document_path),
            "preview_mode_var": _DummyVar("solution"),
            "preview_page_format_var": _DummyVar("a4_portrait"),
            "preview_section_separator_var": _DummyVar("dot"),
            "preview_hide_future_sections_var": _DummyVar(False),
            "preview_contrast_var": _DummyVar("standard"),
            "design_color_profile_var": _DummyVar("indigo"),
            "design_font_profile_var": _DummyVar("segoe"),
            "preview_fit_mode_var": _DummyVar("fit_width"),
            "preview_layout_mode_var": _DummyVar("single"),
            "zoom_percent": 100,
            "current_page_index": 0,
            "_read_document_mode": lambda self, _path: "worksheet",
            "_read_document_type": lambda self, _path: DOCUMENT_TYPE_KURZENTWURF,
        },
    )()

    state = BlattwerkAppBase._build_document_tab_state(dummy, document)

    assert state["document_mode"] == "worksheet"
    assert state["document_type"] == DOCUMENT_TYPE_KURZENTWURF
    assert state["preview_mode"] == "worksheet"