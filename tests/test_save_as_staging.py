"""Tests für Speichern-unter mit Typwechsel (`app/core/save_as_staging.py`)."""

from app.core.document_semantics import marker_diagnostics
from app.core.blatt_kern_shared import split_front_matter
from app.core.save_as_staging import stage_save_as_content

WORKSHEET = "---\ndocument_type: worksheet\nTitel: T\nFach: M\nThema: X\n---\n:::task\nA\n:::\n"


def test_worksheet_to_exam_writes_canonical_marker():
    staged = stage_save_as_content(WORKSHEET, "worksheet", "exam")

    assert staged.type_changed and staged.marker_updated and not staged.edit_unsafe
    assert staged.content == WORKSHEET.replace("document_type: worksheet", "document_type: exam")
    meta, _ = split_front_matter(staged.content)
    assert marker_diagnostics(meta, "exam") == []  # kein selbst erzeugtes FM008


def test_exam_to_worksheet_writes_worksheet():
    exam = WORKSHEET.replace("worksheet", "exam")
    assert "document_type: worksheet" in stage_save_as_content(exam, "exam", "worksheet").content


def test_alias_marker_is_replaced_by_canonical_value():
    content = WORKSHEET.replace("document_type: worksheet", "document_type: arbeitsblatt")
    assert "document_type: presentation" in stage_save_as_content(content, "worksheet", "presentation").content


def test_old_mode_line_is_kept_unchanged():
    content = WORKSHEET.replace("Titel: T\n", "Titel: T\nmode: test\n")
    staged = stage_save_as_content(content, "worksheet", "exam")
    assert "mode: test" in staged.content


def test_blattwerk_to_markdown_keeps_marker_unchanged():
    staged = stage_save_as_content(WORKSHEET, "worksheet", "markdown")

    assert staged.type_changed and not staged.marker_updated
    assert staged.content == WORKSHEET
    meta, _ = split_front_matter(staged.content)
    assert [d.code for d in marker_diagnostics(meta, "markdown")] == ["FM008"]


def test_exam_to_markdown_does_not_add_markdown_marker():
    content = "---\nTitel: T\n---\nText\n"
    assert stage_save_as_content(content, "exam", "markdown").content == content


def test_markdown_to_blattwerk_adds_marker_even_without_frontmatter():
    staged = stage_save_as_content("Text\n", "markdown", "worksheet")
    assert staged.content == "---\ndocument_type: worksheet\n---\nText\n"


def test_same_type_changes_nothing():
    staged = stage_save_as_content(WORKSHEET, "worksheet", "worksheet")
    assert not staged.type_changed and staged.content == WORKSHEET


def test_unsafe_frontmatter_reports_edit_unsafe_and_keeps_content():
    content = "---\na: 1\na: 2\n---\n"
    staged = stage_save_as_content(content, "worksheet", "exam")
    assert staged.edit_unsafe and staged.content == content
