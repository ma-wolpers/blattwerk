from app.core.document_diagnostics import inspect_document_text
from app.core.document_types import DOCUMENT_TYPE_KURZENTWURF, DOCUMENT_TYPE_WORKSHEET


def test_inspect_document_text_uses_blattwerk_validator_for_worksheet():
    result = inspect_document_text(
        "---\nTitel: T\nFach: M\nThema: X\n---\n:::lines\n\n:::\n"
    )

    assert result.document_type == DOCUMENT_TYPE_WORKSHEET
    assert any(diag.code == "AN005" for diag in result.diagnostics)


def test_inspect_document_text_uses_kurzentwurf_validator_for_kurzentwurf():
    result = inspect_document_text(
        "---\nStundenthema: Thema\nLerngruppe: 6a\nstart: 08:00\n---\n:::lines\n"
    )

    assert result.document_type == DOCUMENT_TYPE_KURZENTWURF
    assert any(diag.code == "KZF010" for diag in result.diagnostics)
    assert any("Kurzentwurf-DSL" in diag.message for diag in result.diagnostics if diag.code == "KZF010")


def test_inspect_document_text_uses_legacy_kurzentwurf_fallback_for_kwe_path():
    result = inspect_document_text(
        "---\nStundenthema: Thema\n---\n#einstieg t=10\nS> Impuls\n",
        detection_mode="document_type_key",
        source_path="beispiel.kwe.md",
    )

    assert result.document_type == DOCUMENT_TYPE_KURZENTWURF
    assert all(diag.code != "FM001" for diag in result.diagnostics)


def test_inspect_document_text_uses_legacy_kurzentwurf_fallback_for_plain_md():
    result = inspect_document_text(
        "---\nStundenthema: Thema\nLerngruppe: 6a\n---\n#einstieg t=10\nS> Impuls\n",
        detection_mode="document_type_key",
        source_path="beispiel.md",
    )

    assert result.document_type == DOCUMENT_TYPE_KURZENTWURF
    assert all(diag.code != "FM001" for diag in result.diagnostics)


def test_inspect_document_text_recognizes_user_style_plain_md_kurzentwurf():
    result = inspect_document_text(
        "---\n"
        "Stundentyp: Unterricht\n"
        "Dauer: 2\n"
        "Stundenthema: Bist du normal\n"
        "Oberthema: Prozentrechnung\n"
        "Stundenziel: Prozentwerte berechnen\n"
        "Teilziele:\n"
        "Kompetenzen:\n"
        "  - Dreisatz nutzen\n"
        "Material:\n"
        "Unterrichtsbesuch:\n"
        "---\n\n"
        "#einstieg t=5\n",
        detection_mode="document_type_key",
        source_path="lila-5 06-15 Prozentwerte.md",
    )

    assert result.document_type == DOCUMENT_TYPE_KURZENTWURF
    assert all(diag.code != "FM001" for diag in result.diagnostics)


def test_kurzentwurf_implicit_lines_do_not_emit_kzf049_warning():
    result = inspect_document_text(
        "---\n"
        "Stundenthema: Thema\n"
        "Lerngruppe: 6a\n"
        "start: 08:00\n"
        "---\n\n"
        "#einstieg t=10\n"
        "Freitext ohne Marker\n",
    )

    assert result.document_type == DOCUMENT_TYPE_KURZENTWURF
    assert all(diag.code != "KZF049" for diag in result.diagnostics)
