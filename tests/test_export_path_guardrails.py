from pathlib import Path

import pytest

from app.core.export_path_guardrails import PROJECT_ROOT, validate_export_output_path


def test_validate_export_output_path_accepts_regular_pdf_target(tmp_path):
    target = tmp_path / "blatt.pdf"

    normalized = validate_export_output_path(target, allowed_suffixes={".pdf"})

    assert normalized.suffix == ".pdf"


def test_validate_export_output_path_rejects_directory_target(tmp_path):
    with pytest.raises(ValueError, match="muss eine Datei"):
        validate_export_output_path(tmp_path, allowed_suffixes={".pdf"})


def test_validate_export_output_path_rejects_invalid_suffix(tmp_path):
    with pytest.raises(ValueError, match="ungueltige Endung"):
        validate_export_output_path(tmp_path / "blatt.txt", allowed_suffixes={".pdf"})


def test_validate_export_output_path_rejects_internal_project_folder_target():
    blocked_target = PROJECT_ROOT / ".git" / "artifact.pdf"

    with pytest.raises(ValueError, match="internen Projektordner"):
        validate_export_output_path(blocked_target, allowed_suffixes={".pdf"})
