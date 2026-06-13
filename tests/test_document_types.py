from app.core.document_types import (
    DOCUMENT_TYPE_DETECTION_EXPLICIT_KEY,
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_PRESENTATION,
    DOCUMENT_TYPE_WORKSHEET,
    build_new_document_content,
    detect_document_type_from_meta,
)


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