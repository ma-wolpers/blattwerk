"""Tests für Typidentität (I1), Konsistenzmarker (I2), Registry und Templates."""

import pytest

from app.core.blatt_kern_shared import split_front_matter
from app.core.document_semantics import (
    Absent,
    Canonical,
    Invalid,
    canonicalize_document_type,
    marker_diagnostics,
    type_for_path,
    type_for_tab,
)
from app.core.document_type_registry import (
    BLATTWERK_EXTENSIONS,
    DOCUMENT_TYPE_EXAM,
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_MARKDOWN,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    KNOWN_DOCUMENT_TYPES,
    has_slide_layout,
    shows_work_hints,
    solutions_renderable,
    spec_for_type,
)
from app.core.document_type_templates import build_new_document_content, get_new_document_dialog_defaults
from app.ui.blatt_ui_base import BlattwerkAppBase
from app.ui.blatt_ui_document_type import BlattwerkDocumentTypeMixin
from app.ui.blatt_ui_preview import BlattwerkAppPreviewMixin


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("blatt.abw", DOCUMENT_TYPE_WORKSHEET),
        ("folien.PBW", DOCUMENT_TYPE_PRESENTATION),
        ("klausur.kbw", DOCUMENT_TYPE_EXAM),
        ("entwurf.ebw", DOCUMENT_TYPE_KURZENTWURF),
        ("notiz.md", DOCUMENT_TYPE_MARKDOWN),
        ("alt.kwe.md", DOCUMENT_TYPE_MARKDOWN),
        ("notiz.txt", None),
        ("ohne_endung", None),
    ],
)
def test_type_comes_only_from_extension(name, expected):
    assert type_for_path(name) == expected


def test_type_for_tab_path_wins_over_cache_and_unknown_uses_explicit_type():
    assert type_for_tab("blatt.abw", DOCUMENT_TYPE_EXAM) == DOCUMENT_TYPE_WORKSHEET
    assert type_for_tab("notiz.txt", DOCUMENT_TYPE_MARKDOWN) == DOCUMENT_TYPE_MARKDOWN
    assert type_for_tab("notiz.txt", None) is None
    assert type_for_tab(None, DOCUMENT_TYPE_PRESENTATION) == DOCUMENT_TYPE_PRESENTATION


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, Absent()),
        ("", Absent()),
        ("   ", Absent()),
        ("worksheet", Canonical(DOCUMENT_TYPE_WORKSHEET)),
        (" Exam ", Canonical(DOCUMENT_TYPE_EXAM)),
        ("arbeitsblatt", Canonical(DOCUMENT_TYPE_WORKSHEET)),
        ("slide_deck", Canonical(DOCUMENT_TYPE_PRESENTATION)),
        ("lesson_plan", Canonical(DOCUMENT_TYPE_KURZENTWURF)),
        ("banana", Invalid("banana")),
        (3, Invalid(3)),
        (True, Invalid(True)),
        (["worksheet"], Invalid(["worksheet"])),
        ({"a": 1}, Invalid({"a": 1})),
    ],
)
def test_canonicalize_document_type(raw, expected):
    assert canonicalize_document_type(raw) == expected


def test_alias_counts_as_matching_marker():
    assert marker_diagnostics({"document_type": "slide_deck"}, DOCUMENT_TYPE_PRESENTATION) == []


def test_registry_capabilities_replace_former_mode_semantics():
    assert has_slide_layout(DOCUMENT_TYPE_PRESENTATION)
    assert not has_slide_layout(DOCUMENT_TYPE_EXAM)
    assert not solutions_renderable(DOCUMENT_TYPE_PRESENTATION)
    assert solutions_renderable(DOCUMENT_TYPE_EXAM)
    assert not shows_work_hints(DOCUMENT_TYPE_EXAM)
    assert shows_work_hints(DOCUMENT_TYPE_WORKSHEET)


def test_registry_extensions_and_ordered_export_formats():
    assert BLATTWERK_EXTENSIONS == (".abw", ".pbw", ".kbw", ".ebw")
    assert spec_for_type(DOCUMENT_TYPE_PRESENTATION).export_formats[-1] == "pptx"
    assert all(isinstance(spec_for_type(t).export_formats, tuple) for t in KNOWN_DOCUMENT_TYPES)


def test_evaluation_capability_only_for_worksheet_and_exam():
    available = {t for t in KNOWN_DOCUMENT_TYPES if spec_for_type(t).evaluation}
    assert available == {DOCUMENT_TYPE_WORKSHEET, DOCUMENT_TYPE_EXAM}


@pytest.mark.parametrize("document_type", KNOWN_DOCUMENT_TYPES)
def test_templates_write_canonical_marker_only_for_blattwerk_types(document_type):
    content = build_new_document_content(document_type, {"default_subject": "Mathe"})
    meta, _rest = split_front_matter(content)

    if spec_for_type(document_type).marker_required:
        assert meta.get("document_type") == document_type
        assert marker_diagnostics(meta, document_type) == []
    else:
        assert "document_type" not in meta
    assert "mode" not in meta


def test_dialog_defaults_use_type_extension():
    for document_type in KNOWN_DOCUMENT_TYPES:
        _title, filename = get_new_document_dialog_defaults(document_type)
        assert type_for_path(filename) == document_type


def test_worksheet_template_ignores_removed_work_emoji_preference():
    content = build_new_document_content(DOCUMENT_TYPE_WORKSHEET, {"default_work_emoji_visible": False})

    assert "mode:" not in content


def test_build_presentation_template_uses_pagebreak_not_framebreak_between_distinct_tasks():
    """Regressionstest: `-+` (Framebreak) baut denselben Gedanken schrittweise auf und ist kein
    Folientrenner -- zwischen den beiden inhaltlich verschiedenen Beispiel-Tasks gehört `--!`."""
    content = build_new_document_content(DOCUMENT_TYPE_PRESENTATION, {})

    assert "\n--!\n" in content
    assert "-+" not in content


def test_build_kurzentwurf_template_contains_yaml_identity_keys():
    content = build_new_document_content(DOCUMENT_TYPE_KURZENTWURF, {"default_subject": "Informatik"})

    assert "document_type: kurzentwurf" in content
    assert "Stundenthema: Neuer Kurzentwurf" in content
    assert "Lerngruppe: Informatik Klasse eintragen" in content
    assert "#einstieg t=10" in content


def test_kurzentwurf_template_validates_without_any_diagnostic():
    """Die Vorlage ist zugleich der Schnellstart in ANLEITUNG_KURZENTWURF.md und wird
    gern als Muster kopiert -- sie darf deshalb auch keine Warnung (z. B. KZF152/KZF154)
    auslösen."""
    from app.core.kurzentwurf_runtime.validator import inspect_kurzentwerfer_text

    content = build_new_document_content(DOCUMENT_TYPE_KURZENTWURF, {})
    result = inspect_kurzentwerfer_text(content)

    assert [(d.code, d.line) for d in result.diagnostics] == []
    assert result.document is not None


def test_removed_preferences_are_dropped_and_have_no_effect():
    from app.storage.user_preferences_adapter import normalize_user_preferences

    normalized = normalize_user_preferences(
        {"document_type_detection_mode": "hybrid", "default_work_emoji_visible": False}
    )

    assert "document_type_detection_mode" not in normalized
    assert "default_work_emoji_visible" not in normalized


class _DummyVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


def test_preview_cache_key_changes_for_kurzentwurf_runtime_options(tmp_path):
    document = tmp_path / "kurzentwurf.ebw"
    document.write_text("---\nStundenthema: T\nLerngruppe: 6a\n---\n", encoding="utf-8")

    dummy = type(
        "DummyPreview",
        (),
        {
            "preview_black_screen_var": _DummyVar("none"),
            "preview_section_separator_var": _DummyVar("dot"),
            "preview_hide_future_sections_var": _DummyVar(False),
            "design_color_profile_var": _DummyVar("indigo"),
            "design_font_profile_var": _DummyVar("segoe"),
            "design_font_size_profile_var": _DummyVar("normal"),
            "_normalize_presentation_section_separator": staticmethod(
                BlattwerkAppPreviewMixin._normalize_presentation_section_separator
            ),
            "_parse_bool_setting": staticmethod(BlattwerkAppPreviewMixin._parse_bool_setting),
            "user_preferences": {"kurzentwurf_column_widths_text": "10 20 60 10"},
        },
    )()

    def key():
        return BlattwerkAppPreviewMixin._build_preview_cache_key(
            dummy, document, False, "a4_portrait", "standard", document_type=DOCUMENT_TYPE_KURZENTWURF
        )

    cache_key_a = key()
    dummy.user_preferences = {"kurzentwurf_column_widths_text": "1 2 3 2"}
    assert cache_key_a != key()


class _TypeDummy(BlattwerkDocumentTypeMixin):
    pass


def test_read_document_type_uses_extension_not_content(tmp_path):
    document = tmp_path / "eigentlich_kurzentwurf.md"
    document.write_text("---\nStundenthema: A\nLerngruppe: 6a\nstart: 08:00\n---\n", encoding="utf-8")

    assert _TypeDummy()._read_document_type(document) == DOCUMENT_TYPE_MARKDOWN


def test_unknown_extension_is_markdown_only_after_explicit_interpretation(tmp_path, monkeypatch):
    document = tmp_path / "notiz.txt"
    document.write_text("Text", encoding="utf-8")
    dummy = _TypeDummy()

    assert dummy._read_document_type(document) is None
    monkeypatch.setattr("app.ui.blatt_ui_document_type.messagebox.askyesno", lambda *a, **k: False)
    assert dummy._confirm_open_unknown_extension(document) is False
    assert dummy._read_document_type(document) is None

    monkeypatch.setattr("app.ui.blatt_ui_document_type.messagebox.askyesno", lambda *a, **k: True)
    assert dummy._confirm_open_unknown_extension(document) is True
    assert dummy._read_document_type(document) == DOCUMENT_TYPE_MARKDOWN
    assert dummy._requires_markdown_save_as(document) is True


def test_known_extension_never_asks(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.ui.blatt_ui_document_type.messagebox.askyesno",
        lambda *a, **k: pytest.fail("darf nicht fragen"),
    )
    assert _TypeDummy()._confirm_open_unknown_extension(tmp_path / "blatt.abw") is True
    assert _TypeDummy()._requires_markdown_save_as(tmp_path / "blatt.abw") is False


def test_build_document_tab_state_forces_worksheet_preview_for_kurzentwurf(tmp_path):
    document = tmp_path / "kurzentwurf.ebw"
    document.write_text("", encoding="utf-8")

    dummy = type(
        "DummyBase",
        (BlattwerkDocumentTypeMixin,),
        {
            "_normalize_document_path": staticmethod(BlattwerkAppBase._normalize_document_path),
            "_font_size_profile_is_per_tab": BlattwerkAppBase._font_size_profile_is_per_tab,
            "preview_mode_var": _DummyVar("solution"),
            "preview_page_format_var": _DummyVar("a4_portrait"),
            "preview_section_separator_var": _DummyVar("dot"),
            "preview_hide_future_sections_var": _DummyVar(False),
            "preview_contrast_var": _DummyVar("standard"),
            "design_color_profile_var": _DummyVar("indigo"),
            "design_font_profile_var": _DummyVar("segoe"),
            "design_font_size_profile_var": _DummyVar("normal"),
            "preview_fit_mode_var": _DummyVar("fit_width"),
            "preview_layout_mode_var": _DummyVar("single"),
            "zoom_percent": 100,
            "current_page_index": 0,
        },
    )()

    state = BlattwerkAppBase._build_document_tab_state(dummy, document)

    assert "document_mode" not in state
    assert state["document_type"] == DOCUMENT_TYPE_KURZENTWURF
    assert state["preview_mode"] == "worksheet"


def test_preview_toolbar_capabilities_follow_registry():
    caps = BlattwerkAppPreviewMixin._preview_toolbar_capabilities

    assert caps(DOCUMENT_TYPE_PRESENTATION)["phase_controls_enabled"] is True
    assert caps(DOCUMENT_TYPE_PRESENTATION)["show_solution_toggle"] is False
    assert caps(DOCUMENT_TYPE_EXAM)["show_solution_toggle"] is True
    assert caps(DOCUMENT_TYPE_MARKDOWN)["show_page_format"] is False
    assert caps(None)["show_design_controls"] is False
