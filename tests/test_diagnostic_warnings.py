from pathlib import Path

from app.core.diagnostic_warnings import build_warning_payload


def test_build_warning_payload_contains_signature_and_count_for_valid_document(tmp_path):
    doc_path = tmp_path / "ok.md"
    doc_path.write_text(
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "---\n"
        "Text\n",
        encoding="utf-8",
    )

    payload = build_warning_payload(doc_path, "Vorschau")

    assert payload is not None
    assert payload["count"] == 0
    assert payload["title"] == "Blattwerk-Warnungen (Vorschau)"
    assert payload["message"] == ""
    assert payload["signature"][0].endswith("ok.md")


def test_build_warning_payload_formats_first_diagnostic_line(tmp_path):
    doc_path = tmp_path / "warn.md"
    doc_path.write_text(
        "---\n"
        "Titel: T\n"
        "Fach: M\n"
        "Thema: X\n"
        "---\n"
        ":::lines\n\n:::\n",
        encoding="utf-8",
    )

    payload = build_warning_payload(doc_path, "Export")

    assert payload is not None
    assert payload["count"] >= 1
    assert payload["title"] == "Blattwerk-Warnungen (Export)"
    assert "AN005" in payload["message"]
