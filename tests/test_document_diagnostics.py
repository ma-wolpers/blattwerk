"""Tests für die typabhängige Diagnose (Marker + passender Validator)."""

import pytest

from app.core.document_diagnostics import inspect_document_path, inspect_document_text
from app.core.document_type_registry import (
    DOCUMENT_TYPE_KURZENTWURF,
    DOCUMENT_TYPE_MARKDOWN,
    DOCUMENT_TYPE_WORKSHEET,
)


def _codes(result):
    return [diag.code for diag in result.diagnostics]


def test_worksheet_uses_blattwerk_validator():
    result = inspect_document_text(
        "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n:::lines\n\n:::\n",
        document_type=DOCUMENT_TYPE_WORKSHEET,
    )

    assert result.document_type == DOCUMENT_TYPE_WORKSHEET
    assert "AN005" in _codes(result)
    assert not {"FM008", "FM009", "FM010"} & set(_codes(result))


def test_kurzentwurf_uses_kurzentwurf_validator():
    result = inspect_document_text(
        "---\ndocument_type: kurzentwurf\nStundenthema: Thema\nLerngruppe: 6a\nstart: 08:00\n---\n:::lines\n",
        document_type=DOCUMENT_TYPE_KURZENTWURF,
    )

    assert result.document_type == DOCUMENT_TYPE_KURZENTWURF
    assert any(diag.code == "KZF010" and "Kurzentwurf-DSL" in diag.message for diag in result.diagnostics)


def test_kurzentwurf_implicit_lines_do_not_emit_kzf049_warning():
    result = inspect_document_text(
        "---\ndocument_type: kurzentwurf\nStundenthema: Thema\nLerngruppe: 6a\nstart: 08:00\n---\n\n"
        "#einstieg t=10\nFreitext ohne Marker\n",
        document_type=DOCUMENT_TYPE_KURZENTWURF,
    )

    assert "KZF049" not in _codes(result)


def test_content_never_decides_the_type():
    # Kurzentwurf-Keys in einer Arbeitsblatt-Datei machen sie nicht zum Kurzentwurf (I1).
    result = inspect_document_text(
        "---\ndocument_type: worksheet\nStundenthema: X\nLerngruppe: 6a\nstart: 08:00\n---\n",
        document_type=DOCUMENT_TYPE_WORKSHEET,
    )

    assert result.document_type == DOCUMENT_TYPE_WORKSHEET
    assert "FM001" in _codes(result)


def test_markdown_runs_no_blattwerk_validator():
    result = inspect_document_text("# Titel\n\n:::lines\n\n:::\n", document_type=DOCUMENT_TYPE_MARKDOWN)

    assert result.document_type == DOCUMENT_TYPE_MARKDOWN
    assert _codes(result) == []


def test_missing_marker_warns_only_for_blattwerk_types():
    worksheet = inspect_document_text("---\nTitel: T\nFach: M\nThema: X\n---\n", document_type="worksheet")
    markdown = inspect_document_text("---\nTitel: T\n---\nText\n", document_type="markdown")

    assert "FM009" in _codes(worksheet)
    assert "FM009" not in _codes(markdown)


def test_mismatching_marker_warns_and_extension_wins():
    result = inspect_document_text(
        "---\ndocument_type: exam\nTitel: T\nFach: M\nThema: X\n---\n", document_type="worksheet"
    )

    assert result.document_type == DOCUMENT_TYPE_WORKSHEET
    assert "FM008" in _codes(result)


def test_markdown_with_blattwerk_marker_gets_fm008():
    result = inspect_document_text("---\ndocument_type: exam\n---\nText\n", document_type="markdown")

    assert _codes(result) == ["FM008"]


def test_inspect_document_path_uses_extension(tmp_path):
    path = tmp_path / "entwurf.ebw"
    path.write_text("---\ndocument_type: kurzentwurf\nStundenthema: T\nLerngruppe: 6a\nstart: 08:00\n---\n", encoding="utf-8")

    assert inspect_document_path(path).document_type == DOCUMENT_TYPE_KURZENTWURF


def test_inspect_document_path_rejects_unknown_extension_without_explicit_type(tmp_path):
    path = tmp_path / "notiz.txt"
    path.write_text("Text", encoding="utf-8")

    with pytest.raises(ValueError):
        inspect_document_path(path)
    assert inspect_document_path(path, document_type="markdown").document_type == DOCUMENT_TYPE_MARKDOWN
