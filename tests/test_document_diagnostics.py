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
