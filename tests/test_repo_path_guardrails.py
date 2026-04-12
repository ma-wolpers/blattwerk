import json

from tools.repo_ci import check_no_absolute_paths


def test_absolute_path_detector_covers_main_variants():
    assert check_no_absolute_paths._looks_like_absolute_path("A:/vault/file.md")
    assert check_no_absolute_paths._looks_like_absolute_path("A:\\vault\\file.md")
    assert check_no_absolute_paths._looks_like_absolute_path("\\\\server\\share\\file.md")
    assert check_no_absolute_paths._looks_like_absolute_path("/var/data/file.md")

    assert not check_no_absolute_paths._looks_like_absolute_path("7thVault/notes/file.md")
    assert not check_no_absolute_paths._looks_like_absolute_path("https://example.com/file")


def test_validate_file_reports_absolute_json_path(tmp_path, monkeypatch):
    payload_path = tmp_path / "state.json"
    payload_path.write_text(
        json.dumps({"dialog_initial_dirs": {"input_markdown": "A:/7thCloud/7thVault"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_no_absolute_paths, "ROOT", tmp_path)

    violations = check_no_absolute_paths._validate_file("state.json")

    assert violations
    assert "absolute path" in violations[0]


def test_has_relevant_changes_detects_state_json_prefix():
    changed = {"app/storage/.state/blattwerk_ui_settings.json"}
    assert check_no_absolute_paths._has_relevant_changes(changed) is True


def test_has_relevant_changes_detects_guardrail_script_itself():
    changed = {"tools/repo_ci/check_no_absolute_paths.py"}
    assert check_no_absolute_paths._has_relevant_changes(changed) is True


def test_has_relevant_changes_returns_false_for_unrelated_paths():
    changed = {"docs/ARCHITEKTUR.md", "app/core/blatt_validator.py"}
    assert check_no_absolute_paths._has_relevant_changes(changed) is False
