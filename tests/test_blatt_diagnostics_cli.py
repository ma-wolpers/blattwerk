from pathlib import Path

from app.cli.blatt_diagnostics_cli import _diagnostics_json


def _write_markdown(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_diagnostics_json_sets_blocking_in_strict_mode(tmp_path):
    md_file = _write_markdown(
        tmp_path / "strict.md",
        "---\nTitel: T\nFach: M\nThema: X\n---\n:::answer type=lines\n\n:::\n",
    )

    payload = _diagnostics_json(md_file, "strict")

    assert payload["mode"] == "strict"
    assert payload["blocking"] is True


def test_diagnostics_json_standard_mode_keeps_non_blocking_warning(tmp_path):
    md_file = _write_markdown(
        tmp_path / "standard.md",
        "---\nTitel: T\nFach: M\nThema: X\n---\n:::answer type=lines\n\n:::\n",
    )

    payload = _diagnostics_json(md_file, "standard")

    assert payload["mode"] == "standard"
    assert payload["blocking"] is False
